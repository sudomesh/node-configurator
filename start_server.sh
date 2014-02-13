#!/bin/sh

if [ ! -f pyvirt/bin/activate ]; then
  echo "python virtual environtment not found"
  echo "You should probably run ./scripts/install_python_prereqs"
  exit 1
fi

. pyvirt/bin/activate
python server.py
