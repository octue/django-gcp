FROM windpioneers/gdal-python:mid-swan-gdal-2.4.1-python-3.9-dev

# Bust any pre-existing apt cache
#     Solves: https://askubuntu.com/questions/1388000/failed-to-fetch-deb-debian-org-debian-pool-main-l-linux-linux-libc-dev-5-10-70-1
RUN apt-get update -y

# Tell zsh where you want to store history
#     We leave you to decide, but if you put this into a folder that's been mapped
#     into the container, then history will persist over container rebuilds :)
#
#     !!!IMPORTANT!!!
#     Make sure your .zsh_history file is NOT committed into your repository, as it can contain
#     sensitive information. So in this case, you should add
#         .devcontainer/.zsh_history
#     to your .gitignore file.
ENV HISTFILE="/workspace/.devcontainer/.zsh_history"

# Install the gcloud CLI
#    Required for dev builds only
#    See https://cloud.google.com/sdk/docs/install#deb
RUN echo "deb [signed-by=/usr/share/keyrings/cloud.google.gpg] http://packages.cloud.google.com/apt cloud-sdk main" | tee -a /etc/apt/sources.list.d/google-cloud-sdk.list && curl https://packages.cloud.google.com/apt/doc/apt-key.gpg | apt-key --keyring /usr/share/keyrings/cloud.google.gpg  add - && apt-get update -y && apt-get install google-cloud-cli -y

# Install poetry, cache poetry dependencies
#
#    Poetry usage in docker: https://stackoverflow.com/a/54763270/3556110
#    Caching package downloads with buildkit: https://pythonspeed.com/articles/docker-cache-pip-downloads/
#    Using pipx for python development utilities: https://github.com/microsoft/vscode-dev-containers/blob/main/containers/python-3/README.md#installing-or-updating-python-utilities
#
#    Why don't we do this for you in the gdal-python image???
#     - we may need to move the poetry version quicker than the base image
#     - because we can't conditionally mount a cache (for dev/slim images)
#     - poetry and dependencies can be agony, so we want per-project control at least for now
#     - if a repo is not using poetry, it doesn't make sense for us to force the presence of the tool
#
USER vscode
RUN curl -sSL https://raw.githubusercontent.com/python-poetry/poetry/master/get-poetry.py | python
ENV PATH "/home/vscode/.poetry/bin:$PATH"
RUN poetry config virtualenvs.create false
#
# It is possible to install dependencies with a cache, like this:
# COPY pyproject.toml poetry.lock ./
# RUN --mount=type=cache,id=dev-cache,target=/home/vscode/.cache \
#     poetry install --no-interaction --no-ansi
#
# However, at present it seems more reliable to do poetry install as a postcreate command (see devcontainer.json)
