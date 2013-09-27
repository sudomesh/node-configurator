#!/bin/bash

#######################################################
##
## Use this script to generate your own set of SSL/TLS
## certificates if you don't want to use the sudomesh
## certificates. This could be because you are starting
## your own mesh organization and want to manage the
## software updates to your nodes separately from the
## sudomesh updates.
## 
## In order for these certificates to be trusted by the
## mesh nodes, you must add them to the list of trusted
## root certificates in the mesh firmware (that you
## should fork from the sudomesh firmware). 
## TODO: Document how to do this.
##
## Three key/certificate sets are generated:
## 
## A key/cert set is generated for the root CA. The key 
## file for the root CA is password protected and should 
## be kept in a very secure location. It is only ever 
## needed if you want to create or revoke a subordinate 
## CA certificate. The root CA cert expires after 10 years. 
## 
## A key/cert set is generated for the subordinate CA.
## The subordinate CA certificate is signed by the root CA
## and is in turn used to sign the actual certificates used 
## to secure communications between nodes. The subordinate 
## CA and all certificates signed by the subordinate CA can
## be revoked using the root CA key. The key file for the 
## subordinate CA is password protected and should be kept
## secure. The subordinate CA cert expires after 10 years. 
##
## A key/cert set is generated for use by trusted hosts
## in the network. E.g. the servers used for initial
## configuration of new nodes. It is signed by the 
## subordinate CA. The key is not password protected.
## Keep the key on the nodeconf server and keep it secret. 
## The key expires in 2 years.
## 
## This script generates the following files:
##   
##   ca_root.key: The key file for your root CA.
##   ca_root.crt: The root CA certificate.
##
##   ca_sub.key: The key file for the subordinate CA.
##   ca_sub.crt: The subordinate CA certificate.
##   
##   nodeconf.key: The key file for the node conf cert.
##   nodeconf.crt: The certificate for the node conf server.
## 
#######################################################

ORGANIZATION=sudomesh
DOMAIN=sudomesh.org
COUNTRY=US
STATE=CA

NODECONF_DOMAIN=nodeconf.local

# default to 256 bit AES encryption with passphrase
PASS_OPTION="-aes256"

function die {
    rm -f certs/ca_sub.csr
    rm -f certs/nodeconf.csr
    rm -f certs/serial
    rm -f certs/crlnumber
    rm -f certs/index.txt
    rm -f certs/.rand
    exit 1
}

