#!/usr/bin/env bash
set -euo pipefail

# RoadNerd end-to-end runner: prompt suite -> aggregate -> disambiguation -> log scan

BASE_URL="${BASE_URL:-http://localhost:8080}"
CLS_URL="${CLS_URL:-http://127.0.0.1:7080}"
RN_LOG_DIR="${RN_LOG_DIR:-$HOME/.roadnerd/logs}"

STAMP_DATE="$(date +%Y%m%d)"
STAMP_TIME="$(date +%H%M%S)"
RUN_ID="run-${STAMP_DATE}-${STAMP_TIME}"
E2E_ROOT="$RN_LOG_DIR/e2e/$STAMP_DATE/$RUN_ID"
mkdir -p "$E2E_ROOT"

echo "== RoadNerd run-all =="
echo "BASE_URL=$BASE_URL"
echo "CLS_URL=$CLS_URL"
echo "RN_LOG_DIR=$RN_LOG_DIR"
echo "RUN_ID=$RUN_ID"

echo "\n[1/4] Prompt suite"
python3 RoadNerd/tools/run_prompt_suite.py --base-url "$BASE_URL" \
  --cases RoadNerd/tests/prompts/cases.yaml --tag "$RUN_ID" \
  | tee "$E2E_ROOT/prompt_suite.log"

echo "\n[2/4] Aggregate JSONL logs"
python3 RoadNerd/tools/aggregate_llm_runs.py | tee "$E2E_ROOT/aggregate.log" || true

echo "\n[3/4] Disambiguation flow"
python3 RoadNerd/tools/run_disambiguation_flow.py --base-url "$BASE_URL" \
  --issue "Internet not working" --categories wifi,dns,network --n 2 --creativity 2 \
  | tee "$E2E_ROOT/disambiguation.log" || true

echo "\n[4/4] Scan logs for errors via Code-Log-Search-MCP"
Q='error|failed|timeout|Exception|parsing|traceback'
curl -s -X POST "$CLS_URL/actions/search_logs" \
  -H 'Content-Type: application/json' \
  -d "{\"query\":\"$Q\",\"date\":\"$STAMP_DATE\",\"maxResults\":200}" \
  > "$E2E_ROOT/log_scan.json" || true

COUNT=$(python3 - <<'PY'
import json,sys
try:
  data=json.load(open(sys.argv[1]))
  print(len(data.get('entries',[])))
except Exception:
  print(0)
PY
"$E2E_ROOT/log_scan.json")

REPORT="$E2E_ROOT/report.md"
{
  echo "# RoadNerd Run Report — $RUN_ID"
  echo
  echo "- Base URL: $BASE_URL"
  echo "- Logs root: $RN_LOG_DIR"
  echo "- E2E dir: $E2E_ROOT"
  echo
  echo "## Steps"
  echo "1. Prompt Suite → prompt_suite.log"
  echo "2. Aggregate Logs → aggregate.log"
  echo "3. Disambiguation Flow → disambiguation.log"
  echo "4. Log Scan (Code-Log-Search-MCP) → log_scan.json (matches: $COUNT)"
  echo
  echo "## Notes"
  echo "- Use http://localhost:8080/logs to browse JSONL logs"
  echo "- Use $CLS_URL/search to run ad-hoc searches"
} > "$REPORT"

echo "\nDone. Report: $REPORT"
