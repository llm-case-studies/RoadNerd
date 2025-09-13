#!/usr/bin/env python3
"""
Run a YAML prompt suite against a live RoadNerd server and log results to JSONL.

Usage:
  python3 tools/run_prompt_suite.py --base-url http://localhost:8080 \
    --cases tests/prompts/cases.yaml --tag quick | tee /tmp/prompt_suite.log
"""
import argparse
import json
import os
import re
from pathlib import Path
from datetime import datetime
import requests
import yaml


def load_cases(path: Path):
    with path.open() as f:
        return yaml.safe_load(f)


def ensure_log_path() -> Path:
    # Prefer RN_LOG_DIR if set
    env = os.environ.get('RN_LOG_DIR')
    if env:
        out_dir = Path(env) / 'llm_runs'
    else:
        repo_root = Path(__file__).resolve().parents[1]
        out_dir = repo_root / 'logs' / 'llm_runs'
    out_dir.mkdir(parents=True, exist_ok=True)
    return out_dir / (datetime.now().strftime('%Y%m%d') + '.jsonl')


def append_jsonl(path: Path, record: dict):
    with path.open('a') as f:
        f.write(json.dumps(record, ensure_ascii=False) + '\n')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--base-url', default='http://localhost:8080')
    ap.add_argument('--cases', default=str(Path(__file__).resolve().parents[1] / 'tests' / 'prompts' / 'cases.yaml'))
    ap.add_argument('--tag', default='suite')
    args = ap.parse_args()

    status = requests.get(f"{args.base_url}/api/status").json()
    print("Server status:")
    print(json.dumps(status, indent=2))

    cases = load_cases(Path(args.cases))
    log_path = ensure_log_path()

    results = []
    for case in cases:
        issue = case['issue']
        cid = case.get('id')
        print(f"\n== Case {cid} ==")
        r = requests.post(f"{args.base_url}/api/diagnose", json={'issue': issue})
        data = r.json()
        suggestion = data.get('llm_suggestion') or ''

        # Evaluate naive expectations
        exp = case.get('expect_any') or []
        ok = False
        matched = None
        for pat in exp:
            if re.search(pat, suggestion, flags=re.IGNORECASE):
                ok = True
                matched = pat
                break

        rec = {
            'mode': 'prompt_suite',
            'timestamp': datetime.now().isoformat(),
            'case': case,
            'server': {
                'backend': status.get('llm_backend'),
                'model': status.get('model'),
            },
            'status': status,
            'response': data,
            'eval': {
                'pass': ok,
                'matched': matched,
                'tokens_est': len(suggestion.split()),
            },
            'tag': args.tag,
        }
        append_jsonl(log_path, rec)
        results.append(rec)
        print(json.dumps({'pass': ok, 'matched': matched, 'tokens_est': rec['eval']['tokens_est']}, indent=2))

    # Summary
    total = len(results)
    passed = sum(1 for r in results if r['eval']['pass'])
    print(f"\nSummary: {passed}/{total} passed ({(passed/total*100):.1f}%)")


if __name__ == '__main__':
    main()
