FROM python:3.8-buster

ENV DEBIAN_FRONTEND noninteractive

RUN curl -s https://deb.nodesource.com/gpgkey/nodesource.gpg.key | apt-key add - \
      && echo 'deb https://deb.nodesource.com/node_14.x buster main' > /etc/apt/sources.list.d/nodesource.list

RUN apt-get -qq update \
      && apt-get -qq install \
            nodejs \
         --no-install-recommends \
      && rm -rf /var/lib/apt/lists/*

RUN npm install -g sass postcss-cli autoprefixer

COPY bin/chrome_setup.bash bin/docker-provision script/config/packages /install/

RUN chmod u+x /install/docker-provision && /install/docker-provision

COPY requirements.txt /install/
RUN pip install -r /install/requirements.txt