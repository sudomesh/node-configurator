# Introduction #

This is the sudo mesh node configurator. The idea is that you flash a node with the sudo mesh firmware, then run the node configurator on e.g. your laptop and connect your laptop and the flashed node to the same LAN and boot the node. The node will find the node configurator using DNS-SD, connect to the node using SSL (ensuring that the node configurator is an official authorized configurator) and ask for updates. The configurator will send one or more .ipkg files and their md5 checksums and the node will write these to /tmp, verify their checksums, install them and remove the files from /tmp. 

This is a work in progress!

Instructions for how to use it:

For testing it may be easier to turn off password protection for the SSL certificates, so use:

./gen_certificates.sh nopass

This will generate a self-signed key/crt for a root CA, a key/crt for a subordinate CA signed by the root CA and finally a crt/key signed by the subordinate CA which is used as the crt/key pair for the python server.

# Server #
## Prerequisites ##

For a typical modern Debian / Ubuntu desktop machine first install some prerequisites:

  sudo aptitude install python avahi-daemon python-virtualenv python-pip python-openssl python-dbus python-avahi build-essential libssl-dev expect fakeroot python-dev dropbear whois

Install the extra required python packages in a virtual python environment:

  ./scripts/install_python_prereqs

## Starting the server ##

Simply do:

  ./start_server.sh


# Setup #

## Configuration ##

## Security ##

IMPORTANT: PLEASE READ THE FOLLOWING.

If you are configuring nodes that are to be managed by an existing group, such as sudo mesh, then you need to obtain the SSL certificates and SSH keys from that group. If you are setting up your own node(s) that you want to manage yourself, then follow the instructions in the following sections. 

You should generate both SSL certs and SSH keys on a secured computer that is not (and preferably never has been) plugged in to a network. You should keep the root certificate key file in multiple very secure locations, since they are only needed when revoking or creating new subordinate certificates. You should keep the subordinate certificate key on a secure and disconnected computer, as it will only be used to generate certificates for new mesh services. You should keep the private SSH key on a disconnected computer, and only connect it to the network when absolutely needed. In the future, hopefully we can get around having to keep the SSH key on an internet-connected computer at all.

If you generate your own SSL certs and SSH keys, then you will have to compile your own firmware. 

### Choosing passwords ###

You should use reasonably secure passwords. You probably won't be able to remember them, as you won't be using them very often, but you could use xkcd-style passwords to make them easier to memorize for short periods of time:

* [redacted's xkcd-style password generator](https://github.com/redacted/XKCD-password-generator)

### SSL certificates ###

Use ./gen_certificates.sh to generate certifiates. It will ask you for a root cert password and a subordinate cert password. You will be asked for these passwords multiple times during certificate generation.

You will only need to keepy certs/nodeconf.key and certs/nodeconf_chain.crt on the computer running node-configurator. Keeping the other .key files on the computer running node-configurator is a mayor security issue.

NOTE: It is likely that your newly flashed nodes will have the wrong date set, which can cause problems with SSL. As of this writing, OpenWRT attitude adjustment (upon which the sudoWRT is based) seems to set the initial date to 2014-01-01.Since the SSL generated certificates are only valid starting from the date and time they were created, the nodes will refuse to connect to the node-configurator. You can edit the gen_certificates.sh scripts and change the STARTDATE variable to e.g. 13123101000001Z (January 31st, 2013, 00:00:01) before you generate the certificates, and you will have certificates that are valid from the earlier date. A prettier solution might be to set the firmware date before flashing, but realistically we'll sometimes want to generate new SSL certificates that are trusted by nodes that have been flashed a long time ago (e.g. if we have a stock of already flashed nodes and need to configure them from a new server), so this solution seems good.

### SSH keys ###

To generate ssh keys, use:

```
ssh-keygen -t rsa
```

Copy the pub key (e.g. id_rsa.pub) that you want to give root access to all configured nodes to the authorized_keys/ directory. It doesn't matter what their filenames are, so you can give them helpful names.

### Compiling firmware with new SSL key ###

You should get [the sudo mesh firmware](https://github.com/sudomesh/openwrt-firmware) and copy your generated ca_root.crt to openwrt-firmware/files/etc/certs/ca_root.crt

Follow the instructions in openwrt-firmware/README to compile the firmware containing the new certificate. Routers flashed with this firmware will automatically connect to your node-configurator if on the same LAN.

# Some assumptions #

Currently, to make all of this work, you need to be running avahi on the computer running the node configurator. Avahi must be configured with the hostname nodeconf.local (this requirement should be removed in future versions). It is also assumed that a DHCP server is running on the LAN. 

