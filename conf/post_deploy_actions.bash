#!/bin/bash

# abort on any errors
set -e

# check that we are in the expected directory
cd `dirname $0`/..

wget https://bootstrap.pypa.io/get-pip.py
sudo python3 get-pip.py

# Upgrade setuptools, to avoid "invalid environment marker" error from
# cryptography package. https://github.com/ansible/ansible/issues/31741
sudo pip3 install --upgrade setuptools

sudo pip3 install --requirement requirements.txt

# make sure that there is no old code (the .py files may have been git deleted)
find . -name '*.pyc' -delete

# create or update database
sudo python3 manage.py migrate
script/server