#!/usr/bin/python

import json
import time
import string
import random
import threading
import re
import os
import shutil
import urllib
import subprocess

from random               import randint

from twisted.web.resource import Resource
from twisted.web.static   import File
from twisted.web.http_headers import Headers


# kinda ugly to use httplib when we're also using twisted
# but twisted http requests are rediculously overcomplicated
import httplib

#from http_request import httpRequest

# Implementation specific constants.
STATIC_DIR_PATH = "./static_web"
INDEX_FILE_NAME = "index.html"
CONFIG_FILE = "config/common.json"

class Config():

    @staticmethod
    def load():
        return json.load(open(CONFIG_FILE))

class NodeDB():

    # db is the directory where json files are written
    def __init__(self, db_host=None):
        self.db_host = db_host
        self.local_backup_dir = "fakedb"
        self.basePath = os.getcwd()
        self.outPath = os.path.join(self.basePath, self.local_backup_dir)
        
    # This method creates the node in the database
    # and gets e.g. IP addresses and UUIDs assigned
    # from the database at the same time.
    def create(self, nodeConfig):
        
        if not nodeConfig or not nodeConfig['mac_addr'] or (nodeConfig['mac_addr'] == ''):
            return False

        # TODO also make a local backup after IP assigned?
        self.local_backup(nodeConfig)
        
        nodeConfig['type'] = 'node'

        params = urllib.urlencode({'data': json.dumps(nodeConfig)})
        headers = {"Content-type": "application/x-www-form-urlencoded", "Accept": "text/plain"}
        con = httplib.HTTPConnection(self.db_host)
        con.request("POST", "/nodes", params, headers)
        response = con.getresponse()
        # TODO check response code
        data_str = response.read() 
        print "DATA STR: " + data_str
        msg = json.loads(data_str)
        return msg['data']
                    
    def local_backup(self, nodeConfig):
        outFileName = 'node-config-'+re.sub(':', '-', nodeConfig['mac_addr'])+'.json'
        outFile = os.path.join(self.outPath, outFileName)

        if not os.path.exists(self.outPath):
            os.makedirs(self.outPath)
        
        f = open(outFile, 'w')
        f.write(json.dumps(nodeConfig))
        f.close()
        
        return outFile

        # TODO calculate the following:
        # mesh_dhcp_range_start
        # mesh_ipv4_addr
        # -- both calculated from node_public_subnet_ipv4

        # TODO assign the following:
        # private_subnet_ipv4_addr (172.30.0.1) 
        # ^-- Hrm won't this always be the same?
        # node_public_subnet_ipv4
        # relay_node_mesh_ipv4_addr
        # exit_node_ipv4_addr

        # TODO assign if not set
        # private_wifi_key
        # private_wifi_ssid
    

