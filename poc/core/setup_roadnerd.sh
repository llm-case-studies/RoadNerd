#!/bin/bash
# RoadNerd Setup Script - Handles all dependencies properly

set -e  # Exit on error

echo "╦═╗┌─┐┌─┐┌┬┐╔╗╔┌─┐┬─┐┌┬┐  ╔═╗┌─┐┌┬┐┬ ┬┌─┐"
echo "╠╦╝│ │├─┤ ││║║║├┤ ├┬┘ ││  ╚═╗├┤  │ │ │├─┘"
echo "╩╚═└─┘┴ ┴─┴┘╝╚╝└─┘┴└──┴┘  ╚═╝└─┘ ┴ └─┘┴  "
echo ""
echo "Setting up RoadNerd Server Environment..."
echo "=========================================="

# Detect OS
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    OS="linux"
    DISTRO=$(lsb_release -si 2>/dev/null || echo "Unknown")
elif [[ "$OSTYPE" == "darwin"* ]]; then
    OS="macos"
else
    OS="unknown"
fi

echo "Detected OS: $OS ($DISTRO)"

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Step 1: Install system dependencies
echo ""
echo "Step 1: Installing system dependencies..."
echo "-----------------------------------------"

if [ "$OS" = "linux" ]; then
    # Update package list
    sudo apt-get update
    
    # Install Python and venv support
    sudo apt-get install -y python3 python3-venv python3-pip
    
    # Install system packages (fallback option)
    echo "Installing Python packages via apt..."
    sudo apt-get install -y python3-flask python3-requests || true
    
    # Install curl for Ollama
    sudo apt-get install -y curl
fi

# Step 2: Setup Python environment
echo ""
echo "Step 2: Setting up Python environment..."
echo "-----------------------------------------"

VENV_DIR="${RN_VENV:-$HOME/.roadnerd_venv}"

# Create virtual environment if it doesn't exist
if [ ! -d "$VENV_DIR" ]; then
    echo "Creating virtual environment at $VENV_DIR"
    python3 -m venv "$VENV_DIR"
fi

# Activate virtual environment
if [ -d "$VENV_DIR" ]; then
  # shellcheck disable=SC1090
  source "$VENV_DIR/bin/activate"
else
  echo "Creating virtual environment at $VENV_DIR"
  python3 -m venv "$VENV_DIR"
  # shellcheck disable=SC1090
  source "$VENV_DIR/bin/activate"
fi

# Upgrade pip
pip install --upgrade pip

# Install Python packages
echo "Installing Python packages..."
pip install flask flask-cors requests

# Step 3: Install Ollama (if not present)
echo ""
echo "Step 3: Checking Ollama installation..."
echo "-----------------------------------------"

if ! command_exists ollama; then
    echo "Ollama not found. Installing..."
    curl -fsSL https://ollama.com/install.sh | sh
else
    echo "✓ Ollama is already installed"
fi

# Step 4: Setup Ollama model
echo ""
echo "Step 4: Setting up LLM model..."
echo "-----------------------------------------"

# Start Ollama service
echo "Starting Ollama service..."
ollama serve > /dev/null 2>&1 &
OLLAMA_PID=$!
sleep 3

# Pull a lightweight model
echo "Downloading LLM model (this may take a few minutes)..."
ollama pull llama3.2:3b || ollama pull tinyllama || echo "Model download failed - you can retry later"

# Step 5: Create launcher scripts
echo ""
echo "Step 5: Creating launcher scripts..."
echo "-----------------------------------------"

# Create server launcher
cat > "$HOME/roadnerd_server.sh" << 'EOF'
#!/bin/bash
# RoadNerd Server Launcher

# Activate virtual environment (honor RN_VENV)
VENV_DIR="${RN_VENV:-$HOME/.roadnerd_venv}"
if [ -d "$VENV_DIR" ]; then
  # shellcheck disable=SC1090
  source "$VENV_DIR/bin/activate"
else
  echo "Warning: venv not found at $VENV_DIR; continuing without activation." >&2
fi

# Ensure Ollama is running
if ! pgrep -x "ollama" > /dev/null; then
    echo "Starting Ollama..."
    ollama serve > /dev/null 2>&1 &
    sleep 2
fi

# Run the server
echo "Starting RoadNerd Server..."
python3 roadnerd_server.py
EOF

chmod +x "$HOME/roadnerd_server.sh"

# Create client launcher
cat > "$HOME/roadnerd_client.sh" << 'EOF'
#!/bin/bash
# RoadNerd Client Launcher

# Activate virtual environment (honor RN_VENV)
VENV_DIR="${RN_VENV:-$HOME/.roadnerd_venv}"
if [ -d "$VENV_DIR" ]; then
  # shellcheck disable=SC1090
  source "$VENV_DIR/bin/activate"
else
  echo "Warning: venv not found at $VENV_DIR; continuing without activation." >&2
fi

# Run the client
python3 roadnerd_client.py "$@"
EOF

chmod +x "$HOME/roadnerd_client.sh"

# Step 6: Setup USB networking helper
echo ""
echo "Step 6: Creating USB network helper..."
echo "-----------------------------------------"

cat > "$HOME/enable_usb_tethering.sh" << 'EOF'
#!/bin/bash
# Enable USB tethering for RoadNerd

echo "RoadNerd USB Tethering Setup"
echo "============================"
echo ""
echo "Option 1: GUI Method (Easiest)"
echo "1. Open Settings -> Network"
echo "2. Find 'USB Ethernet' or similar"
echo "3. Enable 'Share connection'"
echo ""
echo "Option 2: Command Line"
echo "Run: nmcli device connect usb0"
echo ""
echo "Option 3: Manual Setup"
echo "Run these commands:"
echo "  sudo ip link set usb0 up"
echo "  sudo ip addr add 192.168.42.1/24 dev usb0"
echo ""
echo "After enabling, the client laptop should connect to:"
echo "  http://192.168.42.1:8080"
EOF

