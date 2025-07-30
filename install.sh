#!/bin/sh

mkdir -p ~/.config ~/.local/bin

if ! cd "$HOME/dotfiles" > /dev/null; then
	exit 1
fi

# alacritty/.config/alacritty
FOLDERS="
bin/bin
home/
claude/.claude
"

for i in $FOLDERS; do
	TARGET_DIR="$(echo "$i" | cut -d'/' -f2-)"
	mkdir -p "$HOME/$TARGET_DIR"
	find "$i" -mindepth 1 -maxdepth 1 -exec sh -xc "ln -sf ${HOME}/dotfiles/\$0 ${HOME}/${TARGET_DIR}/" {} \;
done
