#!/usr/bin/env bash
set -euo pipefail

# RoadNerd test runner and server launcher
# Usage:
#   ./run-tests-and-server.sh                    # Run all tests + start server
#   ./run-tests-and-server.sh -unit-tests        # Run only unit tests
#   ./run-tests-and-server.sh -e2e-tests         # Run only e2e tests  
#   ./run-tests-and-server.sh -all-tests         # Run all tests (explicit)
#   ./run-tests-and-server.sh -server-only       # Skip tests, just start server
#
# Port Policy: ALWAYS uses port 8080. Any conflicting processes are killed.
# Override only for comparative testing with explicit RN_PORT_REASON.

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$HERE"

# Setup logging
LOGS_DIR="$HERE/logs"
mkdir -p "$LOGS_DIR"
RESTART_LOG="$LOGS_DIR/restart.log"

# Simple logger available before any usage
log() { 
  local msg="$*"
  printf "[run] %s\n" "$msg"
  printf "[%s] [run] %s\n" "$(date '+%Y-%m-%d %H:%M:%S')" "$msg" >> "$RESTART_LOG"
}

# Parse command line arguments
RUN_UNIT_TESTS=true
RUN_E2E_TESTS=true
RUN_SERVER=true

case "${1:-}" in
  -unit-tests)
    RUN_E2E_TESTS=false
    RUN_SERVER=false
    ;;
  -e2e-tests)
    RUN_UNIT_TESTS=false
    RUN_SERVER=false
    ;;
  -all-tests)
    RUN_UNIT_TESTS=true
    RUN_E2E_TESTS=true
    RUN_SERVER=false
    ;;
  -server-only)
    RUN_UNIT_TESTS=false
    RUN_E2E_TESTS=false
    ;;
  "")
    # Default: run all tests + server
    ;;
  *)
    echo "Usage: $0 [-unit-tests|-e2e-tests|-all-tests|-server-only]"
    exit 1
    ;;
esac

# Log session start with configuration
{
  echo "=== SESSION START ==="
  echo "Timestamp: $(date '+%Y-%m-%d %H:%M:%S')"
  echo "Args: ${1:-[default]}"
  echo "Config: RUN_UNIT_TESTS=$RUN_UNIT_TESTS RUN_E2E_TESTS=$RUN_E2E_TESTS RUN_SERVER=$RUN_SERVER"
  echo "Environment:"
  echo "  RN_MODEL=${RN_MODEL:-[default]}"
  echo "  RN_PORT=${RN_PORT:-8080}"
  echo "  RN_PORT_REASON=${RN_PORT_REASON:-[none]}" 
  echo "  RN_SAFE_MODE=${RN_SAFE_MODE:-true}"
  echo "  RN_USE_CHAT_MODE=${RN_USE_CHAT_MODE:-auto}"
  echo "  RN_VENV=${RN_VENV:-$HOME/.roadnerd_venv}"
} >> "$RESTART_LOG"

# Detect base path (this script may live at repo root or inside RoadNerd/)
BASE="."
SERVER_REL="poc/core/roadnerd_server.py"
if [[ ! -f "$BASE/$SERVER_REL" ]]; then
  if [[ -f "RoadNerd/$SERVER_REL" ]]; then
    BASE="RoadNerd"
  else
    echo "[run] Cannot find $SERVER_REL (looked in . and RoadNerd)." >&2
    exit 1
  fi
fi

# Activate runtime venv per project policy (before picking python)
VENV="${RN_VENV:-$HOME/.roadnerd_venv}"
if [[ -d "$VENV/bin" ]]; then
  log "Activating venv: $VENV"
  # shellcheck disable=SC1090
  source "$VENV/bin/activate"
else
  log "No venv found at $VENV; skipping activation. (Set RN_VENV to override.)"
fi

# Choose Python interpreter (after venv activation)
if [[ -n "${PYTHON:-}" ]]; then
  PY="$PYTHON"
elif command -v python3 >/dev/null 2>&1; then
  PY="python3"
elif command -v python >/dev/null 2>&1; then
  PY="python"
else
  echo "[run] No python interpreter found. Install python3 or set PYTHON env var." >&2
  exit 1
fi

# Config - PORT POLICY ENFORCEMENT
BIND="${RN_BIND:-127.0.0.1}"
PORT="${RN_PORT:-8080}"
SAFE="${RN_SAFE_MODE:-true}"
CHAT="${RN_USE_CHAT_MODE:-auto}"

# Port 8080 policy enforcement
if [[ "$PORT" != "8080" ]]; then
  if [[ -z "${RN_PORT_REASON:-}" ]]; then
    log "ERROR: Port override to $PORT without justification"
    log "Port 8080 is REQUIRED unless RN_PORT_REASON is set"
    log "Valid reasons: 'comparative-testing', 'load-testing', 'production-conflict'"
    exit 1
  else
    log "WARNING: Using non-standard port $PORT"
    log "Reason: $RN_PORT_REASON"
  fi
