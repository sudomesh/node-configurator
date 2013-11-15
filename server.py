#!/usr/bin/env python

import sys
import json

from random import randint

from twisted.python import log
from twisted.internet import reactor, ssl, protocol
from twisted.web.server import Site
from twisted.protocols.basic import LineReceiver

from autobahn.websocket import WebSocketServerFactory, \
                               WebSocketServerProtocol, \
                               listenWS

from autobahn.resource import WebSocketResource

from mesh_util import Config, \
                      MeshNodeFactory, \
                      NodeStaticResources, \
                      FakeNodePopulatorThread

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
        # send fake actions over the WebSocket every 5 seconds
#        self._nodePopulator = FakeNodePopulatorThread()
#        self._nodePopulator.setup(self, 5)
#        self._nodePopulator.start()

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
        self._nodePopulator.finish()
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
#        nodeData = MeshNodeFactory.buildFake()
#        self.factory.nodeListChanged(nodeData)

    def sendConfigCommand(self):
        self.sendLine(NodeProtocol.COMMAND_NODE_SET_CONFIG)
        self.sendLine("FILE:0003:foo:fee77fce8a77d5c5bc8948693d48f75f:0000000000000015")
        self.transport.write("this is a hest\n")

    def connectionMade(self):
        print "Got connection"
        self.nodeInfo = None

    def connectionLost(self, reason):
        print "Lost connection"
        if(self.nodeInfo):
            self.factory.nodeDisappeared(self.nodeInfo)


    def gotNodeInfo(self, msg):
        self.nodeInfo = msg['data']
        self.factory.nodeAppeared(self.nodeInfo)
        
    def parseMessage(self, msg_str):
        print "Parsing message"
        msg = json.loads(msg_str)
        if not msg:
            print "Could not parse JSON"
            self.transport.loseConnection()
            return

        if msg['type'] == 'node_appeared':
            self.gotNodeInfo(msg)
        else:
            print "Unknown message"

    def lineReceived(self, line):
        print "GOT: " + line
        self.parseMessage(line)
#        if line == NodeProtocol.COMMAND_NODE_HELLO:
#        if line == config['protocol']['cmd_node_hello']:
#            self.nodeConnected()
#            self.sendConfigCommand()
#        else:
#            print "Received unrecognized command from Socket Client: " + line
#            self.transport.loseConnection()

    def rawDataReceived(self, data):
        "As soon as any data is received, write it back."
        self.transport.write(data)

class NodeConfFactory(protocol.Factory):

    protocol = NodeProtocol
    nodeWSFactory = None
    nodes = [] # connected nodes

    def nodeAppeared(self, nodeInfo):
        if self.nodeWSFactory:
            self.nodeWSFactory.nodeAppeared(nodeInfo)

    def nodeDisappeared(self, nodeInfo):
        if self.nodeWSFactory:
            self.nodeWSFactory.nodeDisappeared(nodeInfo)


    def gotConnection(self, node):
        self.nodes.append(node)
        log.msg("node count: %d" % len(self.nodes))

    def lostConnection(self, node):
        self.nodes.remove(node)
        log.msg("node count: %d" % len(self.nodes))

# node configuraiton web socket factory
class NodeWSFactory(WebSocketServerFactory):

    nodeConfFactory = None
    protocol = ConfWebSocketProtocol
    websockets = [] # connected websockets

    def nodeAppeared(self, nodeInfo):

        for websocket in self.websockets:
            log.msg("Sending updated nodelist to one of %d websockets" % len(self.websockets))
            msg = {}
            msg['type'] = 'node_appeared'
            msg['data'] = nodeInfo
            websocket.sendMsg(msg)
            
    def nodeDisappeared(self, nodeInfo):

        for websocket in self.websockets:
            log.msg("Sending updated nodelist to one of %d websockets" % len(self.websockets))
            msg = {}
            msg['type'] = 'node_disappeared'
            msg['data'] = nodeInfo
            websocket.sendMsg(msg)

    def gotConnection(self, webSocketProtocol):
        self.websockets.append(webSocketProtocol)
        log.msg("websocket count: %d" % len(self.websockets))

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

    # create the node configuration server
    nodeConfFactory = NodeConfFactory()
    reactor.listenSSL(int(config['server']['port']), nodeConfFactory, contextFactory)
    # create the WebSocket server.
#    webSocketFactory = WebSocketServerFactory("wss://localhost:%d" % WEBSERVER_PORT, debug=False)

    # Build Web and WebSocket URIs
    hostname = config['server']['hostname']
    web_protocol = config['server']['protocol']
    websocket_protocol = None

    if web_protocol == 'http':
        websocket_protocol = 'ws'
    else:
        websocket_protocol = 'wss'

    web_port = int(config['server']['web_port'])
    port_str = ''
    if ((web_protocol == 'http') and (web_port != 80)) or ((web_protocol == 'https') and (web_port != 443)):
        port_str = ':%s' % str(web_port)

    websocket_uri = websocket_protocol + '://' + hostname + port_str
    web_uri = web_protocol + '://' + hostname + port_str

    nodeWSFactory = NodeWSFactory(websocket_uri, nodeConfFactory=nodeConfFactory, debug=False)
#    nodeWSFactory.protocol = ConfWebSocketProtocol
#    listenWS(webSocketFactory, contextFactory)

    # create the HTTP server.
    nodeHttpResources = NodeStaticResources()
    wsresource = WebSocketResource(nodeWSFactory)
    wsresource_name = config['server']['websocket_path'][1:]

    # add the WebSocket server as a resource to the webserver
    nodeHttpResources.putChild(wsresource_name, wsresource)

    webServerFactory = Site(nodeHttpResources)

    reactor.listenSSL(web_port, webServerFactory, contextFactory)

    log.msg("Webserver ready on %s" % web_uri);

    # start the servers.
    reactor.run()


if __name__ == "__main__":
    config = Config.load()
    start()
