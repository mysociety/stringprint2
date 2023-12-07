#!/bin/bash 


DOWNLOAD_URL=$(
    wget -qO- https://googlechromelabs.github.io/chrome-for-testing/known-good-versions-with-downloads.json |
    jq -r '.versions[] |
        select(.version == "'$(google-chrome --version | awk '{print $NF}' | cut -d. -f1,2,3,4 )'") |
        .downloads.chromedriver[] |
        select(.platform == "linux64") |
        .url'
)

wget -q "$DOWNLOAD_URL"
unzip chromedriver-linux64.zip
mv chromedriver-linux64/chromedriver /usr/bin/chromedriver
chown root:root /usr/bin/chromedriver
chmod +x /usr/bin/chromedriver
rm -f chromedriver-linux64.zip
