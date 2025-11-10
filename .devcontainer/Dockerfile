FROM windpioneers/gdal-python:rational-swordtail-gdal-3.10.0-python-3.13-dev

# Use system environment for UV instead of .venv (we're already in a devcontainer)
ENV UV_PROJECT_ENVIRONMENT="/usr/local/"

# Install localtunnel
RUN npm install -g localtunnel
