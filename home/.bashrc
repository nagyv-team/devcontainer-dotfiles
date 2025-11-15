[ -f /etc/bash_completion ] && source /etc/bash_completion
[ -f /etc/bashrc ] && source /etc/bashrc
[ -f /etc/bash.bashrc ] && source /etc/bash.bashrc
[ -f "$HOME/.aliases" ] && source ~/.aliases

eval "$(direnv hook bash)"

export PNPM_HOME="/home/vscode/.local/share/pnpm"
case ":$PATH:" in
*":$PNPM_HOME:"*) ;;
*) export PATH="$PNPM_HOME:$PATH" ;;
esac

export PATH=$HOME/bin:"${KREW_ROOT:-$HOME/.krew}/bin:$PATH"
