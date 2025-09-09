#!/usr/bin/env python3
"""
Simple hybrid retrieval over KB/profile snippets.

If Whoosh and sentence-transformers are installed, use them; otherwise, fall back to a
lightweight keyword scoring.
"""
from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple


@dataclass
class Snippet:
    source: str
    text: str
    score: float


class HybridRetriever:
    def __init__(self, root: Optional[Path] = None) -> None:
        self.root = root or Path(__file__).resolve().parents[3]  # repo root
        self.docs: List[Tuple[str, str]] = []  # (source, text)
        self._load_default_corpus()
        self._embed = None
        self._use_embed = False
        try:
            from sentence_transformers import SentenceTransformer
            self._embed = SentenceTransformer('all-MiniLM-L6-v2')
            self._use_embed = True
        except Exception:
            self._use_embed = False

    def _load_default_corpus(self) -> None:
        # Load small subset from docs and poc/docs
        paths = []
        paths += list((self.root / 'RoadNerd' / 'docs').rglob('*.md'))
        paths += list((self.root / 'RoadNerd' / 'poc' / 'docs').rglob('*.md'))
        # Limit to first ~40 files for speed
        for p in paths[:40]:
            try:
                txt = p.read_text(encoding='utf-8', errors='ignore')
            except Exception:
                continue
            # Split into paragraphs
            for para in re.split(r"\n\s*\n", txt):
                para = para.strip()
                if 64 <= len(para) <= 600:
                    self.docs.append((str(p), para))

    @staticmethod
    def _tokenize(text: str) -> List[str]:
        return re.findall(r"[a-zA-Z0-9_]+", text.lower())

    def search(self, query: str, category_hint: Optional[str] = None, k: int = 3) -> List[Snippet]:
        if not self.docs:
            return []
        q_tokens = self._tokenize(query)
        if category_hint:
            q_tokens += [category_hint.lower()]

        # Very small keyword scoring
        scored: List[Snippet] = []
        for src, para in self.docs:
            text_lower = para.lower()
            s = sum(2 if t in text_lower else 0 for t in q_tokens)
            s += sum(1 for t in set(q_tokens) if t in text_lower)
            if s > 0:
                scored.append(Snippet(src, para, float(s)))
        scored.sort(key=lambda x: x.score, reverse=True)
        return scored[:k]

