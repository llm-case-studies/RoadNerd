#!/usr/bin/env python3
"""
Aggregate JSONL logs from logs/llm_runs and print a simple leaderboard.

Usage:
  python3 tools/aggregate_llm_runs.py [--date YYYYMMDD]
"""
import argparse
import json
import os
from pathlib import Path
from collections import defaultdict, Counter


def iter_jsonl(path: Path):
    with path.open() as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except Exception:
                continue


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--date', help='YYYYMMDD file; default: latest file')
    args = ap.parse_args()

    # Prefer RN_LOG_DIR if set; otherwise use repo logs/llm_runs
    env = os.environ.get('RN_LOG_DIR')
    if env:
        logs_dir = Path(env) / 'llm_runs'
    else:
        logs_dir = Path(__file__).resolve().parents[1] / 'logs' / 'llm_runs'
    files = sorted(logs_dir.glob('*.jsonl'))
    if not files:
        print('No logs found in', logs_dir)
        return
    target = None
    if args.date:
        cand = logs_dir / f"{args.date}.jsonl"
        target = cand if cand.exists() else None
    if target is None:
        target = files[-1]

    print('Aggregating:', target)
    records = list(iter_jsonl(target))
    if not records:
        print('No records')
        return

    by_mode = defaultdict(list)
    for r in records:
        by_mode[r.get('mode', 'unknown')].append(r)

    # Simple stats for prompt_suite and legacy modes
    def pct(a, b):
        return 0.0 if b == 0 else 100.0 * a / b

    for mode, items in by_mode.items():
        print(f"\n== Mode: {mode} ==")
        total = len(items)
        passes = sum(1 for x in items if x.get('eval', {}).get('pass'))
        kb_hits = sum(1 for x in items if x.get('response', {}).get('kb_solution'))
        toks = [x.get('eval', {}).get('tokens_est') or x.get('result', {}).get('llm_tokens_est') or 0 for x in items]
        avg_toks = (sum(toks)/len(toks)) if toks else 0.0
        print(f"total: {total}, pass: {passes} ({pct(passes,total):.1f}%), kb_hits: {kb_hits}, avg_tokens: {avg_toks:.1f}")

    # Category breakdown for prompt_suite
    cats = Counter()
    cat_pass = Counter()
    for r in by_mode.get('prompt_suite', []):
        cat = (r.get('case') or {}).get('category', 'unknown')
        cats[cat] += 1
        if r.get('eval', {}).get('pass'):
            cat_pass[cat] += 1
    if cats:
        print('\nBy category:')
        for cat, n in cats.items():
            p = cat_pass[cat]
            print(f"  {cat}: {p}/{n} ({pct(p,n):.1f}%)")


if __name__ == '__main__':
    main()
