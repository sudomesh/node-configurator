#!/usr/bin/python

import json
import time
import string
import random
import threading
import re
import os
import shutil

from random               import randint

from twisted.web.resource import Resource
from twisted.web.static   import File
#import os.path

from subprocess import call



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


class TemplateCompiler():

    def __init__(self, nodeConfig, inputDir, outputDir):
        self.nodeConfig = nodeConfig
        self.inputDir = inputDir
        self.outputDir = outputDir
        
    # writes data to file at path
    # if either file or any dirs that are part of path 
    # don't exist, then they are created
    # if file exists, overwrite
    def write_file(self, path, data):
        d = os.path.dirname(path)
        if not os.path.exists(d):
            os.makedirs(d)

        f = open(path, 'w')
        f.write(data)
        f.close()
        
    # takes uncompiled data (a template) as input
    # returns compiled data
    def compile_data(self, data):
        for key in self.nodeConfig:
            pattern = '<'+key+'>'
            data = data.replace('<'+key+'>', self.nodeConfig[key])
        return data

    # check if a filename should be skipped
    # returns True for skip, False for not skip
    def should_skip(self, filename):
        if re.match(".*~$", filename):
            return True
        if re.match("^#.*#$", filename):
            return True
        return False

    # compile all files in input dir
    # and put the results in the output dir
    def compile(self):
        for root, dirs, files in os.walk(self.inputDir):
            for curfile in files:
                if self.should_skip(curfile) == True:
                    continue
                inpath = os.path.join(root, curfile)
                f = open(inpath, 'r')
                template = f.read()
                f.close()
                compiled = self.compile_data(template)
                outpath = os.path.join(self.outputDir, root, curfile)
                self.write_file(outpath, compiled)
            

class IPKBuilder():

    def __init__(self, nodeConfig):
        self.nodeConfig = nodeConfig
        self.staging_dir  = 'per-node-config-'+self.nodeConfig['mac_addr'].replace(':', '-')
        self.ipk_file = self.staging_dir+'.ipk'
        
    def build(self):
        os.chdir('staging')
        
        try:
            os.remove(self.ipk_file)
        except:
            pass

        try:
            shutil.rmtree(self.staging_dir)
        except:
            pass

        os.mkdir(self.staging_dir)
        os.chdir(self.staging_dir)

        shutil.copy("../../templates/debian-binary", "./")

        os.mkdir("control")
        shutil.copy("../../templates/control", "control/")

        os.mkdir("data")
        os.chdir("data")

        # generate host ssh keys
        os.makedirs("etc/ssh")
        os.chdir("etc/ssh")
        call(["expect", "-f", "../../../../../scripts/gen_ssh_keys.exp"])
        os.chdir("../../")
                
        # package it up
        os.chdir("../")
        call(["tar", "-czf", "data.tar.gz", "data"])
        call(["tar", "-czf", "control.tar.gz", "control"])
        call(["tar", "-czf", '../'+self.ipk_file, "data.tar.gz", "control.tar.gz", "debian-binary"])
        os.chdir("../")

        # delete staging dir
        shutil.rmtree(self.staging_dir)

        return True
        

class NodeConfigResource(Resource):
    isLeaf = True
    nodeConfFactory = None

    def __init__(self, nodeConfFactory):
        self.nodeConfFactory = nodeConfFactory

    def render_POST(self, request):
        reply = {}
        reply['type'] = "node_config_reply"
        reply['status'] = "success"
        msg_str = request.content.read()
        print "Got: " + msg_str
        msg = json.loads(msg_str)
        
        if not msg:
            reply['status'] = "error"
            reply['error'] = "Server could not parse JSON submitted by client"
            return json.dumps(reply)

        if msg['type'] != "node_config":
            reply['status'] = "error"
            reply['error'] = "Unrecognized message type: " + msg['type']
            return json.dumps(reply)

        if not self.nodeConfFactory.configureNode(msg['data']):
            if msg['type'] != "node_config":
                reply['status'] = "error"
                # TODO better error message
                reply['error'] = "Node configuration failed"
                return json.dumps(reply)

        return json.dumps(reply)

class NodeStaticResource(Resource):
    'Subclass Resource to serve static node configuration resource'

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
        
