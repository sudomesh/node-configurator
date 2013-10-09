#!/usr/bin/python

import threading
import string
import random

from twisted.web.server import Site
from twisted.internet   import reactor

from sudomesh_conf import NodeConfStaticServer, SudoNode

# create and run the server
resource = NodeConfStaticServer()
factory = Site(resource)
reactor.listenTCP(8880, factory)
reactor.run()

class ThreadClass(threading.Thread):
  def rand_string(self, size=6, chars=string.ascii_uppercase + string.digits):
    return ''.join(random.choice(chars) for x in range(size))

  def run(self):
    myNode = SudoNode(self.rand_string(), self.rand_string(12))
    print myNode.toJSON()
    return

for i in range(2):
  t = ThreadClass()
  t.start()