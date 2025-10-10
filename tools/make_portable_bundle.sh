#!/usr/bin/env bash
set -euo pipefail

INCLUDE_MODELS=false
INCLUDE_DEPS=false
INTERACTIVE_MODELS=false
PRELOAD_MODELS=""
TARGET=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --include-models|-m) INCLUDE_MODELS=true; shift ;;
    --include-deps|-d) INCLUDE_DEPS=true; shift ;;
    --interactive-models|-i) INTERACTIVE_MODELS=true; INCLUDE_MODELS=true; shift ;;
    --preload-models) PRELOAD_MODELS="$2"; shift 2 ;;
    *) TARGET="$1"; shift ;;
  esac
done

if [ -z "${TARGET:-}" ]; then
  echo "Usage: $0 [OPTIONS] <target_dir>" >&2
  echo "Options:" >&2
  echo "  --include-models,-m: Bundle all locally cached Ollama models" >&2
  echo "  --interactive-models,-i: Interactive selection of models to bundle" >&2
  echo "  --preload-models 'model1,model2': Download and bundle specific models" >&2
  echo "  --include-deps,-d: Bundle Python dependencies for offline installation" >&2
  echo "" >&2
  echo "Examples:" >&2
  echo "  $0 --include-models /media/usb/bundle" >&2
  echo "  $0 --interactive-models --include-deps /tmp/roadnerd-bundle" >&2
  echo "  $0 --preload-models 'codellama:13b,llama3:8b' /tmp/bundle" >&2
  exit 1
fi

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"

# Model handling functions
list_available_models() {
  if ! command -v ollama >/dev/null 2>&1; then
    echo "Warning: Ollama not found. Models cannot be bundled." >&2
    return 1
  fi
  ollama list 2>/dev/null | tail -n +2 | awk '{print $1}' | grep -v '^$'
}

list_cached_models() {
  if [ -d "$HOME/.ollama/models/manifests" ]; then
    find "$HOME/.ollama/models/manifests" -name "*.json" -o -type d -mindepth 3 | \
      sed 's|.*/manifests/registry.ollama.ai/library/||' | \
      sed 's|/.*||' | sort -u | grep -v '^$'
  fi
}

preload_models() {
  local models="$1"
  echo "Pre-loading models for bundling: $models"
  IFS=',' read -ra MODEL_LIST <<< "$models"
  for model in "${MODEL_LIST[@]}"; do
    model=$(echo "$model" | xargs) # trim whitespace
    echo "Downloading model: $model (this may take time...)"
    if ! ollama pull "$model"; then
      echo "Warning: Failed to download $model. Skipping..." >&2
    fi
  done
}

