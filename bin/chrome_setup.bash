#!/bin/bash 

VERSION=$( curl -s https://chromedriver.storage.googleapis.com/LATEST_RELEASE_$( google-chrome --version | awk '{print $NF}' | cut -d. -f1,2,3 ) )
wget -q https://chromedriver.storage.googleapis.com/${VERSION}/chromedriver_linux64.zip
unzip chromedriver_linux64.zip
mv chromedriver /usr/bin/chromedriver
chown root:root /usr/bin/chromedriver
chmod +x /usr/bin/chromedriver
rm -f chromedriver_linux64.zip
