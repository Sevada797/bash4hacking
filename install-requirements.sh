#!/bin/bash
# install-requirements.sh
# Bash4Hacking setup requirements script - run after 'bash setup.sh'


echo "[*] Installing Go tools for Bash4Hacking (subdomain/URL recon)..."

# Add GOPATH/bin to PATH
export PATH=$PATH:$(go env GOPATH)/bin

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
