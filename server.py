#!/usr/bin/env python

import sys
import json
import os
import hashlib

from random import randint

from twisted.python import log
from twisted.internet import reactor, ssl, protocol
from twisted.web.server import Site
from twisted.protocols.basic import LineReceiver
from twisted.web.client import Agent

from autobahn.twisted.websocket import WebSocketServerFactory, \
                               WebSocketServerProtocol, \
                               listenWS

from netaddr import * # for OUI database lookups

from autobahn.twisted.resource import WebSocketResource

from pprint import pprint 

from zeroconfService import ZeroconfService

from mesh_util import Config, \
                      MeshNodeFactory, \
                      NodeStaticResource, \
                      FakeNodePopulatorThread, \
                      NodeConfigResource, \
                      GetSSIDResource, \
                      PrintStickerResource, \
                      IPKBuilder, \
                      TemplateCompiler, \
                      NodeDB

config = None

class ConfWebSocketProtocol(WebSocketServerProtocol):
    'Subclass WebSocketServerProtocol configure mesh nodes over WebSocket'

    COMMAND_KEY     = 'command'
    SOCKET_ID_KEY   = 'socket_id'
    NODE_OBJECT_KEY = 'node_obj'
    
    def sendMsg(self, msg):
        self.sendMessage(json.dumps(msg), False)

    def onOpen(self):
        self.factory.gotConnection(self)

    def _process_message(self, message):
        try:
            command_array = json.loads(message)
            socket_id = command_array[ConfWebSocketProtocol.SOCKET_ID_KEY]
            nodeObj = MeshNodeFactory.buildFromArray(command_array[ConfWebSocketProtocol.NODE_OBJECT_KEY])

            if command_array[ConfWebSocketProtocol.COMMAND_KEY] == NodeProtocol.COMMAND_NODE_SET_CONFIG:
                test = configNodeStub
                test(socket_id, nodeObj)
            else:
                print "Received unrecognized command from Web Client: " + message

        except:
            print "JSON decode error for received Web Client message: " + message

    def onMessage(self, msg, binary):
        if not binary:
            self._process_message(msg)

    def connectionLost(self, reason):
        self.factory.lostConnection(self)
        WebSocketServerProtocol.connectionLost(self, reason)


def configNodeStub(socket_id, meshNode):
    print "Configure node at socket %d using: " % socket_id + meshNode.toString()


class ChainedOpenSSLContextFactory(ssl.DefaultOpenSSLContextFactory):
    def __init__(self, privateKeyFileName, certificateChainFileName,
                 sslmethod=ssl.SSL.TLSv1_METHOD):
        """
        @param privateKeyFileName: Name of a file containing a private key
        @param certificateChainFileName: Name of a file containing a certificate chain
        @param sslmethod: The SSL method to use
        """
        self.privateKeyFileName = privateKeyFileName
        self.certificateChainFileName = certificateChainFileName
        self.sslmethod = sslmethod
        self.cacheContext()
    
    def cacheContext(self):
        ctx = ssl.SSL.Context(self.sslmethod)
        ctx.use_certificate_chain_file(self.certificateChainFileName)
        ctx.use_privatekey_file(self.privateKeyFileName)
        self._context = ctx


class NodeProtocol(LineReceiver):
    """Node Configurator protocol"""
    delimiter = "\n"
    
    def nodeConnected(self):
        print "Node connected"

    # Send the configuration IPK to the node
    # and ask the node to run a command
    def sendConfig(self, ipkFilePath):

        # TODO get command from config file
        fileName = os.path.basename(ipkFilePath)
        fileSize = os.path.getsize(ipkFilePath)

        # calculate md5
        md5 = hashlib.md5()
        f = open(ipkFilePath, 'rb')
        for line in f:
            md5.update(line)
        fileMD5 = md5.hexdigest()
        f.seek(0)

        msg = {
            'type': 'configure',
            'data': {
                'file_name': fileName,
                'file_size': fileSize,
                'file_md5': fileMD5,
                'run_cmd': config['configure_cmd'],
                'post_cmd': config['post_configure_cmd']
                }
            }

        # send the message
        msg_str = json.dumps(msg)
        self.sendLine(msg_str)
        # send the file
        while True:
            data = f.read(8192)
            if data == '':
                break
            self.transport.write(data)
        f.close()

