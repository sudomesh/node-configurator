# Introduction #

This is the sudo mesh node configurator. The idea is that you flash a node with the sudo mesh firmware, then run the node configurator on e.g. your laptop and connect your laptop and the flashed node to the same LAN and boot the node. The node will find the node configurator using DNS-SD, connect to the node using SSL (ensuring that the node configurator is an official authorized configurator) and ask for updates. The configurator will send one or more .ipk files and their md5 checksums and the node will write these to /tmp, verify their checksums, install them and reboot.

This piece of software is in an early but usable state.

# Prerequisites #

For a typical modern Debian / Ubuntu machine first install some prerequisites:

```
sudo aptitude install python avahi-daemon python-virtualenv python-pip python-openssl python-dbus python-avahi build-essential libssl-dev expect fakeroot python-dev dropbear whois
```

Install the extra required python packages in a virtual python environment:

```
./scripts/install_python_prereqs
```

You also need to download the [node database](https://github.com/sudomesh/node-database).

# Setup #

## Configuration ##

Copy config/server.json.example to config.json and edit it to suit your needs.

* hostname: The hostname or ip where the node configurator server listens for node configurator client connections.
* port: The port where the node configurator server listens for node configurator client connections.
* web_hostname: The hostname or ip where the node configurator web server listens for web browsers to connect.
* web_port: The port where the node configurator web server listens for web browsers to connect.
* db_host: The hostname/IP and port (separated by a colon) where your [node database](https://github.com/sudomesh/node-database) is running.
* wordlist: The word list used to generate wifi SSID names.
* configure_cmd: The command to be run on the node in order to configure it after it has received the configuration from the node-configurator server. If the sub-string \<file\> is present, then it will be substituted by the name of the file sent to the node by the node-configurator (usually an ipk file) before being run.
* post_configure_cmd: The command to be run on the node after successfully completing the configure_cmd successfully (usually "reboot").
* service_type: The service type to use for node-configurator DNS-SD announcements (via Avahi).

There are other configuration options, but you shouldn't change them as it may break the code.

## Avahi ##

You need to be running avahi. This is normally already the ase on Debian / Ubuntu. The node configurator uses Avahi to announce itself using DNS-SD.

Avahi must be configured with the hostname nodeconf.local (this requirement should be removed in future versions).

# DHCP server #

The newly flashed nodes will expect a DHCP server to give them an IP on the same subnet as the node-configurator. You can easily set up dnsmasq (a combined DNS and DHCP server) to do this job.

First install dnsmasq:

```
sudo aptitude install dnsmasq
```

Ensure that dnsmasq is enabled. The file /etc/default/dnsmasq should include the line:

```
ENABLED=1
```

Configure dnsmasq to give out IPs in the subnet where the node configurator is listening. E.g. if you have hostname set to 10.0.0.1" in config/server.json then you can simply add the following line to /etc/dnsmasq.conf:

```
dhcp-range=10.0.0.10,10.0.0.250
```

Then ensure that one of your computer's network interfaces (the one you'll be connecting to nodes) has the IP 10.0.0.1:

```
sudo ifconfig eth0 10.0.0.1 netmask 255.0.0.0 up
```

NOTE: The above command won't do anything if you're using Network Manager, which is the default on Ubuntu desktops. You'll have to use Network Manager to configure a static IP or tell Network Manager to ignore that specific network interface (eth0).

Finally, restart dnsmasq:

```
sudo /etc/init.d/dnsmasq restart
```

## Node database ##

You need to have a running instance of the [node database](https://github.com/sudomesh/node-database). The node database is used for tracking and assigning unique static IP addresses for nodes and also keeps track of contat information for node ownwers initial passwords assigned to nodes.

If you just download and run it, it will come up on localhost port 3000.

## Security ##

IMPORTANT: PLEASE READ THE FOLLOWING.

If you are configuring nodes that are to be managed by an existing group, such as sudo mesh, then you need to obtain the SSL certificates and SSH keys from that group. 

If you are not planning to deploy your nodes, but just want to test things out or work on development, then you can just use the insecure dev certificates by running:

  ./scripts/get_dev_certs.sh

Using the dev certificates is easy because it means you don't have to build your own firmware.

If you are setting up your own node(s) that you want to manage yourself or as part of a new mesh networking group/organization, then follow the instructions in the following sections. 

You should generate both SSL certs and SSH keys on a secured computer that is not (and preferably never has been) plugged in to a network. You should keep the root certificate key file in multiple very secure locations, since they are only needed when revoking or creating new subordinate certificates. You should keep the subordinate certificate key on a secure and disconnected computer, as it will only be used to generate certificates for new mesh services. You should keep the private SSH key on a disconnected computer, and only connect it to the network when absolutely needed. In the future, hopefully we can get around having to keep the SSH key on an internet-connected computer at all.

If you generate your own SSL certs and SSH keys, then you will have to compile your own firmware. 

### Choosing passwords ###

You should use reasonably secure passwords. You probably won't be able to remember them, as you won't be using them very often, but you could use xkcd-style passwords to make them easier to memorize for short periods of time:

* [redacted's xkcd-style password generator](https://github.com/redacted/XKCD-password-generator)

### SSL certificates ###

To generate a set of SSL certifiates run:

```
./scripts/gen_certificates.sh
```

It will ask you for a root cert password and a subordinate cert password. You will be asked for these passwords multiple times during certificate generation.

The script generates both a self-signed root certificate, a subordinate certificate signed by the root certificate and a certificate for nodeconf.local signed by the subordinate certificate.

You will only need to keep certs/nodeconf.key and certs/nodeconf_chain.crt on the computer running node-configurator. Keeping the other .key files on the computer running node-configurator is a mayor security issue.

NOTE: It is likely that your newly flashed nodes will have the wrong date set, which can cause problems with SSL. As of this writing, OpenWRT attitude adjustment (upon which the sudoWRT is based) seems to set the initial date to some time in January 2014. Since the generated SSL certificates are only valid starting from the date and time they were created, the nodes will refuse to connect to the node-configurator since it believes the certificates are slated to become valid at some point in the future. You can edit the gen_certificates.sh scripts and change the STARTDATE variable to e.g. 13123101000001Z (January 31st, 2013, 00:00:01) before you generate the certificates, and you will have certificates that are valid from the earlier date. A prettier solution might be to set the firmware date correctly before flashing, but realistically we'll sometimes want to generate new SSL certificates that are trusted by nodes that have been flashed a long time ago (e.g. if we have a stock of already flashed nodes and need to configure them from a new server), so backdating SSL new certificates seems like a good solution.

### SSH keys ###

To generate ssh keys, use:

```
ssh-keygen -t rsa
```

Copy the pub key (e.g. id_rsa.pub) that you want to give root access to all configured nodes to the authorized_keys/ directory. It doesn't matter what their filenames are, so you can give them helpful names.

### Compiling firmware with new SSL key ###

You should get [the sudo mesh firmware](https://github.com/sudomesh/openwrt-firmware) and copy your generated ca_root.crt to openwrt-firmware/files/etc/certs/ca_root.crt

Follow the instructions in openwrt-firmware/README to compile the firmware containing the new certificate. Routers flashed with this firmware will automatically connect to your node-configurator if on the same LAN.

### Security of node database ###

For a production system, you want to ensure that the node database is kept secure and backed up. Access to the node database means access to all nodes where the users haven't changed the initial passwords (realistically probably most nodes) and private contact info of node owners.

# Running #

To start the server, first ensure that Avahi and the node database are running, then run:

  ./start_server.sh

# Using #

The server should inform you of the URL to access. It will be something like:

```
https://10.0.0.1:8080/
```

Your browser will give you a security warning the first time you access that address. 

The web app will automatically show new nodes in the left-hand panel as they connect. You don't need to refresh/reload unless you restart the node configurator server.

Once the node shows up in the left-hand panel. Click it.

Now fill out the form and click "Configure node". A loading animation will appear while the node configures and a message will appear at the top of the page when the configuration has completed (whether it fails or succeeds).

Your node should now be rebooting after having been suessfully configured!

# License #

This software is licensed under the GPLv3.