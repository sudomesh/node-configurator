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

  def __init__(self, hardware_model, firmware_version, geo_location, op_name, op_email, op_phone):
    self.hardware_model = hardware_model
    self.firmware_version = firmware_version
    self.geo_location = geo_location
    self.op_name = op_name
    self.op_email = op_email
    self.op_phone = op_phone

  def toJSON(self):
    return json.dumps([{
                         'hardware_model'   : self.hardware_model,
                         'firmware_version' : self.firmware_version,
                         'geo_location'     : self.geo_location,
                         'op_name'          : self.op_name,
                         'op_email'         : self.op_email,
                         'op_phone'         : self.op_phone }]);

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
        myNode = SudoNode("Ubiquity nano-station",
                          "SudoNode v0.5",
                          "Oakland, CA",
                          self.rand_string(),
                          self.rand_string() + "@" + self.rand_string() + ".org",
                          "1-555-555-1337")

        self.webSocketServer.sendMessage(myNode.toJSON(), False)

    return

  def finish(self):
    self.running = False
