# RoadNerd Test Suite

## Structure
- unit: fast, no network; tests server utilities and client helpers
- integration: Flask `test_client` API tests and scripted client flows (includes ideas endpoints)
- prompts: YAML cases for live server prompt checks (tools/run_prompt_suite.py)
- flows: disambiguation runner exercising brainstorm→probe→judge (tools/run_disambiguation_flow.py)

## Running
- Recommended: Python 3.10+ with a venv

```
python3 -m venv ~/.venvs/rn && source ~/.venvs/rn/bin/activate
pip install -U pip pytest requests flask flask-cors
pytest -q RoadNerd/tests
```

- With markers:
```
pytest -q -m unit RoadNerd/tests
pytest -q -m integration RoadNerd/tests
```

## Live Prompt Suite (Phase 0)
```
python3 RoadNerd/poc/core/roadnerd_server.py &
python3 RoadNerd/tools/run_prompt_suite.py --base-url http://localhost:8080 \
  --cases RoadNerd/tests/prompts/cases.yaml --tag quick | tee /tmp/prompt_suite.log
python3 RoadNerd/tools/aggregate_llm_runs.py
```

## Ideas Endpoints (Integration)
- Brainstorm parsing and probe whitelist are covered in:
  - `tests/integration/test_ideas_endpoints.py`
- Manual in browser: `http://localhost:8080/api-docs` (brainstorm, probe, judge sections)

## Disambiguation Flow (Ambiguous Inputs)
```
python3 RoadNerd/tools/run_disambiguation_flow.py \
  --base-url http://localhost:8080 \
  --issue "Internet not working" \
  --categories wifi,dns,network --n 2 --creativity 2
```

## Classifier & Retrieval (Phase A scaffolding)
- Classifier quick check:
  - `python3 RoadNerd/tools/test_classifier.py "My WiFi is not working; nmcli shows disconnected"`
- Retrieval quick check:
  - `python3 RoadNerd/tools/test_retrieval.py --query "dns failing resolv.conf" --category dns`

Notes
- Flask tests stub the LLM to avoid external dependencies.
- Client interactive tests script `input()` and stub HTTP with a dummy session.
- For local endpoint tests, ensure Flask and Flask-CORS are installed.
- Prompt templates live in `poc/core/prompts/` and hot‑reload; override directory with `RN_PROMPT_DIR`.
