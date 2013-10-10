#!/usr/bin/python

import sys

from twisted.python       import log
from twisted.internet     import reactor
from twisted.web.server   import Site
from twisted.web.resource import Resource
from twisted.web.static   import File

from autobahn.websocket   import WebSocketServerFactory, \
                                 WebSocketServerProtocol, \
                                 listenWS

from sudomesh_conf        import FakeNodePopulatorThread

CONST_WEBSOCKET_PORT  = 9000;
CONST_WEB_SERVER_PORT = 8080;
CONST_STATIC_NAME     = "static"

# Implementation specific constants.
CONST_STATIC_DIR_PATH = "./static_web"
CONST_INDEX_FILE_NAME = "config.html"

class NodeConfStaticResources(Resource):
  'Subclass Resource to serve static node configuration resources'

  def getChild(self, name, request):
    if name == CONST_STATIC_NAME:
      return File(CONST_STATIC_DIR_PATH)

    return File(CONST_STATIC_DIR_PATH + "/" + CONST_INDEX_FILE_NAME)

class NodeConfWebSocketProtocol(WebSocketServerProtocol):
  'Subclass WebSocketServerProtocol configure mesh nodes over WebSocket'

  def onOpen(self):
    # send fake nodes over the WebSocket
    self.nodePopulator = FakeNodePopulatorThread()
    self.nodePopulator.setup(self, 5)
    self.nodePopulator.start()

  def onMessage(self, msg, binary):
    print "sending echo:", msg
    self.sendMessage(msg, binary)

  def connectionLost(self, reason):
    self.nodePopulator.finish()
    WebSocketServerProtocol.connectionLost(self, reason)




log.startLogging(sys.stdout)

# create the WebSocket server.
webSocketFactory = WebSocketServerFactory("ws://localhost:%d" % CONST_WEBSOCKET_PORT, debug=False)
webSocketFactory.protocol = NodeConfWebSocketProtocol
listenWS(webSocketFactory)

# create the HTTP server.
nodeHttpResources = NodeConfStaticResources()
webServerFactory = Site(nodeHttpResources)
reactor.listenTCP(CONST_WEB_SERVER_PORT, webServerFactory)

# start the servers.
reactor.run()