#!/bin/bash

ORG=sudomesh
CRT_FILE="${ORG}_root.crt"

echo "This script will install the ${ORG} root CA certificate as a trusted certificate for your entire operating system. Proceed? [y/N]: "

sudo cp certs/ca_root.crt /usr/share/ca-certificates/extra/${CRT_FILE}

sudo echo -e "\nextra/${CRT_FILE}\n" >> /etc/ca-certificates.conf

sudo update-ca-certificates

echo "Root certificate for ${ORG} successfully installed!"


