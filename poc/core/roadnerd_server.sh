#!/bin/bash
# RoadNerd Server Launcher

# Activate virtual environment
source "$HOME/.roadnerd_venv/bin/activate"

# Ensure Ollama is running
if ! pgrep -x "ollama" > /dev/null; then
    echo "Starting Ollama..."
    ollama serve > /dev/null 2>&1 &
    sleep 2
fi

# Run the server
echo "Starting RoadNerd Server..."
python3 roadnerd_server.py