#        self.transport.loseConnection()

    def connectionMade(self):
        print "Got connection"
        self.nodeInfo = None

    def connectionLost(self, reason):
        print "Lost connection"
        if(self.nodeInfo):
            self.factory.nodeDisappeared(self)

    # configures an attached node
    # based on form POST data received
    # from the web app
    def configure(self, nodeConfig):
        
        # Step 1: Assign unique IP and log to DB
        
        # Step 2: Build the IPK

        builder = IPKBuilder(nodeConfig)
        stagingDir = builder.stage()
        
        dataDir = os.path.join(stagingDir, 'data')
        tcompiler = TemplateCompiler(nodeConfig, 'templates', dataDir, config['wordlist'])

        nodeConfig = tcompiler.assign()

        # create the node in the database
        # and receive the nodeConfig with assigned
        # IP address and unique id
        nodeConfig = self.factory.node_db.create(nodeConfig)
        if not nodeConfig:
            # TODO bubble error up to browser
            print "-- Error talking to node database"
            return

        tcompiler.compile(nodeConfig)

        ipk_file_path = builder.build()
        builder.clean()

        # Step 3: Send the IPK to the node

        self.sendConfig(ipk_file_path)
        
        return nodeConfig

    def lookup_org_from_mac(self, mac_addr):
        mac = EUI(mac_addr)
        if not mac:
            return None
        reg = mac.oui.registration()
        if not reg:
            return None
        return reg.org
        

    def gotNodeInfo(self, msg):
        self.nodeInfo = msg['data']
        if not self.nodeInfo['mac_addr']:
            return
        
        self.nodeInfo['mac_org'] = self.lookup_org_from_mac(self.nodeInfo['mac_addr']) or "Unknown"
#        print "ORG: " + self.nodeInfo['mac_org']
        self.factory.nodeAppeared(self)
        
    def parseMessage(self, msg_str):
        print "Parsing message"
        msg = json.loads(msg_str)
        if not msg:
            print "Could not parse JSON"
            self.transport.loseConnection()
            return

        print "Got message: "
        pprint(msg)

        if msg['type'] == 'node_appeared':
            self.gotNodeInfo(msg)
        elif msg['type'] == 'node_status':
            self.factory.forwardToWebSockets(msg)
        else:
            print "Unknown message"

    def lineReceived(self, line):
        self.parseMessage(line)

    def rawDataReceived(self, data):
        "As soon as any data is received, write it back."
        self.transport.write(data)

class NodeConfFactory(protocol.Factory):

    protocol = NodeProtocol
    nodeWSFactory = None
    nodes = [] # connected nodes

    def __init__(self, node_db):
        self.node_db = node_db

    # takes the node config data submitted from the from
    # in the web app and runs configuration for the node
    # with the matchin MAC address
    def configureNode(self, nodeConfig):
        for node in self.nodes:
            if nodeConfig['mac_addr'] == node.nodeInfo['mac_addr']:
                return node.configure(nodeConfig)

        return False
            
    def forwardToWebSockets(self, msg):
        if self.nodeWSFactory:
            self.nodeWSFactory.sendToConnected(msg)

    def nodeAppeared(self, proto):
        self.nodes.append(proto)
        log.msg("node count: %d" % len(self.nodes))
        if self.nodeWSFactory:
            self.nodeWSFactory.nodeAppeared(proto.nodeInfo)

    def nodeDisappeared(self, proto):
        self.nodes.remove(proto)
        log.msg("node count: %d" % len(self.nodes))
        if self.nodeWSFactory:
            self.nodeWSFactory.nodeDisappeared(proto.nodeInfo)


# node configuraiton web socket factory
class NodeWSFactory(WebSocketServerFactory):

    nodeConfFactory = None
    protocol = ConfWebSocketProtocol
    websockets = [] # connected websockets

    def sendToConnected(self, msg):
        for websocket in self.websockets:
            websocket.sendMsg(msg)

    def nodeAppeared(self, nodeInfo):

        log.msg("Sending updated nodelist %d websockets" % len(self.websockets))
        msg = {}
        msg['type'] = 'node_appeared'
        msg['data'] = nodeInfo
        self.sendToConnected(msg)

    def nodeDisappeared(self, nodeInfo):

        for websocket in self.websockets:
            log.msg("Sending updated nodelist to one of %d websockets" % len(self.websockets))
            msg = {}
            msg['type'] = 'node_disappeared'
            msg['data'] = nodeInfo
            websocket.sendMsg(msg)

    def gotConnection(self, webSocketProtocol):
        # every time a new websocket connects, 
        # tell them about all connected nodes
        self.websockets.append(webSocketProtocol)
        log.msg("websocket count: %d" % len(self.websockets))
        for node in self.nodeConfFactory.nodes:
            msg = {}
            msg['type'] = 'node_appeared'
            msg['data'] = node.nodeInfo
            webSocketProtocol.sendMsg(msg)

    def lostConnection(self, webSocketProtocol):
        self.websockets.remove(webSocketProtocol)
        log.msg("websocket count: %d" % len(self.websockets))

    def __init__(self, url=None, debug=False, nodeConfFactory=None):
        self.nodeConfFactory = nodeConfFactory
        self.nodeConfFactory.nodeWSFactory = self;
        WebSocketServerFactory.__init__(self, url=url, debug=debug)