if [ $# -gt 0 ]; then

    if [ "$1" = "-h" ]; then
        echo "This script generates a set of OpenSSL certificates"
        echo "View script comments with for more info:"
        echo " "
        echo "  less ${0}"
        echo " "
        echo "Usage: ${0} [nopass]"
        echo "  -f: Delete all existing certs. Removes certs/ directory."
        echo "  -h: Print this help text"
        echo " "
        echo "  nopass: Do not password-protect private keys." 
        echo "          WARNING: Use for testing only!"
        echo " "
        exit 0

    elif [ "$1" = "nopass" ] || [ "$2" = "nopass" ]; then
        PASS_OPTION=""

        echo "!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!"
        echo "!!           WARNING            !!"
        echo "!!    passphrase turned off     !!"
        echo "!! private keys are unencrypted !!"
        echo "!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!"
        echo " "
    fi
fi


if [ -d "certs" ] || [ -f "certs" ]; then
    if [ $# -gt 0 ] && [ "$1" = "-f" ]; then
        echo "Overwriting existing files."
        rm -rf certs
    else
        echo "certs/ directory already exists. Aborting."
        echo "Re-run command with -f to overwrite existing files."
        die
    fi
fi

mkdir -p certs
chmod 700 certs

if [ ! $? -eq 0 ]; then
    echo "Error creating certs/ directory"
    die
fi

# These are needed for openssl to function
# see: http://www.openssl.org/docs/apps/ca.html
echo "0100" > certs/serial
echo "0100" > certs/crlnumber
touch certs/index.txt

# Random numbers
touch certs/.rand
chmod 600 certs/.rand

echo "== Generating random numbers =="
echo " "
openssl rand -out certs/.rand 4096

if [ ! $? -eq 0 ]; then
    echo "Error generating random numbers"
    die
fi

# root CA key
touch certs/ca_root.key
chmod 600 certs/ca_root.key

echo "== Generating root CA key =="
echo " "
openssl genrsa -out certs/ca_root.key $PASS_OPTION -rand certs/.rand 4096

if [ ! $? -eq 0 ]; then
    echo "Error generating root CA key"
    die
fi

# root CA certificate
echo "== Generating root CA certificate =="
echo " "
openssl req -batch -x509 -sha256 -new -subj "/C=${COUNTRY}/ST=${STATE}/O=${ORGANIZATION}/CN=${DOMAIN}" -key certs/ca_root.key -out certs/ca_root.crt -config openssl.cnf -days 3650 -extensions v3_ca

if [ ! $? -eq 0 ]; then
    echo "Error generating root CA certificate"
    die
fi

echo "== Generating random numbers =="
echo " "
openssl rand -out certs/.rand 4096

# subordinate CA key
touch certs/ca_sub.key
chmod 600 certs/ca_sub.key

echo "== Generating subordinate CA key =="
echo " "
openssl genrsa -out certs/ca_sub.key $PASS_OPTION -rand certs/.rand 4096

if [ ! $? -eq 0 ]; then
    echo "Error generating subordinate CA key"
    die
fi

# subordinate CA certificate signing request
echo "== Generating subordinate CA certificate signing request =="
echo " "
openssl req -batch -sha256 -new -subj "/C=${COUNTRY}/ST=${STATE}/O=${ORGANIZATION}/CN=${DOMAIN}" -key certs/ca_sub.key -out certs/ca_sub.csr -config openssl.cnf

if [ ! $? -eq 0 ]; then
    echo "Error generating subordinate CA certificate signing request"
    die
fi

echo "== Generating subordinate CA certificate =="
echo " "
openssl ca -batch -in certs/ca_sub.csr -keyfile certs/ca_root.key -cert certs/ca_root.crt -out certs/ca_sub.crt -outdir certs/ -config openssl.cnf -extensions v3_ca -days 3650

if [ ! $? -eq 0 ]; then
    echo "Error generating subordinate CA certificate"
    die
fi

echo "== Generating random numbers =="
echo " "
openssl rand -out certs/.rand 4096

# nodeconf server key
touch certs/nodeconf.key
chmod 600 certs/nodeconf.key

echo "== Generating nodeconf server key =="
echo " "
openssl genrsa -out certs/nodeconf.key -rand certs/.rand 4096

if [ ! $? -eq 0 ]; then
    echo "Error generating nodeconf server key"
    die
fi

# nodeconf server certificate signing request
echo "== Generating nodeconf server certificate signing request =="
echo " "
openssl req -batch -sha256 -new -subj "/C=${COUNTRY}/ST=${STATE}/O=${ORGANIZATION}/CN=${NODECONF_DOMAIN}" -key certs/nodeconf.key -out certs/nodeconf.csr -config openssl.cnf

if [ ! $? -eq 0 ]; then
    echo "Error generating nodeconf server certificate signing request"
    die
fi

echo "== Generating nodeconf server certificate =="
echo " "
openssl ca -batch -in certs/nodeconf.csr -keyfile certs/ca_sub.key -cert certs/ca_sub.crt -out certs/nodeconf.crt -outdir certs/ -config openssl.cnf -days 730

if [ ! $? -eq 0 ]; then
    echo "Error generating nodeconf server certificate"
    die
fi

echo "== Generating chained cert containing nodeconf and subordinate CA certs =="

cat certs/nodeconf.crt > certs/nodeconf_chain.crt
cat certs/ca_sub.crt >> certs/nodeconf_chain.crt

echo "== Cleanup =="
echo " "

# It seems like there is no way to prevent the
# "openssl ca" command from also creating these pem 
# files with the exact same content as the .crt files
rm -f certs/*.csr
rm -f certs/*.pem
chmod 755 certs


echo "Certificates and keys created successfully:"
echo " "
echo "  Root CA key:          certs/ca_root.key"
echo "  Root CA cert:         certs/ca_root.crt"
echo "    Expires in 10 years!"
echo " "
echo "  Subordinate CA key:   certs/ca_sub.key"
echo "  Subordinate CA cert:  certs/ca_sub.crt"
echo "    Expires in 10 years!"
echo " "
echo "  nodeconf server key:  certs/nodeconf.key"
echo "  nodeconf server cert: certs/nodeconf.crt"
echo "    Expires in 2 years!"
