#!/usr/bin/python

import sys
import json

from twisted.python       import log
from twisted.internet     import reactor
from twisted.web.server   import Site

from autobahn.websocket   import WebSocketServerFactory, \
                                 WebSocketServerProtocol, \
                                 listenWS

from mesh_util            import NodeProtocol, \
                                 MeshNodeFactory, \
                                 NodeStaticResources, \
                                 FakeNodePopulatorThread

WEB_SERVER_PORT        = 8080;
WEBSOCKET_SERVER_PORT  = 9000;

class NodeConfWebSocketProtocol(WebSocketServerProtocol):
  'Subclass WebSocketServerProtocol configure mesh nodes over WebSocket'

  ACTION_KEY      = 'action'
  NODE_ID_KEY     = 'node_id'
  NODE_OBJECT_KEY = 'node_obj'

  def sendAction(self, action, node_id = -1, meshNode = -1):
    action_array = {
      NodeConfWebSocketProtocol.ACTION_KEY  : action,
      NodeConfWebSocketProtocol.NODE_ID_KEY : node_id,
    }
    if meshNode != -1:
      action_array[NodeConfWebSocketProtocol.NODE_OBJECT_KEY] = meshNode.toDictionary()

    self.sendMessage(json.dumps(action_array), False)

  def onOpen(self):
    # send fake actions over the WebSocket every 5 seconds
    self._nodePopulator = FakeNodePopulatorThread()
    self._nodePopulator.setup(self, 5)
    self._nodePopulator.start()

  def _process_message(self, message):
    try:
      action_array = json.loads(message)
      node_id = action_array[NodeConfWebSocketProtocol.NODE_ID_KEY]
      nodeObj = MeshNodeFactory.buildFromArray(action_array[NodeConfWebSocketProtocol.NODE_OBJECT_KEY])

      if action_array[NodeConfWebSocketProtocol.ACTION_KEY] == NodeProtocol.COMMAND_NODE_SET_CONFIG:
        configNodeStub(node_id, nodeObj)
      else:
        print "Received unrecognized action  from Web Client: " + message

    except:
      print "JSON decode error for received Web Client message: " + message

  def onMessage(self, msg, binary):
    if not binary:
      self._process_message(msg)

  def connectionLost(self, reason):
    self._nodePopulator.finish()
    WebSocketServerProtocol.connectionLost(self, reason)

def configNodeStub(socket_id, meshNode):
  print "Configure node at socket %d using: " % socket_id + meshNode.toString()

def start():
  log.startLogging(sys.stdout)

  # create the WebSocket server.
  webSocketFactory = WebSocketServerFactory("ws://localhost:%d" % WEBSOCKET_SERVER_PORT, debug=False)
  webSocketFactory.protocol = NodeConfWebSocketProtocol
  listenWS(webSocketFactory)

  # create the HTTP server.
  nodeHttpResources = NodeStaticResources()
  webServerFactory = Site(nodeHttpResources)
  reactor.listenTCP(WEB_SERVER_PORT, webServerFactory)

  # start the servers.
  reactor.run()

if __name__ == "__main__":
    start()