#def addSocket(nodeSocket):
#    print "add socket stub fileno() %d " % nodeSocket.transport.file.fileno()

#def removeSocket(nodeSocket):
#    print "remove socket stub fileno() %d " % nodeSocket.transport.file.fileno()


def start():
    log.startLogging(sys.stdout)

    contextFactory = ChainedOpenSSLContextFactory(
      privateKeyFileName="certs/nodeconf.key",
      certificateChainFileName="certs/nodeconf_chain.crt", 
      sslmethod = ssl.SSL.TLSv1_METHOD)

        
    db = NodeDB(
        db_host=config['db_host'],
        )


    # create the node configuration server
    nodeConfFactory = NodeConfFactory(node_db=db)
    reactor.listenSSL(int(config['port']), nodeConfFactory, contextFactory, interface=config['hostname'])
    # create the WebSocket server.
#    webSocketFactory = WebSocketServerFactory("wss://localhost:%d" % WEBSERVER_PORT, debug=False)

    # Build Web and WebSocket URIs
    hostname = config['hostname']
    web_hostname = config['web_hostname']
    web_protocol = config['protocol']
    websocket_protocol = None

    if web_protocol == 'http':
        websocket_protocol = 'ws'
    else:
        websocket_protocol = 'wss'

    web_port = int(config['web_port'])
    port_str = ''
    if ((web_protocol == 'http') and (web_port != 80)) or ((web_protocol == 'https') and (web_port != 443)):
        port_str = ':%s' % str(web_port)

    websocket_uri = websocket_protocol + '://' + web_hostname + port_str
    web_uri = web_protocol + '://' + web_hostname + port_str

    nodeWSFactory = NodeWSFactory(websocket_uri, nodeConfFactory=nodeConfFactory, debug=False)
#    nodeWSFactory.protocol = ConfWebSocketProtocol
#    listenWS(webSocketFactory, contextFactory)

    # create the HTTP server.
    nodeHttpResource = NodeStaticResource()
    wsresource = WebSocketResource(nodeWSFactory)
    wsresource_name = config['websocket_path'][1:]

    # add the WebSocket server as a resource to the webserver
    nodeHttpResource.putChild(wsresource_name, wsresource)

    # add the form POST handlers as a resources to the webserver
    # configure node post
    nodeConfigResource = NodeConfigResource(nodeConfFactory)
    nodeConfigResourceName = config['config_post_path'][1:]
    nodeHttpResource.putChild(nodeConfigResourceName, nodeConfigResource)
    # get ssid post
    getSSIDResource = GetSSIDResource(nodeConfFactory, config['wordlist'])
    getSSIDResourceName = config['get_ssid_path'][1:]
    nodeHttpResource.putChild(getSSIDResourceName, getSSIDResource)
    # print sticker post
    stickerPath = 'stickers' # TODO get this from config file
    printStickerResource = PrintStickerResource(nodeConfFactory, stickerPath)
    printStickerResourceName = 'print-sticker' 
    nodeHttpResource.putChild(printStickerResourceName, printStickerResource)

    webServerFactory = Site(nodeHttpResource)

    reactor.listenSSL(web_port, webServerFactory, contextFactory, interface=config['web_hostname'])

    service = ZeroconfService(name="sudomesh node configurator", stype=config['service_type'], port=int(config['port']))

    service.publish()

    log.msg("Publishing Avahi service of type %s on port %s" % (config['service_type'], str(config['port'])))
    log.msg("Webserver ready on %s" % web_uri);

    # start the servers.
    reactor.run()
    service.unpublish()

if __name__ == "__main__":
    config = Config.load()
    start()
