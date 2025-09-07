#!/bin/bash
# RoadNerd Client Launcher

# Activate virtual environment
source "$HOME/.roadnerd_venv/bin/activate"

# Run the client
python3 roadnerd_client.py "$@"
