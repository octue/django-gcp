FROM windpioneers/gdal-python:rational-swordtail-gdal-3.10.0-python-3.13-dev

# Bust any pre-existing apt cache
#     Solves https://askubuntu.com/questions/1388000/failed-to-fetch-deb-debian-org-debian-pool-main-l-linux-linux-libc-dev-5-10-70-1
#     Overcomes the fact that yarn don't bother putting their keys on the ring (required for installing sshd feature)...
#     https://github.com/yarnpkg/yarn/issues/7866#issuecomment-1404052064
RUN curl -sS https://dl.yarnpkg.com/debian/pubkey.gpg | sudo gpg --dearmour -o "/usr/share/keyrings/yarn-keyring.gpg" & \
    echo "deb [signed-by=/usr/share/keyrings/yarn-keyring.gpg] https://dl.yarnpkg.com/debian stable main" | tee /etc/apt/sources.list.d/yarn.list & \
    gpg --refresh-keys & \
    apt-get update -y

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
# RUN curl -sfL https://raw.githubusercontent.com/aquasecurity/trivy/main/contrib/install.sh | sh -s -- -b /usr/local/bin v0.67.2

# Install apt packages used by Claude Code features
# bubblewrap: process sandbox (reduced capability in containers)
# socat: proxied network access for domain allowlists
# jq: useful for writing hooks directly in settings.json
RUN apt-get update -y && apt-get install -y jq bubblewrap socat

# Ensure vscode user owns its bin and share directories
RUN mkdir -p ~/.local/share ~/.local/bin && chown -R vscode:vscode ~/.local

USER vscode

# Install claude code as vscode so autoupdate works
# RUN curl -fsSL https://claude.ai/install.sh | bash
# ENV PATH="/home/vscode/.local/bin:${PATH}"
