# RoadNerd — Portable, Offline System Diagnostics (MIT)

RoadNerd is your pocket sysadmin: a tiny, safe diagnostics server + client that works without internet. It guides troubleshooting over a direct Ethernet link (10.55.0.x), using small local LLMs — fast enough on laptops, accurate enough for field fixes.

## Why RoadNerd
- Works offline: diagnose when the network is broken.
- Small-model friendly: performs with 1B–8B models; scales up when needed.
- Safe by design: never auto‑executes; fixes are commented and require approval.
- Portable and fast: start server, connect patient, get guidance in under a minute.

## Proof Points (from real tests)
- Model ladder throughput (MSI i9‑14900HX):
  - 1B: ~83 tokens/s, 3B: ~55 t/s, 8B: ~31 t/s, 13B code model: ~9 t/s
- New Ideas API (brainstorm → probe → judge) improves success rate on vague issues.
- Prompt templates hot‑reload for rapid tuning; JSONL logging for evaluation.
- Direct Ethernet workflow: no USB needed; patient ↔ nerd on 10.55.0.1:8080.

## Quick Start
- Server (nerd):
  - `python3 RoadNerd/poc/core/roadnerd_server.py`
  - Open `http://10.55.0.1:8080/api-docs` (API console)
- Patient (client):
  - `python3 RoadNerd/poc/core/roadnerd_client.py http://10.55.0.1:8080`

## What’s Inside
- API console for browser testing; safe command execution; knowledge base; machine profiles.
- Disambiguation flow for low‑confidence cases: small, high‑value probes before fixes.
- Evaluation harness: prompt suite + aggregator; ideas workflow logging to JSONL.

Contribute, test, and tell us what breaks — RoadNerd gets better from real‑world feedback.
