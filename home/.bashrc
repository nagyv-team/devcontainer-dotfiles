[ -f /etc/bash_completion ] && source /etc/bash_completion
[ -f /etc/bashrc ] && source /etc/bashrc
[ -f /etc/bash.bashrc ] && source /etc/bash.bashrc
[ -f "$HOME/.aliases" ] && source ~/.aliases

eval "$(direnv hook bash)"
export PATH=$HOME/bin:$PATH
