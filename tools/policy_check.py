#!/usr/bin/env python3
"""
RoadNerd Policy Check (Quick QA)

Scans the repo for common policy violations:
 - Hard-coded venv paths instead of RN_VENV
 - Auto-installing packages in code (pip install in Python modules)
 - Logging path not honoring RN_LOG_DIR (informational)

Usage:
  python3 RoadNerd/tools/policy_check.py [--strict]
"""
from __future__ import annotations

import argparse
import re
from pathlib import Path
from typing import Dict, List


ROOT = Path(__file__).resolve().parents[1]


def read_text_safe(p: Path) -> str:
    try:
        return p.read_text(encoding='utf-8', errors='ignore')
    except Exception:
        return ''


def check_hardcoded_venv(files: List[Path]) -> List[Dict]:
    issues = []
    pat = re.compile(r"\.roadnerd_venv")
    for p in files:
        if p.suffix not in {'.sh', '.py'}:
            continue
        text = read_text_safe(p)
        if pat.search(text):
            # Encourage RN_VENV usage in launchers/scripts; warn for now
            issues.append({'file': str(p), 'policy': 'venv_path_hardcoded', 'severity': 'warn'})
    return issues


def check_auto_pip(files: List[Path]) -> List[Dict]:
    issues = []
    pip_pat = re.compile(r"pip\s+install|subprocess\.run\([^)]*pip[^)]*install", re.IGNORECASE | re.DOTALL)
    for p in files:
        if p.suffix != '.py':
            continue
        text = read_text_safe(p)
        if pip_pat.search(text):
            issues.append({'file': str(p), 'policy': 'auto_pip_install', 'severity': 'fail'})
    return issues


def check_logging_paths(files: List[Path]) -> List[Dict]:
    issues = []
    log_pat = re.compile(r"logs/llm_runs")
    for p in files:
        if p.suffix != '.py':
            continue
        text = read_text_safe(p)
        if log_pat.search(text) and 'RN_LOG_DIR' not in text:
            issues.append({'file': str(p), 'policy': 'log_dir_repo_relative', 'severity': 'warn'})
    return issues


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--strict', action='store_true', help='Exit non-zero on any violation')
    args = ap.parse_args()

    files = [p for p in ROOT.rglob('*') if p.is_file() and '.venv' not in str(p) and 'node_modules' not in str(p)]

    findings: List[Dict] = []
    findings += check_hardcoded_venv(files)
    findings += check_auto_pip(files)
    findings += check_logging_paths(files)

    if not findings:
        print('Policy check: OK (no issues)')
        return 0

    # Print grouped summary
    print('Policy check findings:')
    by_policy: Dict[str, List[Dict]] = {}
    for f in findings:
        by_policy.setdefault(f['policy'], []).append(f)

    for policy, items in by_policy.items():
        sev = items[0]['severity']
        print(f"- {policy} [{sev}]: {len(items)} occurrence(s)")
        for it in items:
            print(f"  • {it['file']}")

    if args.strict and any(f.get('severity') == 'fail' for f in findings):
        return 2
    return 0


if __name__ == '__main__':
    raise SystemExit(main())

