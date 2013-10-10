#!/usr/bin/python

import sys
import threading
import time
import json

from random import randint

from twisted.python       import log
from twisted.internet     import reactor
from twisted.web.server   import Site
from twisted.web.resource import Resource
from twisted.web.static   import File

from autobahn.websocket   import WebSocketServerFactory, \
                                 WebSocketServerProtocol, \
                                 listenWS

from mesh_util            import MeshNodeFactory

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

class FakeNodePopulatorThread(threading.Thread):
  'Subclass Thread to send fake actions over a WebSocket at an interval'

  def setup(self, webSocketServer, interval):
    self._has_server = True
    self._connect_node = True
    self._interval = interval
    self._webSocketServer = webSocketServer

  def _doFakeStuff(self):
    fakeNode = MeshNodeFactory.buildFake()

    if self._connect_node:
      self._webSocketServer.sendAction(NodeConfWebSocketProtocol.CONST_ACTION_NODE_CONNECTED, randint(0, 100), fakeNode)
    else:
      self._webSocketServer.sendAction(NodeConfWebSocketProtocol.CONST_ACTION_NODE_DISCONNECTED, randint(0, 100), fakeNode)
    self._connect_node = not self._connect_node

  def run(self):
    self._running = True

    while self._running:
      if self._has_server:
        time.sleep(self._interval)
        self._doFakeStuff()

  def finish(self):
    self._running = False

class NodeConfWebSocketProtocol(WebSocketServerProtocol):
  'Subclass WebSocketServerProtocol configure mesh nodes over WebSocket'

  CONST_ACTION_KEY               = 'action'
  CONST_NODE_ID_KEY              = 'node_id'
  CONST_NODE_OBJECT_KEY          = 'node_obj'

  CONST_ACTION_NODE_CONNECTED    = 'node_connected'
  CONST_ACTION_NODE_DISCONNECTED = 'node_disconnected'
  CONST_ACTION_NODE_CONFIGURE    = 'node_configure'

  def sendAction(self, action, node_id = -1, meshNode = -1):
    actionArray = {
      NodeConfWebSocketProtocol.CONST_ACTION_KEY      : action,
      NodeConfWebSocketProtocol.CONST_NODE_ID_KEY     : node_id,
    }
    if meshNode != -1:
      actionArray[NodeConfWebSocketProtocol.CONST_NODE_OBJECT_KEY] = meshNode.toDict()

    self.sendMessage(json.dumps(actionArray), False)

  def onOpen(self):
    # send fake actions over the WebSocket every 5 seconds
    self._nodePopulator = FakeNodePopulatorThread()
    self._nodePopulator.setup(self, 5)
    self._nodePopulator.start()

  def _process_message(self, message):
    try:
      action = json.loads(message)
      node_id = action[NodeConfWebSocketProtocol.CONST_NODE_ID_KEY]
      nodeObj = MeshNodeFactory.buildFromArray(action[NodeConfWebSocketProtocol.CONST_NODE_OBJECT_KEY])

      if action[NodeConfWebSocketProtocol.CONST_ACTION_KEY] == self.CONST_ACTION_NODE_CONFIGURE:
        print "client requests configure of node %d using: " % node_id + nodeObj.toString()
      else:
        print "received unrecognized action from client: " + message

    except:
      print "JSON decode error for received client message: " + message

  def onMessage(self, msg, binary):
    if not binary:
      self._process_message(msg)

  def connectionLost(self, reason):
    self._nodePopulator.finish()
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