fi

# --- Stop existing server(s) ---
log "Stopping any existing roadnerd_server.py processes..."
pids=$(pgrep -f 'roadnerd_server.py' || true)
if [[ -n "${pids}" ]]; then
  log "Killing PIDs: ${pids}"
  kill ${pids} || true
  sleep 1
fi
if command -v lsof >/dev/null 2>&1; then
  lsof -ti ":${PORT}" 2>/dev/null | xargs -r kill || true
fi

# Track test results for logging
TEST_RESULTS=()

# Enhanced test runner with result tracking
run_pytest_dir() {
  local dir="$1" 
  local test_type="$2"
  if [[ -d "$dir" ]]; then
    log "Running $test_type tests in $dir"
    if "$PY" -m pytest --version >/dev/null 2>&1; then
      if ( cd "$dir" && "$PY" -m pytest -q ); then
        TEST_RESULTS+=("$test_type:$dir:PASS")
        log "$test_type tests in $dir: PASSED"
      else
        TEST_RESULTS+=("$test_type:$dir:FAIL")
        log "$test_type tests in $dir: FAILED"
      fi
    else
      TEST_RESULTS+=("$test_type:$dir:SKIP")
      log "pytest not found for $PY; skipping $dir (install: pip install pytest)"
    fi
  else
    TEST_RESULTS+=("$test_type:$dir:MISSING")
    log "Test directory $dir not found, skipping $test_type tests"
  fi
}

if [[ "$RUN_UNIT_TESTS" == "true" ]]; then
  run_pytest_dir "$BASE/poc/core" "unit"
  run_pytest_dir "$BASE/tests/unit" "unit"
fi

if [[ "$RUN_E2E_TESTS" == "true" ]]; then
  run_pytest_dir "$BASE/tests/integration" "integration"  
  run_pytest_dir "$BASE/tests/e2e" "e2e"
fi

# --- Preflight dependency check (fail fast per policy) ---
log "Checking runtime dependencies..."
if ! "$PY" - <<'PY' >/dev/null 2>&1
import importlib
for m in ("flask","flask_cors","requests","psutil"):
    importlib.import_module(m)
PY
then
  echo "[run] Missing dependencies for RoadNerd server (flask, flask-cors, requests, psutil)." >&2
  echo "[run] Please activate your venv and install them, e.g.:" >&2
  echo "[run]   source \"$VENV/bin/activate\"" >&2
  echo "[run]   pip install flask flask-cors requests psutil" >&2
  exit 2
fi

if [[ "$RUN_SERVER" == "true" ]]; then
  # --- Start server ---
  log "Starting server on ${BIND}:${PORT} (safe_mode=${SAFE}, chat_mode=${CHAT})"
  mkdir -p /tmp
  nohup env RN_SAFE_MODE="${SAFE}" RN_BIND="${BIND}" RN_PORT="${PORT}" RN_USE_CHAT_MODE="${CHAT}" \
    "$PY" "$BASE/$SERVER_REL" > /tmp/roadnerd-server.log 2>&1 &
  PID=$!
  log "Server PID: ${PID}"
  sleep 1

  if [[ -f /tmp/roadnerd-server.log ]]; then
    log "--- last 20 lines of /tmp/roadnerd-server.log ---"
    tail -n 20 /tmp/roadnerd-server.log || true
  fi

  log "Ready: open http://${BIND}:${PORT}/api-docs"
  
  # Log final session summary
  {
    echo "=== SESSION SUMMARY ==="
    echo "Timestamp: $(date '+%Y-%m-%d %H:%M:%S')"
    if [[ ${#TEST_RESULTS[@]} -gt 0 ]]; then
      echo "Test Results:"
      for result in "${TEST_RESULTS[@]}"; do
        echo "  $result"
      done
    fi
    echo "Server: Started on ${BIND}:${PORT} (PID: ${PID})"
    echo "Model: ${RN_MODEL:-[default]}"
    echo "Chat Mode: ${CHAT}"
    echo "Safe Mode: ${SAFE}"
    echo ""
  } >> "$RESTART_LOG"
else
  log "Server startup skipped (test-only mode)"
  
  # Log test-only session summary
  {
    echo "=== TEST-ONLY SESSION SUMMARY ==="
    echo "Timestamp: $(date '+%Y-%m-%d %H:%M:%S')"
    if [[ ${#TEST_RESULTS[@]} -gt 0 ]]; then
      echo "Test Results:"
      for result in "${TEST_RESULTS[@]}"; do
        echo "  $result"
      done
    fi
    echo ""
  } >> "$RESTART_LOG"
fi

log "Session logged to: $RESTART_LOG"
