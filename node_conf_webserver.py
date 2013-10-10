#!/usr/bin/python

import sys

from twisted.web.server import Site
from twisted.internet   import reactor
from twisted.python     import log

from autobahn.websocket import WebSocketServerFactory, \
                               WebSocketServerProtocol, \
                               listenWS

from sudomesh_conf      import NodeConfStaticServer, \
                               FakeNodePopulatorThread

class EchoServerProtocol(WebSocketServerProtocol):

  def onOpen(self):
    # send fake nodes over the WebSocket
    self.nodePopulator = FakeNodePopulatorThread()
    self.nodePopulator.setServer(self)
    self.nodePopulator.start()

  def onMessage(self, msg, binary):
    print "sending echo:", msg
    self.sendMessage(msg, binary)

  def connectionLost(self, reason):
    self.nodePopulator.finish()
    WebSocketServerProtocol.connectionLost(self, reason)

log.startLogging(sys.stdout)

# create WebSocket server.
webSocketFactory = WebSocketServerFactory("ws://localhost:9000", debug=False)
webSocketFactory.protocol = EchoServerProtocol
listenWS(webSocketFactory)

# create http server.
resource = NodeConfStaticServer()
factory = Site(resource)

# start the servers.
reactor.listenTCP(8880, factory)
reactor.run()