interactive_model_selection() {
  echo "Available models:"
  local available_models=($(list_available_models))
  local cached_models=($(list_cached_models))
  
  if [ ${#available_models[@]} -eq 0 ]; then
    echo "No models found. Consider running 'ollama pull <model>' first."
    return 1
  fi
  
  echo ""
  echo "Select models to include in bundle (enter numbers separated by spaces):"
  local i=1
  local selection_map=()
  
  for model in "${available_models[@]}"; do
    local cached_status=""
    if [[ " ${cached_models[@]} " =~ " ${model%:*} " ]]; then
      cached_status=" [CACHED]"
    else
      cached_status=" [NEEDS DOWNLOAD]"
    fi
    echo "  $i) $model$cached_status"
    selection_map[$i]="$model"
    ((i++))
  done
  
  echo ""
  echo "Enter selection (e.g., '1 3 5' for models 1, 3, and 5):"
  echo "Or 'all' to select all models, 'cached' for cached only:"
  read -r selection
  
  local selected_models=()
  if [ "$selection" = "all" ]; then
    selected_models=("${available_models[@]}")
  elif [ "$selection" = "cached" ]; then
    for model in "${available_models[@]}"; do
      if [[ " ${cached_models[@]} " =~ " ${model%:*} " ]]; then
        selected_models+=("$model")
      fi
    done
  else
    for num in $selection; do
      if [[ "$num" =~ ^[0-9]+$ ]] && [ "$num" -ge 1 ] && [ "$num" -lt "$i" ]; then
        selected_models+=("${selection_map[$num]}")
      fi
    done
  fi
  
  if [ ${#selected_models[@]} -eq 0 ]; then
    echo "No models selected."
    return 1
  fi
  
  echo "Selected models: ${selected_models[*]}"
  
  # Download any models that aren't cached
  for model in "${selected_models[@]}"; do
    if [[ ! " ${cached_models[@]} " =~ " ${model%:*} " ]]; then
      echo "Downloading $model (this may take time...)"
      if ! ollama pull "$model"; then
        echo "Warning: Failed to download $model. It will be skipped in the bundle." >&2
      fi
    fi
  done
  
  return 0
}

# Handle model pre-loading and selection
if [ -n "$PRELOAD_MODELS" ]; then
  preload_models "$PRELOAD_MODELS"
elif [ "$INTERACTIVE_MODELS" = true ]; then
  interactive_model_selection
fi

echo "Creating portable bundle at: $TARGET"
mkdir -p "$TARGET/poc/core/prompts"
mkdir -p "$TARGET/poc/core/modules"
mkdir -p "$TARGET/tests/prompts"
mkdir -p "$TARGET/tools"
mkdir -p "$TARGET/models"

# Copy core server/client and prompts
cp -v "$ROOT_DIR/poc/core/roadnerd_server.py" "$TARGET/poc/core/" 
cp -v "$ROOT_DIR/poc/core/roadnerd_client.py" "$TARGET/poc/core/" 
cp -rv "$ROOT_DIR/poc/core/prompts/." "$TARGET/poc/core/prompts/"

# Copy modular components (current architecture)
if [ -d "$ROOT_DIR/poc/core/modules" ]; then
  echo "Copying modular components..."
  cp -rv "$ROOT_DIR/poc/core/modules/." "$TARGET/poc/core/modules/"
fi

# Copy future architecture components if they exist
if [ -d "$ROOT_DIR/src" ]; then
  echo "Copying future architecture components..."
  mkdir -p "$TARGET/src"
  cp -rv "$ROOT_DIR/src/." "$TARGET/src/"
fi 

# Copy tools/scripts for testing
cp -v "$ROOT_DIR/tools/run_prompt_suite.py" "$TARGET/tools/" || true
cp -v "$ROOT_DIR/tools/run_disambiguation_flow.py" "$TARGET/tools/" || true
cp -v "$ROOT_DIR/tools/aggregate_llm_runs.py" "$TARGET/tools/" || true
cp -v "$ROOT_DIR/tests/prompts/cases.yaml" "$TARGET/tests/prompts/" || true

# Bundle Python dependencies for offline installation
if [ "$INCLUDE_DEPS" = true ]; then
  echo "Bundling Python dependencies for offline installation..."
  mkdir -p "$TARGET/python-deps"
  
  # Create requirements.txt
  cat > "$TARGET/requirements.txt" << 'EOF'
flask>=2.0.0
flask-cors>=3.0.0
requests>=2.25.0
pyyaml>=5.4.0
numpy>=1.21.0
scikit-learn>=1.0.0
EOF
  
  # Download all dependencies and their transitive deps to local directory
  echo "Downloading dependencies (this may take a moment)..."
  if command -v pip3 >/dev/null 2>&1; then
    pip3 download -r "$TARGET/requirements.txt" -d "$TARGET/python-deps/"
  elif command -v pip >/dev/null 2>&1; then
    pip download -r "$TARGET/requirements.txt" -d "$TARGET/python-deps/"
  else
    echo "Warning: pip not found. Dependencies will not be bundled."
  fi
  
  # Create offline installer
  cat > "$TARGET/install_dependencies.sh" << 'EOF'
#!/usr/bin/env bash
set -euo pipefail

DIR="$(cd "$(dirname "$0")" && pwd)"

echo "Installing Python dependencies from bundled packages..."
if [ ! -d "$DIR/python-deps" ]; then
  echo "Error: python-deps directory not found. Run with --include-deps flag during bundle creation."
  exit 1
fi

if command -v pip3 >/dev/null 2>&1; then
    pip3 install --user --no-index --find-links "$DIR/python-deps" -r "$DIR/requirements.txt"
elif command -v pip >/dev/null 2>&1; then
    pip install --user --no-index --find-links "$DIR/python-deps" -r "$DIR/requirements.txt"
else
    echo "Error: Neither pip nor pip3 found. Please install pip first."
    exit 1
fi
echo "Dependencies installed successfully from bundled packages."
EOF
else
  echo "Creating requirements.txt (dependencies not bundled - use --include-deps for offline installation)..."
  cat > "$TARGET/requirements.txt" << 'EOF'
flask>=2.0.0
flask-cors>=3.0.0
requests>=2.25.0
pyyaml>=5.4.0
numpy>=1.21.0
scikit-learn>=1.0.0
EOF
  
  # Create online installer (requires internet)
  cat > "$TARGET/install_dependencies.sh" << 'EOF'
#!/usr/bin/env bash
set -euo pipefail

echo "Installing Python dependencies from PyPI (requires internet)..."
if command -v pip3 >/dev/null 2>&1; then
    pip3 install --user -r requirements.txt
elif command -v pip >/dev/null 2>&1; then
    pip install --user -r requirements.txt
else
    echo "Error: Neither pip nor pip3 found. Please install pip first."
    exit 1
fi
echo "Dependencies installed successfully."
EOF
fi
chmod +x "$TARGET/install_dependencies.sh"

# Optionally include models cache tarball
if [ "$INCLUDE_MODELS" = true ]; then
  CACHE1="$HOME/.roadnerd/models/ollama-models.tar.gz"
  CACHE2="$HOME/.ollama/models"
  if [ -f "$CACHE1" ]; then
    echo "Including cached models from $CACHE1"
    cp -v "$CACHE1" "$TARGET/models/ollama-models.tar.gz"
  elif [ -d "$CACHE2" ]; then
    echo "Creating models tarball from $CACHE2 (this may take time)"
    tar czf "$TARGET/models/ollama-models.tar.gz" -C "$HOME" .ollama/models
  else
    echo "No model cache found; skipping. You can run profile-machine.py --cache-models beforehand."
  fi
fi

# Start script
cat > "$TARGET/start_roadnerd.sh" << 'EOF'
#!/usr/bin/env bash
set -euo pipefail

DIR="$(cd "$(dirname "$0")" && pwd)"
export RN_SAFE_MODE=${RN_SAFE_MODE:-true}
export RN_PROMPT_DIR="$DIR/poc/core/prompts"
export RN_LOG_DIR="$DIR/logs"
mkdir -p "$RN_LOG_DIR"

echo "Starting RoadNerd at http://localhost:${RN_PORT:-8080}"
python3 "$DIR/poc/core/roadnerd_server.py"
EOF
chmod +x "$TARGET/start_roadnerd.sh"

# Optional installer for models
cat > "$TARGET/install_models.sh" << 'EOF'
#!/usr/bin/env bash
set -euo pipefail

DIR="$(cd "$(dirname "$0")" && pwd)"
ARCHIVE="$DIR/models/ollama-models.tar.gz"

if [ ! -f "$ARCHIVE" ]; then
  echo "No models archive found at $ARCHIVE" >&2
  exit 1
fi

if ! command -v ollama >/dev/null 2>&1; then
  echo "Installing Ollama..."
  curl -fsSL https://ollama.com/install.sh | sh
fi

echo "Extracting models to ~/.ollama ..."
mkdir -p "$HOME/.ollama"
tar xzf "$ARCHIVE" -C "$HOME"
echo "Done. You can now run: ollama serve &"
EOF
chmod +x "$TARGET/install_models.sh"

echo "Done. To run on another machine:"
echo "  1) Copy '$TARGET' to USB/network drive"
echo "  2) On the target machine:"
echo "     a) cd into the folder" 
echo "     b) ./install_dependencies.sh (install Python dependencies)"
echo "     c) ./start_roadnerd.sh (start the server)"
echo "  3) Open http://localhost:8080/api-docs to test, choose model via the Model section"
if [ "$INCLUDE_MODELS" = true ]; then
  echo "  (Optional) Install bundled models: ./install_models.sh (then 'ollama serve &')"
fi
echo ""
echo "Bundle contents:"
echo "  - Core RoadNerd server/client (poc/core/)"
echo "  - Modular components (poc/core/modules/)"
if [ -d "$ROOT_DIR/src" ]; then
  echo "  - Future architecture components (src/)"
fi
echo "  - Testing tools (tools/)"
if [ "$INCLUDE_DEPS" = true ]; then
  echo "  - Bundled Python dependencies (python-deps/ + offline installer)"
else
  echo "  - Python dependencies (requirements.txt + online installer - requires internet)"
fi
if [ "$INCLUDE_MODELS" = true ]; then
  echo "  - Bundled LLM models (models/)"
  if [ -f "$TARGET/models/ollama-models.tar.gz" ]; then
    echo "    Available models after extraction:"
    local bundled_models=$(list_cached_models 2>/dev/null || echo "Run list after installation")
    if [ -n "$bundled_models" ]; then
      for model in $bundled_models; do
        echo "      - $model"
      done
    else
      echo "      - See ./install_models.sh output for complete list"
    fi
  fi
fi