class TemplateCompiler():

    def __init__(self, nodeConfig, inputDir, outputDir, wordlist):
        self.nodeConfig = nodeConfig
        self.base_path = os.getcwd()
        self.inputDir = inputDir
        self.wordlist = wordlist
        if not os.path.isabs(self.inputDir):
            self.inputDir = os.path.join(self.base_path, self.inputDir)
        self.outputDir = outputDir
        if not os.path.isabs(self.outputDir):
            self.outputDir = os.path.join(self.base_path, self.outputDir)

        
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
            val = self.nodeConfig[key]
            val = re.sub(r'\s+', '', val)
            if val == '':
                continue
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

    # uses mkpasswd to generate a salted password hash
    # usable in a /etc/shadow file
    def hash_root_password(self):
        sub = subprocess.Popen(["/usr/bin/mkpasswd", "--method=md5", "-s"], stdin=subprocess.PIPE, stdout=subprocess.PIPE)
        sub.stdin.write(self.nodeConfig['root_password']+"\n")
        hashline = sub.stdout.read()
        self.nodeConfig['root_password_hash'] = hashline

    # generate a random password consisting of
    # upper and lower case letters, numbers and # and !
    def generate_root_password(self, length):
        if self.nodeConfig['root_password']:
            self.nodeConfig['root_password'] = self.generate_password(length)
        self.hash_root_password()

    def generate_password(self, length):
        chars = string.letters + string.digits + '#!'
        
        # if this check fails, 
        # there will be bias in passwords
        if len(chars) != 64:
            raise "password generator security compromised!"
        password = ''.join(chars[ord(os.urandom(1)) % 64] for _ in xrange(14))
        return password
        

    # read all authorized keys from the authorized_keys/ dir
    # and combine them and add them to nodeConfig
    def read_authorized_keys(self):
        authd_keys = ''
        for root, dirs, files in os.walk('authorized_keys'):
            for curfile in files:
                if self.should_skip(curfile) == True:
                    continue
                
                f = open(os.path.join(root, curfile))
                authd_keys += f.read()+"\n"
                f.close()
        self.nodeConfig['ssh_authorized_keys'] = authd_keys

    # generate a friendly wifi ssid
    # with specified number of words and numbers
    def generate_wifi_ssid(self, words, numbers=0):
        ssid = ''
        f = open(os.path.join(self.base_path, self.wordlist))
        wordlist = f.readlines()
        f.close()

        # get random word(s)
        for i in xrange(words):
            ssid += wordlist[random.randint(0, len(wordlist)-1)].strip()

        # get random number(s)
        if numbers > 0:
            valid_numbers = '0123456789'
            ssid += ''.join(valid_numbers[random.randint(0, len(valid_numbers)-1)] for _ in xrange(numbers))

        return ssid

    # compile all files in input dir
    # and put the results in the output dir
    def compile(self):
        self.generate_wifi_ssid()
        self.generate_root_password(12)
        self.read_authorized_keys()

        os.chdir(self.inputDir);
        for root, dirs, files in os.walk('.'):
            for curfile in files:
                if self.should_skip(curfile) == True:
                    continue
                inpath = os.path.join(root, curfile)
                f = open(inpath, 'r')
                template = f.read()
                f.close()
                compiled = self.compile_data(template)
                outpath = os.path.join(self.outputDir, root, curfile)
                print "writing to: " + outpath
                self.write_file(outpath, compiled)
        os.chdir(self.base_path)


class IPKBuilder():

    def __init__(self, nodeConfig):
        self.nodeConfig = nodeConfig
        self.base_path = os.getcwd()
        dirname = 'per-node-config-'+self.nodeConfig['mac_addr'].replace(':', '-')
        self.staging_dir  = os.path.join(self.base_path, 'staging', dirname)
        self.ipk_file = os.path.join(self.base_path, 'ipks', dirname+'.ipk')
        

    def stage(self):
        
        try:
            shutil.rmtree(self.staging_dir)
        except:
            pass

        os.makedirs(self.staging_dir)
        os.chdir(self.staging_dir)

        shutil.copy("../../ipk_manifest/debian-binary", "./")

        os.mkdir("control")
        shutil.copy("../../ipk_manifest/control", "control/")

        os.mkdir("data")
        os.chdir("data")

        # generate host ssh keys
        os.makedirs("etc/ssh")
        os.chdir("etc/ssh")
        subprocess.call(["expect", "-f", "../../../../../scripts/gen_ssh_keys.exp"])
             
        os.chdir(self.base_path)

        return self.staging_dir

    # Package the staged files into an IPK
    def build(self):

        try:
            os.remove(self.ipk_file)
        except:
            pass

        os.chdir(self.staging_dir)

        subprocess.call(["tar", "-czf", "data.tar.gz", "data"])
        subprocess.call(["tar", "-czf", "control.tar.gz", "control"])
        subprocess.call(["tar", "-czf", self.ipk_file, "data.tar.gz", "control.tar.gz", "debian-binary"])

        os.chdir(self.base_path)
        return self.ipk_file

    def clean(self):

        # delete staging dir
        shutil.rmtree(self.staging_dir)

        

class NodeConfigResource(Resource):
    isLeaf = True
    nodeConfFactory = None

    def __init__(self, nodeConfFactory):
        self.nodeConfFactory = nodeConfFactory

    def sanitize_msg(self, msg_str):
        # newlines are not allowed
        return re.sub(r'[\r\n]', '', msg_str)

    def render_POST(self, request):
        reply = {}
        reply['type'] = "node_config_reply"
        reply['status'] = "success"
        msg_str = request.content.read()
        msg_str = self.sanitize_msg(msg_str)
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
        
