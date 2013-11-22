#!/usr/bin/python

import os
import sys
import shutil

sys.path.append(os.path.join(os.path.dirname(os.path.realpath(__file__)), '../'))

from mesh_util import TemplateCompiler

nodeConfig = {
    'hostname': "nissemand"
}

outdir = 'tmp/compiled'

tcompiler = TemplateCompiler(nodeConfig, 'templates', outdir)
tcompiler.compile()

print "Compiled to " + outdir


