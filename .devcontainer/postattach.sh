#!/bin/zsh

# Sync the project into a new environment, asserting the lockfile is up to date
uv sync  --locked

# Auto set up remote when pushing new branches
git config --global --add push.autoSetupRemote 1

# Allow precommit to install properly
git config --global --add safe.directory /workspace

# Install precommit hooks
pre-commit install && pre-commit install -t commit-msg

# Install claude code
#   NOTE: You may have to redo this, sometimes it doesn't
#   take after container rebuilds.
npm install -g @anthropic-ai/claude-code

# Install localtunnel
npm install -g localtunnel

# Set zsh history location
#     This is done in postAttach so it's not overridden by the oh-my-zsh devcontainer feature
export HISTFILE="/command-history/.zsh_history"

# Add aliases to zshrc file
echo '# Aliases to avoid typing "python manage.py" repeatedly' >> ~/.zshrc
echo 'alias dj="python manage.py"' >> ~/.zshrc
echo 'alias djmm="python manage.py makemigrations"' >> ~/.zshrc
echo 'alias djm="python manage.py migrate"' >> ~/.zshrc
echo 'alias djr="python manage.py runserver"' >> ~/.zshrc
echo 'alias djreset="python manage.py reset_db -c"' >> ~/.zshrc
echo 'alias djsh="python manage.py shell_plus"' >> ~/.zshrc
echo 'alias djsm="python manage.py showmigrations"' >> ~/.zshrc
echo 'alias djt="pytest backend/test"' >> ~/.zshrc
echo 'alias dju="python manage.py show_urls"' >> ~/.zshrc
