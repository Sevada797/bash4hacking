#!/bin/bash

# Determine which RC file to use (main check: $SHELL)
SHELL_NAME=$(basename "$SHELL")

if [ "$SHELL_NAME" = "zsh" ]; then
    RC_FILE="$HOME/.zshrc"
elif [ "$SHELL_NAME" = "bash" ]; then
    RC_FILE="$HOME/.bashrc"
elif [ -n "$ZSH_VERSION" ]; then
    RC_FILE="$HOME/.zshrc"
elif [ -n "$BASH_VERSION" ]; then
    RC_FILE="$HOME/.bashrc"
else
    # Default fallback to .bashrc
    RC_FILE="$HOME/.bashrc"
fi


IMPORT_MARK="# IMPORT for Bash4hacking"
SRC_DIR="$(pwd)/src"
BFH_PATH="$(pwd)"

# Universal source command (POSIX-safe)
IMPORT_CMD='for file in '"$SRC_DIR"'/*; do [ -f "$file" ] && . "$file"; done'

# Check if already added
if ! grep -qi "bash4hacking" "$RC_FILE"; then
    {
        echo -e "\n##############################"
        echo -e "## IMPORT for Bash4hacking"
        echo -e "##############################"
        echo "$IMPORT_CMD"
        echo "BFH_PATH=\"$BFH_PATH\""
        echo -e "################################"
        echo -e "## ENDOF IMPORT for Bash4hacking"
        echo -e "################################"
    } >> "$RC_FILE"
    echo -e "\n✅ Bash4hacking setup added to $RC_FILE"
else
    echo -e "\nℹ️ Bash4hacking import already exists in $RC_FILE"
fi

# Reload the correct RC file
if [ -n "$BASH_VERSION" ]; then
    . "$RC_FILE"
    echo -e "🔁 Reloaded $RC_FILE\n✅ Setup done!"
elif [ -n "$ZSH_VERSION" ]; then
    source "$RC_FILE"
    echo -e "🔁 Reloaded $RC_FILE\n✅ Setup done!"
else
    echo -e "⚠️ Unknown shell — please restart your terminal or run:\n   source $RC_FILE"
fi
