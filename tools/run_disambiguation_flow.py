#!/usr/bin/env python3
"""
Run an uncertainty-aware disambiguation flow against a live server using existing endpoints.

This script simulates a low-confidence multi-category case by:
 - Faceted brainstorm per category (N small, creativity moderate) using category-focused issue text
 - Judge to pick discriminative checks
 - Probe selected checks (read-only)
 - Judge again to select the best idea

Usage:
  python3 tools/run_disambiguation_flow.py \
    --base-url http://localhost:8080 \
    --issue "Internet not working" \
    --categories wifi,dns,network \
    --n 2 --creativity 2
"""
import argparse
import json
import re
from collections import OrderedDict
from datetime import datetime
from pathlib import Path

import requests


def brainstorm_for_category(base_url: str, issue: str, category: str, others: list, n: int, creativity: int):
    hint = (
        f"{issue}\n\nFocus: {category}. "
        f"Please include discriminative checks to distinguish this from: {', '.join(others)}."
    )
    r = requests.post(f"{base_url}/api/ideas/brainstorm", json={
        'issue': hint,
        'n': n,
        'creativity': creativity,
    })
    r.raise_for_status()
    return r.json().get('ideas', [])


def select_discriminative_checks(ideas: list, max_checks: int = 3) -> list:
    # Simple heuristic: prefer unique, short, whitelisted-looking checks; dedupe preserve order
    seen = OrderedDict()
    for idea in ideas:
        for chk in idea.get('checks', [])[:3]:
            c = chk.strip()
            if len(c) > 0 and len(c) <= 80 and c not in seen:
                seen[c] = True
            if len(seen) >= max_checks:
                break
        if len(seen) >= max_checks:
            break
    return list(seen.keys())


def probe_checks(base_url: str, checks: list) -> dict:
    ideas = [{'hypothesis': 'probe', 'category': 'probe', 'why': 'disambiguation', 'checks': checks}]
    r = requests.post(f"{base_url}/api/ideas/probe", json={'ideas': ideas, 'run_checks': True})
    r.raise_for_status()
    return r.json()


def judge_ideas(base_url: str, issue: str, ideas: list) -> list:
    r = requests.post(f"{base_url}/api/ideas/judge", json={'issue': issue, 'ideas': ideas})
    r.raise_for_status()
    return r.json().get('ranked', [])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--base-url', default='http://localhost:8080')
    ap.add_argument('--issue', required=True)
    ap.add_argument('--categories', required=True, help='comma-separated, e.g., wifi,dns,network')
    ap.add_argument('--n', type=int, default=2)
    ap.add_argument('--creativity', type=int, default=2)
    args = ap.parse_args()

    cats = [c.strip() for c in args.categories.split(',') if c.strip()]
    if len(cats) < 2:
        raise SystemExit('Need at least two categories for disambiguation.')

    print(f"== Disambiguation run ==\nissue: {args.issue}\ncategories: {cats}\n")

    # Pass 1: faceted brainstorm
    pooled_ideas = []
    for c in cats:
        others = [x for x in cats if x != c]
        ideas = brainstorm_for_category(args.base_url, args.issue, c, others, n=args.n, creativity=args.creativity)
        print(f"[brainstorm/{c}] got {len(ideas)} idea(s)")
        pooled_ideas.extend(ideas)

    # Judge all ideas once (ranking baseline)
    ranked = judge_ideas(args.base_url, args.issue, pooled_ideas)
    print(f"\n[judge] baseline top idea: {ranked[0]['idea']['hypothesis'] if ranked else 'n/a'}")

    # Select discriminative checks and probe
    checks = select_discriminative_checks(pooled_ideas, max_checks=3)
    print(f"[probe] selected checks: {checks}")
    probe_res = probe_checks(args.base_url, checks)
    # Merge evidence back into ideas (if any idea had the same checks, attach evidence)
    evidence = (probe_res.get('probed_ideas') or [{}])[0].get('evidence', {})
    for idea in pooled_ideas:
        if 'checks' in idea:
            idea.setdefault('evidence', {})
            for chk in idea['checks']:
                if chk in evidence:
                    idea['evidence'][chk] = evidence[chk]

    # Judge again
    ranked2 = judge_ideas(args.base_url, args.issue, pooled_ideas)
    print(f"[judge] after probe top idea: {ranked2[0]['idea']['hypothesis'] if ranked2 else 'n/a'}\n")

    # Pretty print short summary
    def short(r):
        i = r['idea']
        return {
            'hypothesis': i.get('hypothesis'),
            'category': i.get('category'),
            'risk': i.get('risk'),
            'score': round(r.get('total_score', 0), 3)
        }

    print("Top 3 ideas (after probe):")
    for r in ranked2[:3]:
        print(json.dumps(short(r), ensure_ascii=False))


if __name__ == '__main__':
    main()

