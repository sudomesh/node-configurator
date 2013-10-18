#!/usr/bin/env python

import sys
import json

from random               import randint

from twisted.python     import log
from twisted.internet   import reactor, ssl, protocol
from twisted.web.server import Site
from twisted.protocols.basic   import LineReceiver

from autobahn.websocket import WebSocketServerFactory, \
                               WebSocketServerProtocol, \
                               listenWS

from autobahn.resource import WebSocketResource

from mesh_util import NodeProtocol, \
                      MeshNodeFactory, \
                      NodeStaticResources, \
                      FakeNodePopulatorThread

CONFIGURATOR_PORT = 1337;
WEBSERVER_PORT = 8080;
WEBSOCKET_PORT = 9000;


class ConfWebSocketProtocol(WebSocketServerProtocol):
    'Subclass WebSocketServerProtocol configure mesh nodes over WebSocket'

    COMMAND_KEY     = 'command'
    SOCKET_ID_KEY   = 'socket_id'
    NODE_OBJECT_KEY = 'node_obj'

    def sendCommand(self, command, socket_id=-1, meshNode=-1):
        command_array = {
            ConfWebSocketProtocol.COMMAND_KEY: command,
            ConfWebSocketProtocol.SOCKET_ID_KEY: socket_id,
        }
        if meshNode != -1:
            command_array[ConfWebSocketProtocol.NODE_OBJECT_KEY] = meshNode.toDictionary()

        self.sendMessage(json.dumps(command_array), False)

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
        nodeData = MeshNodeFactory.buildFake()
        self.factory.nodeListChanged(nodeData)

    def sendConfigCommand(self):
        self.sendLine(NodeProtocol.COMMAND_NODE_SET_CONFIG)
        self.sendLine("FILE:0003:foo:fee77fce8a77d5c5bc8948693d48f75f:0000000000000015")
        self.transport.write("this is a hest\n")

    def connectionMade(self):
        print "Got connection"
#        addSocket(self)

    def connectionLost(self, reason):
        print "Lost connection"
#        removeSocket(self)

    def lineReceived(self, line):
#        if line == NodeProtocol.COMMAND_NODE_HELLO:
        if line == "node::hello":
            self.nodeConnected()
#            self.sendConfigCommand()
        else:
            print "Received unrecognized command from Socket Client: " + line
            self.transport.loseConnection()

    def rawDataReceived(self, data):
        "As soon as any data is received, write it back."
        self.transport.write(data)

class NodeConfFactory(protocol.Factory):

    protocol = NodeProtocol
    nodeWSFactory = None
    nodes = [] # connected nodes

    def nodeListChanged(self, nodeData):
        if self.nodeWSFactory:
            self.nodeWSFactory.nodeListChanged(nodeData)

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

    def nodeListChanged(self, nodeData):
        # TODO need to actually send real nodelist

        for websocket in self.websockets:
            log.msg("Sending updated nodelist to one of %d websockets" % len(self.websockets))
#            websocket.sendCommand(NodeProtocol.UI_NODE_CONNECTED, randint(0, 100), nodeData)
            websocket.sendCommand("ui::node_connected", randint(0, 100), nodeData)

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
    reactor.listenSSL(CONFIGURATOR_PORT, nodeConfFactory, contextFactory)
    # create the WebSocket server.
#    webSocketFactory = WebSocketServerFactory("wss://localhost:%d" % WEBSERVER_PORT, debug=False)
    nodeWSFactory = NodeWSFactory("wss://localhost:%d" % WEBSERVER_PORT, nodeConfFactory=nodeConfFactory, debug=False)
#    nodeWSFactory.protocol = ConfWebSocketProtocol
#    listenWS(webSocketFactory, contextFactory)

    # create the HTTP server.
    nodeHttpResources = NodeStaticResources()
    wsresource = WebSocketResource(nodeWSFactory)

    # add the WebSocket server as a resource to the webserver
    nodeHttpResources.putChild("websocket", wsresource)

    webServerFactory = Site(nodeHttpResources)

    reactor.listenSSL(WEBSERVER_PORT, webServerFactory, contextFactory)

    log.msg("Webserver ready on https://localhost:%s" % WEBSERVER_PORT);

    # start the servers.
    reactor.run()


if __name__ == "__main__":
    start()
