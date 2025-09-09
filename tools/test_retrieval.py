#!/usr/bin/env python3
import argparse
from pathlib import Path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--query', required=True)
    ap.add_argument('--category')
    args = ap.parse_args()

    try:
        from poc.core.retrieval import HybridRetriever
    except Exception:
        from RoadNerd.poc.core.retrieval import HybridRetriever

    r = HybridRetriever()
    res = r.search(args.query, category_hint=args.category, k=5)
    for s in res:
        print(f"[{s.score:.1f}] {Path(s.source).name}: {s.text[:200]}...")


if __name__ == '__main__':
    main()

