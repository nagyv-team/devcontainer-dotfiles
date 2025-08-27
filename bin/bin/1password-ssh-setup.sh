#!/bin/bash

set -e

VAULT_NAME="devpod_at_rackspace-spot-ai-codespace-us"

# Check if argument is provided
if [ $# -eq 0 ]; then
    echo "Usage: $0 <key-item-name>"
    echo ""
    echo "This script fetches an SSH private key from 1Password and adds it to the SSH agent."
    echo ""
    echo "Arguments:"
    echo "  key-item-name    Name of the SSH key item in 1Password vault"
    echo ""
    echo "Example:"
    echo "  $0 GitHub"
    echo "  $0 \"Production Server Key\""
    echo ""
    echo "The key will be saved to ~/.ssh/<key-item-name>"
    exit 1
fi

KEY_ITEM_NAME="$1"
SSH_KEY_PATH="$HOME/.ssh/${KEY_ITEM_NAME}"

# Ensure 1Password CLI is authenticated
if ! op account get &>/dev/null; then
    echo "Please sign in to 1Password CLI first:"
    echo "op signin"
    exit 1
fi

# Retrieve private key from 1Password
echo "Fetching SSH private key '$KEY_ITEM_NAME' from 1Password..."

# If stored as SSH Key item:
op item get "$KEY_ITEM_NAME" --vault="$VAULT_NAME" --fields="private_key" --reveal | sed '1s/^"//; $s/"$//; 1{/^$/d}' > "$SSH_KEY_PATH"

# If stored as document:
# op document get "$KEY_ITEM_NAME" --vault="$VAULT_NAME" > "$SSH_KEY_PATH"

# Set proper permissions
chmod 600 "$SSH_KEY_PATH"

# Add key to SSH agent
ssh-add "$SSH_KEY_PATH"

echo "SSH key ${SSH_KEY_PATH} loaded from 1Password and added to SSH agent"

# Optional: Remove the temporary file after adding to agent
# rm "$SSH_KEY_PATH"
