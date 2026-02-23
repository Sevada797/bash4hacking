#!/bin/bash
# install-requirements.sh
# Bash4Hacking setup requirements script - run after 'bash setup.sh'

echo "[*] Installing Go and Python3 pip and moreutils (requires sudo)"
sudo apt install python3-pip golang moreutils

echo "[*] Installing Go tools for Bash4Hacking (subdomain/URL recon)..."

# Add GOPATH/bin to PATH for this session
export PATH=$PATH:$(go env GOPATH)/bin

# ─── Persist GOPATH/bin to the correct RC file ────────────────────────────────
GOPATH_EXPORT='export PATH=$PATH:$HOME/go/bin'
SHELL_NAME=$(basename "$SHELL")

if [ "$SHELL_NAME" = "zsh" ]; then
    RC_FILE="$HOME/.zshrc"
elif [ "$SHELL_NAME" = "bash" ]; then
    RC_FILE="$HOME/.bashrc"
else
    echo "⚠️  Something is wrong — env is neither zsh nor bash (detected: $SHELL_NAME)"
    echo "    Manually add this to your shell RC file:"
    echo "    $GOPATH_EXPORT"
    RC_FILE=""
fi

if [ -n "$RC_FILE" ]; then
    if ! grep -q 'go/bin' "$RC_FILE" 2>/dev/null; then
        echo -e "\n# Go tools path\n$GOPATH_EXPORT" >> "$RC_FILE"
        echo "✅ GOPATH/bin added to $RC_FILE"
        echo "   👉 Run 'source $RC_FILE' or restart terminal to apply"
    else
        echo "ℹ️  GOPATH/bin already in $RC_FILE — skipping"
    fi
fi
# ──────────────────────────────────────────────────────────────────────────────

# ---- Subdomain recon tools ----
go install github.com/projectdiscovery/subfinder/v2/cmd/subfinder@latest
go install github.com/tomnomnom/assetfinder@latest

# ---- HTTP probing ----
go install github.com/projectdiscovery/httpx/cmd/httpx@latest

# ---- URL collection ----
go install github.com/projectdiscovery/katana/cmd/katana@latest
go install github.com/tomnomnom/waybackurls@latest

# ---- Additional utilities ----
go install github.com/tomnomnom/qsreplace@latest
go install github.com/s0md3v/uro@latest

# ---- ffuf by joohoi ----
go install github.com/ffuf/ffuf/v2@latest

echo "[*] Installing Python packages..."
python3 -m pip install --upgrade pip
python3 -m pip install \
    aiohttp \
    anyio \
    httpx \
    openai \
    playwright \
    cryptography \
    urllib3 \
    requests

echo ""
echo "[*] Setup complete!"
