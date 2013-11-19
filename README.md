# Introduction #

This is the sudo mesh node configurator. The idea is that you flash a node with the sudo mesh firmware, then run the node configurator on e.g. your laptop and connect your laptop and the flashed node to the same LAN and boot the node. The node will find the node configurator using DNS-SD, connect to the node using SSL (ensuring that the node configurator is an official authorized configurator) and ask for updates. The configurator will send one or more .ipkg files and their md5 checksums and the node will write these to /tmp, verify their checksums, install them and remove the files from /tmp. 

This is a work in progress!

Instructions for how to use it:

For testing it may be easier to turn off password protection for the SSL certificates, so use:

./gen_certificates.sh nopass

This will generate a self-signed key/crt for a root CA, a key/crt for a subordinate CA signed by the root CA and finally a crt/key signed by the subordinate CA which is used as the crt/key pair for the python server.

Now start the server:

./ssl_server.py

And start the client:

./ssl_client.lua

Requirements for python server stuff:

openssl
dbus
avahi-daemon
python
python-twisted
md5sum

Requirements for lua client stuff:

openssl
mdnsd
lua
luasocket
luasec
md5sum

Also, see more documentation in the comments in ssl_server.py and ssl_client.lua

# Server #

## Prerequisites ##

For a typical modern Debian / Ubuntu desktop machine first install some prerequisites:

  sudo aptitude install python avahi-daemon python-virtualenv python-pip python-openssl python-dbus python-avahi build-essential openssl-dev expect

Install the extra required python packages in a virtual python environment:

  ./scripts/install_python_prereqs

## Starting the server ##

Simply do:

  ./start_server.sh


  
