#!/usr/bin/env python3
import argparse
from pathlib import Path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('text', nargs='*', help='Sample input text (or reads stdin)')
    args = ap.parse_args()

    try:
        from poc.core.classify import InputDetector, CategoryClassifier
    except Exception:
        from RoadNerd.poc.core.classify import InputDetector, CategoryClassifier  # fallback

    if args.text:
        txt = ' '.join(args.text)
    else:
        import sys
        txt = sys.stdin.read()

    det = InputDetector().detect(txt)
    clf = CategoryClassifier().classify(txt)

    print('InputType:', det)
    print('CategoryPrediction:', clf)


if __name__ == '__main__':
    main()
