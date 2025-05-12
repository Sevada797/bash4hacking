BASHRC="$HOME/.bashrc"
IMPORT_MARK="# IMPORT for Bash4hacking"
IMPORT_CMD="source $(pwd)/src/*"

# Check if already added
if ! grep -qi "bash4hacking" "$BASHRC"; then
    {
        echo -e "\n##############################"
        echo -e "## IMPORT for Bash4hacking"
        echo -e "##############################"
        echo "$IMPORT_CMD"
    } >> "$BASHRC"
    echo -e "\n✅ Bash4hacking setup added to ~/.bashrc"
else
    echo -e "\nℹ️ Bash4hacking import already exists in ~/.bashrc"
fi

# Reload .bashrc
source "$BASHRC"
echo -e "🔁 Reloaded ~/.bashrc\n✅ Setup done!"
