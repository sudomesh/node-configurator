#!/bin/sh
# a script for generating replacement dropbear ssh host keys.

/usr/bin/dropbearkey -t rsa -f dropbear_rsa_host_key -s 4096
/usr/bin/dropbearkey -t dss -f dropbear_dss_host_key

