#!/bin/bash

bash ./bin/copy_dotfiles.sh

# Install claude code docs https://github.com/ericbuess/claude-code-docs/
curl -fsSL https://raw.githubusercontent.com/ericbuess/claude-code-docs/main/install.sh | bash
