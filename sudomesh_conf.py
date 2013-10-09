#!/usr/bin/python

import json

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