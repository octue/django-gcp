FROM windpioneers/gdal-python:rational-swordtail-gdal-3.10.0-python-3.13-dev

# Use system environment for UV instead of .venv (we're already in a devcontainer)
ENV UV_PROJECT_ENVIRONMENT="/usr/local/"

ENV PROMPT_COMMAND='history -a'
ENV HISTFILE=/command-history/.zsh_history

# Install terraform-docs
RUN curl -sSLo ./terraform-docs.tar.gz https://terraform-docs.io/dl/v0.17.0/terraform-docs-v0.17.0-$(uname)-amd64.tar.gz && \
    tar -xzf terraform-docs.tar.gz && \
    chmod +x terraform-docs && \
    mv terraform-docs /usr/bin/terraform-docs

# Install tflint
RUN curl -s https://raw.githubusercontent.com/terraform-linters/tflint/master/install_linux.sh | bash

# Install trivy
RUN curl -sfL https://raw.githubusercontent.com/aquasecurity/trivy/main/contrib/install.sh | sudo sh -s -- -b /usr/local/bin v0.67.2


USER vscode
