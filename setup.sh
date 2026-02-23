#!/bin/bash

RC_FILE="$HOME/.bashrc"
ZSH_RC="$HOME/.zshrc"
SRC_DIR="$(pwd)/src"
BFH_PATH="$(pwd)"

IMPORT_CMD='for file in '"$SRC_DIR"'/*; do [ -f "$file" ] && . "$file"; done'

# ─── Inject into .bashrc ───────────────────────────────────────────────────────
if ! grep -qi "bash4hacking" "$RC_FILE" 2>/dev/null; then
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
    echo -e "\nℹ️  Bash4hacking import already exists in $RC_FILE"
fi

# ─── Inject b4 launcher into .zshrc (if zsh exists) ──────────────────────────
if [ -f "$ZSH_RC" ] && ! grep -q "b4 - Bash4Hacking launcher" "$ZSH_RC" 2>/dev/null; then
    cat >> "$ZSH_RC" <<EOF

##############################
# b4 - Bash4Hacking launcher
b4() {
  bash --rcfile <(
    cat ~/.bashrc 2>/dev/null
    echo 'for f in ${SRC_DIR}/*; do [ -f "\$f" ] && source "\$f"; done'
    echo "export BFH_PATH=\"${BFH_PATH}\""
    echo 'echo "📦 Loaded: \$(ls ${SRC_DIR} | tr '"'"'\n'"'"' '"'"' '"'"')"'
    echo 'echo "🔧 Bash4Hacking ready — type exit to return to zsh"'
  ) -i
}
##############################
EOF
    echo -e "✅ b4 launcher added to $ZSH_RC"
    echo -e "   👉 Run 'b4' from zsh to enter bash tool environment"
elif [ -f "$ZSH_RC" ]; then
    echo -e "ℹ️  b4 launcher already exists in $ZSH_RC"
fi

# ─── Reload .bashrc ───────────────────────────────────────────────────────────
. "$RC_FILE"
echo -e "🔁 Reloaded $RC_FILE\n✅ Setup done!"

echo "NOTE: run once 'bash install-requirements.sh' after 'bash setup.sh'"
