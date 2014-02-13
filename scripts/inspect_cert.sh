#!/bin/sh

if [ ! $# -eq 1 ]; then
	echo "Usage: ${0} <mycert.crt>"
	exit 1
fi

openssl x509 -in $1 -noout -text
