FROM python:3.14-bookworm

ENV DEBIAN_FRONTEND=noninteractive
ENV PATH="/root/.local/bin:$PATH"

# apt-key is gone in Debian 12, and the NodeSource repository layout changed
# with it - one keyring, one source, suite "nodistro"
RUN curl -fsSL https://deb.nodesource.com/gpgkey/nodesource-repo.gpg.key \
      | gpg --dearmor -o /usr/share/keyrings/nodesource.gpg \
      && echo 'deb [signed-by=/usr/share/keyrings/nodesource.gpg] https://deb.nodesource.com/node_22.x nodistro main' \
      > /etc/apt/sources.list.d/nodesource.list

RUN apt-get -qq update \
      && apt-get -qq install -y --no-install-recommends nodejs \
      && rm -rf /var/lib/apt/lists/*

# postcss is a peer dependency of postcss-cli and autoprefixer; without it
# `npx postcss --use autoprefixer` exits with ERR_MODULE_NOT_FOUND
RUN npm install -g sass postcss postcss-cli autoprefixer

COPY bin/docker-provision script/config/packages /install/

RUN chmod u+x /install/docker-provision && /install/docker-provision

COPY pyproject.toml poetry.loc[k] /
RUN curl -sSL https://install.python-poetry.org | python - \
      && echo 'export PATH="/root/.local/bin:$PATH"' > ~/.bashrc \
      && poetry config virtualenvs.create false \
      && poetry install
