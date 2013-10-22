#!/usr/bin/python

import json
import time
import string
import random
import threading
import re

from random               import randint

from twisted.web.resource import Resource
from twisted.web.static   import File
import os.path



# Implementation specific constants.
STATIC_DIR_PATH = "./static_web"
INDEX_FILE_NAME = "index.html"
CONFIG_FILE = "config/common.json"

#class NodeProtocol:
#    UI_NODE_CONNECTED    = 'ui::node_connected'
#    UI_NODE_DISCONNECTED = 'ui::node_disconnected'
#    COMMAND_NODE_HAS_NEW_CONFIG   = "node::has_new_config"
#    COMMAND_NODE_WANTS_NEW_CONFIG = "node::wants_new_config"
#    COMMAND_NODE_HELLO        = "node::hello"
#    COMMAND_NODE_SET_CONFIG   = "node::set_config"
#    COMMAND_NODE_SET_FIRMWARE = "node::set_firmware"


class Config():

    @staticmethod
    def load():
        return json.load(open(CONFIG_FILE))

class NodeStaticResources(Resource):
    'Subclass Resource to serve static node configuration resources'

    STATIC_NAME = "static"

    def getChild(self, name, request):
        child = Resource.getChild(self, name, request)
        if name == self.STATIC_NAME:
            f = File(STATIC_DIR_PATH)
            if f.exists():
                return f
            else:
                return child
        

        f = File(STATIC_DIR_PATH + "/" + INDEX_FILE_NAME)
        if f.exists():
            return f
        else:
            return child


class MeshNode:
    'Model of a simple mesh node'

    HARDWARE_MODEL_KEY   = 'hardware_model'
    FIRMWARE_VERSION_KEY = 'firmware_version'
    GEO_LOCATION_KEY     = 'geo_location'
    OP_NAME_KEY          = 'op_name'
    OP_EMAIL_KEY         = 'op_email'
    OP_PHONE_KEY         = 'op_phone'

    def __init__(self, hardware_model, firmware_version, geo_location, op_name, op_email, op_phone):
        self.hardware_model = hardware_model
        self.firmware_version = firmware_version
        self.geo_location = geo_location
        self.op_name = op_name
        self.op_email = op_email
        self.op_phone = op_phone

    def toDictionary(self):
        return {
            self.HARDWARE_MODEL_KEY: self.hardware_model,
            self.FIRMWARE_VERSION_KEY: self.firmware_version,
            self.GEO_LOCATION_KEY: self.geo_location,
            self.OP_NAME_KEY: self.op_name,
            self.OP_EMAIL_KEY: self.op_email,
            self.OP_PHONE_KEY: self.op_phone}

    def toString(self):
        return self.hardware_model + ", " + self.firmware_version + ", " + \
               self.geo_location + ", " + self.op_name + ", " + self.op_email + ", " + self.op_phone


class MeshNodeFactory:
    'Class to generate fake MeshNode objects'

    @staticmethod
    def _rand_string(size=6, chars=string.ascii_uppercase + string.digits):
        return ''.join(random.choice(chars) for x in range(size))

    @staticmethod
    def buildFromArray(nodeArray):
        return MeshNode(
            nodeArray[MeshNode.HARDWARE_MODEL_KEY],
            nodeArray[MeshNode.FIRMWARE_VERSION_KEY],
            nodeArray[MeshNode.GEO_LOCATION_KEY],
            nodeArray[MeshNode.OP_NAME_KEY],
            nodeArray[MeshNode.OP_EMAIL_KEY],
            nodeArray[MeshNode.OP_PHONE_KEY]
        )

    @staticmethod
    def buildFake():
        return MeshNode("Ubiquity nano-station",
                        "SudoNode v0.5",
                        "Oakland, CA",
                        MeshNodeFactory._rand_string(),
                        MeshNodeFactory._rand_string() + "@" + MeshNodeFactory._rand_string() + ".org",
                        "1-555-555-1337")


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
            self._webSocketServer.sendCommand(NodeProtocol.UI_NODE_CONNECTED, randint(0, 100), fakeNode)
        else:
            self._webSocketServer.sendCommand(NodeProtocol.UI_NODE_DISCONNECTED, randint(0, 100), fakeNode)
        self._connect_node = not self._connect_node

    def run(self):
        self._running = True

        while self._running:
            if self._has_server:
                time.sleep(self._interval)
                self._doFakeStuff()

    def finish(self):
        self._running = False
        
