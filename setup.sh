BASHRC="$HOME/.bashrc"
IMPORT_MARK="# IMPORT for Bash4hacking"
SRC_DIR="$(pwd)/src"

# Command that loops and sources only regular files
IMPORT_CMD='for file in '"$SRC_DIR"'/*; do [ -f "$file" ] && source "$file"; done'


# Check if already added
if ! grep -qi "bash4hacking" "$BASHRC"; then
    {
        echo -e "\n##############################"
        echo -e "## IMPORT for Bash4hacking"
        echo -e "##############################"
        echo "$IMPORT_CMD"
        echo "BFH_PATH=\""$(pwd)"\""
        echo -e "################################"
        echo -e "## ENDOF IMPORT for Bash4hacking"
        echo -e "################################"


    } >> "$BASHRC"
    echo -e "\n✅ Bash4hacking setup added to ~/.bashrc"
else
    echo -e "\nℹ️ Bash4hacking import already exists in ~/.bashrc"
fi

# Reload .bashrc
source "$BASHRC"
echo -e "🔁 Reloaded ~/.bashrc\n✅ Setup done!"
