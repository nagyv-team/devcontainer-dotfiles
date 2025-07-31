#!/bin/sh

if ! command -v direnv &> /dev/null; then
    echo "direnv not found"
    exit 0
fi

echo "Direnv: Updating /etc/bash.bashrc and /etc/zsh/zshrc..."
if [[ -f /etc/bash.bashrc ]]; then
    echo -e 'eval "$(direnv hook bash)"' >> /etc/bash.bashrc
fi
if [ -f "/etc/zsh/zshrc" ]; then
    echo -e 'eval "$(direnv hook zsh)"' >> /etc/zsh/zshrc
fi
