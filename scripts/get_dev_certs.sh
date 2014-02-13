#!/bin/sh

echo "Retrieving development certs"
git clone --depth=1 https://github.com/sudomesh/dev-certs

if [ ! $? -eq 0 ]; then
    echo "Error retrieving dev certificates from github"
    exit 1
fi

ln -s dev-certs/ssh_certs/id_rsa.pub authorized_keys/dev_key.pub

if [ ! $? -eq 0 ]; then
    echo "Error creating symlink authorized_keys/dev_key.pub"
    exit 1
fi

ln -s dev-certs/ssl_certs certs

if [ ! $? -eq 0 ]; then
    echo "Error creating symlink certs/"
    exit 1
fi

echo " "
echo "Your SSL certs and keys are in certs/"
echo "Your SSH public key and private key are in dev-certs/ssh_certs/"
echo " "
echo "After configuring a node, you should be able to log in using the command:"
echo " "
echo "  ssh -i dev-certs/ssh_certs/id_rsa root@<ip_of_node>"
echo " "