chmod +x "$HOME/enable_usb_tethering.sh"

# Step 7: Final setup
echo ""
echo "Step 7: Finalizing setup..."
echo "-----------------------------------------"

# Create roadnerd directory
ROADNERD_DIR="$HOME/roadnerd"
mkdir -p "$ROADNERD_DIR"

# Save configuration
cat > "$ROADNERD_DIR/config.json" << EOF
{
    "llm_backend": "ollama",
    "model": "llama3.2:3b",
    "port": 8080,
    "safe_mode": true,
    "venv_path": "$VENV_DIR"
}
EOF

echo "✓ Configuration saved to $ROADNERD_DIR/config.json"

# Write artifacts manifest for cleanup
ARTIFACTS_JSON="$ROADNERD_DIR/artifacts.json"
cat > "$ARTIFACTS_JSON" << EOF
{
  "created_at": "$(date -Iseconds)",
  "venv_path": "$VENV_DIR",
  "files": [
    "$HOME/roadnerd_server.sh",
    "$HOME/roadnerd_client.sh",
    "$HOME/enable_usb_tethering.sh",
    "$ROADNERD_DIR/config.json"
  ],
  "logs_dir": "${RN_LOG_DIR:-$HOME/.roadnerd/logs}",
  "attempted_apt": ["python3", "python3-venv", "python3-pip", "curl", "python3-flask", "python3-requests"],
  "pip_packages": ["flask", "flask-cors", "requests"]
}
EOF

echo "✓ Artifacts manifest: $ARTIFACTS_JSON"

# Create cleanup script
cat > "$HOME/roadnerd_cleanup.sh" << 'EOF'
#!/usr/bin/env bash
set -euo pipefail

ARTIFACTS="$HOME/roadnerd/artifacts.json"
PURGE_MODELS=false
PURGE_LOGS=false
DRY_RUN=false

usage(){
  cat << USAGE
RoadNerd Cleanup
Usage: $0 [--purge-models] [--purge-logs] [--dry-run]
USAGE
}

for arg in "$@"; do
  case "$arg" in
    --purge-models) PURGE_MODELS=true ;;
    --purge-logs) PURGE_LOGS=true ;;
    --dry-run) DRY_RUN=true ;;
    -h|--help) usage; exit 0 ;;
  esac
done

py(){ python3 - "$@" << 'PY'
import json, os, sys
from pathlib import Path
art = Path(os.environ.get('ARTIFACTS'))
data = {}
if art.exists():
    data = json.loads(art.read_text())
print(json.dumps(data))
PY
}

DATA="$(py)"
venv_path="$(printf '%s' "$DATA" | python3 -c 'import sys,json; d=json.load(sys.stdin); print(d.get("venv_path",""))')"
logs_dir="$(printf '%s' "$DATA" | python3 -c 'import sys,json; d=json.load(sys.stdin); print(d.get("logs_dir",""))')"

echo "Cleanup plan:"
echo "  venv: $venv_path"
echo "  logs_dir: $logs_dir (purge_logs=$PURGE_LOGS)"
echo "  purge_models: $PURGE_MODELS"

do_rm(){
  local path="$1"
  if [ -e "$path" ]; then
    if [ "$DRY_RUN" = true ]; then echo "DRY: rm -rf $path"; else rm -rf "$path"; fi
  fi
}

# Remove launchers and config
for f in $(printf '%s' "$DATA" | python3 -c 'import sys,json; d=json.load(sys.stdin); print("\n".join(d.get("files",[])))'); do
  echo "Removing $f"; do_rm "$f";
done

# Remove venv
if [ -n "$venv_path" ]; then echo "Removing venv $venv_path"; do_rm "$venv_path"; fi

# Remove logs if requested
if [ "$PURGE_LOGS" = true ] && [ -n "$logs_dir" ]; then echo "Purging logs $logs_dir"; do_rm "$logs_dir"; fi

# Remove models if requested
if [ "$PURGE_MODELS" = true ]; then
  echo "Purging Ollama models (~/.ollama)"
  if command -v ollama >/dev/null 2>&1; then
    if [ "$DRY_RUN" = true ]; then echo "DRY: ollama rm -a"; else ollama rm -a || true; fi
  fi
  do_rm "$HOME/.ollama"
fi

echo "Cleanup complete."
EOF

chmod +x "$HOME/roadnerd_cleanup.sh"
echo "✓ Cleanup script: $HOME/roadnerd_cleanup.sh"

# Success message
echo ""
echo "=========================================="
echo "✅ RoadNerd Setup Complete!"
echo "=========================================="
echo ""
echo "📁 Files created:"
echo "   • $HOME/roadnerd_server.sh - Start the server"
echo "   • $HOME/roadnerd_client.sh - Start the client"
echo "   • $HOME/enable_usb_tethering.sh - USB setup helper"
echo ""
echo "🚀 Quick Start:"
echo "   1. Save roadnerd_server.py to this directory"
echo "   2. Run: ./roadnerd_server.sh"
echo "   3. Connect USB cable to laptop"
echo "   4. Enable USB tethering (see ./enable_usb_tethering.sh)"
echo "   5. On laptop, run the client"
echo ""
echo "💡 Tips:"
echo "   • The virtual environment is at: $VENV_DIR"
echo "   • To manually activate it: source $VENV_DIR/bin/activate"
echo "   • Ollama models are stored in: ~/.ollama/models"
echo ""

# Cleanup
if [ ! -z "$OLLAMA_PID" ]; then
    kill $OLLAMA_PID 2>/dev/null || true
fi

echo "Ready to go! 🚀"
