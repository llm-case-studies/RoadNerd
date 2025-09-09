#!/bin/bash
# RoadNerd Client Launcher

# Activate virtual environment (honor RN_VENV override)
VENV_DIR="${RN_VENV:-$HOME/.roadnerd_venv}"
if [ -d "$VENV_DIR" ]; then
  # shellcheck disable=SC1090
  source "$VENV_DIR/bin/activate"
else
  echo "Warning: venv not found at $VENV_DIR; continuing without activation." >&2
fi

# Run the client
python3 roadnerd_client.py "$@"
