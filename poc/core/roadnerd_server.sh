#!/bin/bash
# RoadNerd Server Launcher

# Activate virtual environment (honor RN_VENV override)
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
