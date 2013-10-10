#!/usr/bin/python

import json
import threading
import time
import random
import string

from twisted.web.resource import Resource
from twisted.web.static   import File

class SudoNode:
  'Model of a simple SudoMesh node'

  def __init__(self, op_name, geo_location):
    self.op_name = op_name
    self.geo_location = geo_location

  def toJSON(self):
    return json.dumps([ {'op_name' : self.op_name, 'geo_location' : self.geo_location } ]);

class NodeConfStaticServer(Resource):
  'Subclass Resource to serve static node configuration resources'

  CONST_STATIC_NAME     = "static"
  CONST_STATIC_DIR_PATH = "./static_web"
  CONST_INDEX_FILE_NAME = "config.html"

  def getChild(self, name, request):
    if name == self.CONST_STATIC_NAME:
      return File(self.CONST_STATIC_DIR_PATH)

    return File(self.CONST_STATIC_DIR_PATH + "/" + self.CONST_INDEX_FILE_NAME)

class FakeNodePopulatorThread(threading.Thread):

  def setServer(self, webSocketServer):
    self.has_server = True
    self.webSocketServer = webSocketServer

  def rand_string(self, size=6, chars=string.ascii_uppercase + string.digits):
    return ''.join(random.choice(chars) for x in range(size))

  def run(self):
    self.running = True

    while self.running:
      time.sleep(5)
      if self.has_server :
        myNode = SudoNode(self.rand_string(), self.rand_string(12))
        self.webSocketServer.sendMessage(myNode.toJSON(), False)

    return

  def finish(self):
    self.running = False
