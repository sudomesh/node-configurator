#!/usr/bin/python

import string
import random

class MeshNode:
  'Model of a simple mesh node'

  CONST_HARDWARE_MODEL_KEY   = 'hardware_model'
  CONST_FIRMWARE_VERSION_KEY = 'firmware_version'
  CONST_GEO_LOCATION_KEY     = 'geo_location'
  CONST_OP_NAME_KEY          = 'op_name'
  CONST_OP_EMAIL_KEY         = 'op_email'
  CONST_OP_PHONE_KEY         = 'op_phone'

  def __init__(self, hardware_model, firmware_version, geo_location, op_name, op_email, op_phone):
    self.hardware_model = hardware_model
    self.firmware_version = firmware_version
    self.geo_location = geo_location
    self.op_name = op_name
    self.op_email = op_email
    self.op_phone = op_phone

  def toDict(self):
    return {
              self.CONST_HARDWARE_MODEL_KEY   : self.hardware_model,
              self.CONST_FIRMWARE_VERSION_KEY : self.firmware_version,
              self.CONST_GEO_LOCATION_KEY     : self.geo_location,
              self.CONST_OP_NAME_KEY          : self.op_name,
              self.CONST_OP_EMAIL_KEY         : self.op_email,
              self.CONST_OP_PHONE_KEY         : self.op_phone }

class MeshNodeFactory:
  'Class to generate fake MeshNode objects'

  @staticmethod
  def _rand_string(size=6, chars=string.ascii_uppercase + string.digits):
    return ''.join(random.choice(chars) for x in range(size))

  @staticmethod
  def buildFake():
    return MeshNode("Ubiquity nano-station",
                    "SudoNode v0.5",
                    "Oakland, CA",
                    MeshNodeFactory._rand_string(),
                    MeshNodeFactory._rand_string() + "@" + MeshNodeFactory._rand_string() + ".org",
                    "1-555-555-1337")