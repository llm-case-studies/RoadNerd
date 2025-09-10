#!/usr/bin/env python3
"""
Lightweight input type detector and category classifier.

Design:
- No auto-install. If sentence-transformers is available, we use MiniLM for embeddings.
- Otherwise, we fall back to simple regex/keyword heuristics.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List, Tuple, Optional, Dict


@dataclass
class InputType:
    label: str
    confidence: float


@dataclass
class CategoryPrediction:
    label: str
    confidence: float
    candidates: List[Tuple[str, float]]


class InputDetector:
    @staticmethod
    def detect(text: str) -> InputType:
        if not text or not text.strip():
            return InputType('empty', 1.0)

        signals = {
            'shell': 0,
            'log': 0,
            'error': 0,
            'free_text': 0,
        }
        lines = text.splitlines()

        for ln in lines[:50]:
            s = ln.strip()
            if re.search(r"^[a-zA-Z0-9_.-]+@[a-zA-Z0-9_.-]+:~?\$", s):
                signals['shell'] += 2
            if re.search(r"(ERROR|WARN|INFO|TRACE|DEBUG)[ :]", s):
                signals['log'] += 1
            if re.search(r"(Exception|Traceback|stack trace)", s, re.IGNORECASE):
                signals['error'] += 2
            if len(s.split()) > 4 and not re.search(r"[/\\]|:\\|==|::", s):
                signals['free_text'] += 0.5

        # Choose the max signal; compute a crude confidence
        label = max(signals.items(), key=lambda kv: kv[1])[0]
        total = sum(signals.values()) or 1
        confidence = signals[label] / total
        return InputType(label, min(1.0, confidence))


class CategoryClassifier:
    CATEGORIES = [
        'power',        # Battery, charger, won't turn on, power button
        'boot',         # BIOS, bootloader, OS startup, won't start
        'hardware',     # RAM, storage, motherboard, physical damage
        'physical',     # Dropped, liquid damage, environmental issues
        'software',     # Drivers, applications, OS corruption, crashes
        'user',         # Wrong expectations, user error, wrong device
        'network',      # WiFi, ethernet, internet connectivity, DNS
        'performance',  # Slow, overheating, resource issues
        'system'        # General system configuration issues
    ]

    # Simple heuristics
    HEUR_PATTERNS: Dict[str, List[re.Pattern]] = {
        'power': [re.compile(p, re.I) for p in [r"battery|charger|power|turn on|won't start|dead|plug|charge|power button|no lights|black screen"]],
        'boot': [re.compile(p, re.I) for p in [r"boot|bios|grub|startup|won't start|blue screen|kernel panic|post|loading"]],
        'hardware': [re.compile(p, re.I) for p in [r"ram|memory|disk|drive|motherboard|cpu|fan|temperature|beep|clicking|hardware"]],
        'physical': [re.compile(p, re.I) for p in [r"dropped|spill|liquid|water|coffee|damage|cracked|broken|truck|physical"]],
        'software': [re.compile(p, re.I) for p in [r"driver|application|program|crash|freeze|virus|malware|update|install|corrupt"]],
        'user': [re.compile(p, re.I) for p in [r"how to|don't know|confused|wrong|not mine|toy|fake|expected|should|supposed"]],
        'network': [re.compile(p, re.I) for p in [r"wifi|wlan|internet|network|connection|dns|ip\s+addr|ethernet|gateway|ssid"]],
        'performance': [re.compile(p, re.I) for p in [r"slow|lag|freeze|hang|high cpu|memory|swap|load|iowait|overheat"]],
        'system': [re.compile(p, re.I) for p in [r"kernel|dmesg|journalctl|os-release|packages|configuration|settings"]],
    }

    def __init__(self) -> None:
        self._emb = None
        self._labels_emb = None
        # Try to load sentence-transformers if present
        try:
            from sentence_transformers import SentenceTransformer
            self._emb = SentenceTransformer('all-MiniLM-L6-v2')
            self._labels_emb = self._emb.encode(self.CATEGORIES, convert_to_numpy=True)
        except Exception:
            self._emb = None

    @staticmethod
    def _heuristic_scores(text: str) -> List[Tuple[str, float]]:
        scores: List[Tuple[str, float]] = []
        for cat, pats in CategoryClassifier.HEUR_PATTERNS.items():
            s = sum(1.0 for p in pats if p.search(text))
            scores.append((cat, s))
        # Normalize
        total = sum(s for _, s in scores) or 1
        scores = [(c, (s / total)) for c, s in scores]
        return sorted(scores, key=lambda kv: kv[1], reverse=True)

    def classify(self, text: str) -> CategoryPrediction:
        if not text or not text.strip():
            return CategoryPrediction('system', 0.0, [('system', 0.0)])

        # Heuristic baseline
        heur = self._heuristic_scores(text)

        # Embedding-based override if available
        if self._emb is not None:
            import numpy as np
            try:
                q = self._emb.encode([text], convert_to_numpy=True)[0]
                # cosine similarity
                sims = self._labels_emb @ q / (
                    np.linalg.norm(self._labels_emb, axis=1) * (np.linalg.norm(q) or 1)
                )
                pairs = list(zip(self.CATEGORIES, sims.tolist()))
                pairs.sort(key=lambda kv: kv[1], reverse=True)
                top_label, top_score = pairs[0]
                # Map cosine [-1,1] to [0,1]
                conf = max(0.0, (top_score + 1) / 2)
                return CategoryPrediction(top_label, conf, pairs[:3])
            except Exception:
                pass

        # Fallback to heuristics
        top_label, top_score = heur[0]
        return CategoryPrediction(top_label, float(top_score), heur[:3])

