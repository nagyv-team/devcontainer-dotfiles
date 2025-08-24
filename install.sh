#!/bin/bash

bash ./bin/copy_dotfiles.sh

# Install claude code docs https://github.com/ericbuess/claude-code-docs/
curl -fsSL https://raw.githubusercontent.com/ericbuess/claude-code-docs/main/install.sh | bash

# Add codebase index support /index command https://github.com/ericbuess/claude-code-project-index/
curl -fsSL https://raw.githubusercontent.com/ericbuess/claude-code-project-index/main/install.sh | bash

git config --global core.excludesfile ~/.gitignore

# Initialize virtualenv
python -m venv ~/.venv_dotfiles
source ~/.venv_dotfiles/bin/activate
pip install -r requirements.txt
deactivate