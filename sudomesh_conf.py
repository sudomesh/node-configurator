#!/usr/bin/python

import json
import threading
import time
import random
import string

class MeshNode:
  'Model of a simple mesh node'

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

class FakeNodePopulatorThread(threading.Thread):
  'Subclass Thread to send fake nodes over a WebSocket at an interval'

  def setup(self, webSocketServer, interval):
    self.has_server = True
    self.interval = interval
    self.webSocketServer = webSocketServer

  def rand_string(self, size=6, chars=string.ascii_uppercase + string.digits):
    return ''.join(random.choice(chars) for x in range(size))

  def run(self):
    self.running = True

    while self.running:
      if self.has_server :
        time.sleep(self.interval)
        myNode = MeshNode("Ubiquity nano-station",
                          "SudoNode v0.5",
                          "Oakland, CA",
                          self.rand_string(),
                          self.rand_string() + "@" + self.rand_string() + ".org",
                          "1-555-555-1337")
        self.webSocketServer.sendMessage(myNode.toJSON(), False)

    return

  def finish(self):
    self.running = False
