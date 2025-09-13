# RoadNerd - Portable System Diagnostics

*Your pocket-sized sysadmin for when WiFi goes wrong and DNS goes dark*

![RoadNerd Logo](https://img.shields.io/badge/RoadNerd-Portable%20Diagnostics-brightgreen)
![Status](https://img.shields.io/badge/Status-Working%20POC-success)
![Python](https://img.shields.io/badge/Python-3.8+-blue)

## Quick Start

**Server (BeeLink/Helper Device)**:
```bash
cd poc/core
./setup_roadnerd.sh
./roadnerd_server.sh
```

**Client (Patient System)**:
```bash
python3 roadnerd_client.py
# Or specify server: python3 roadnerd_client.py http://10.55.0.1:8080
```

New: API Console and Ideas Workflow
- Open the API console in a browser: `http://<server>:8080/api-docs`  
  Run status/diagnose/execute and the new ideas endpoints (brainstorm, probe, judge) interactively.
- Prompt templates hot‑reload from `poc/core/prompts/` (override with `RN_PROMPT_DIR`). No server restart needed.

## What is RoadNerd?

RoadNerd solves the classic IT problem: **you need internet to fix internet problems**. When you're stuck in a hotel room with broken DNS, or your laptop won't connect to conference WiFi, RoadNerd provides an offline AI assistant for system troubleshooting.

### Architecture

- **Server**: Runs on a portable device (BeeLink mini-PC, second laptop) with local LLM
- **Client**: Connects to server from the "patient" system needing help  
- **Connection**: Direct ethernet, USB tethering, or local hotspot
- **Intelligence**: Llama 3.2 (3B-13B models) for diagnostic guidance

## Proven Features ✅

- ✅ **Works Offline**: No internet required for basic troubleshooting
- ✅ **Network Auto-Discovery**: Finds server on local network automatically  
- ✅ **Safe Command Execution**: Analyzes commands for safety before running
- ✅ **Knowledge Base**: Built-in solutions for common IT issues
- ✅ **Multiple Connection Types**: Ethernet, USB, WiFi hotspot
- ✅ **Model Flexibility**: Swap models via configuration

## Project Structure

```
├── poc/                    # Working implementation (tested!)
│   ├── core/              # Server, client, setup scripts
│   ├── docs/              # Journey documentation & testing results
│   └── features/          # Advanced feature proposals
├── src/                   # Future: refactored architecture  
├── hardware/              # Hardware compatibility guides
├── examples/              # Case studies and use examples
└── deploy/                # Deployment configurations
```

Key Developer Utilities
- Disambiguation runner: `python3 RoadNerd/tools/run_disambiguation_flow.py --issue "Internet not working" --categories wifi,dns,network`
- Prompt suite (Phase 0): `python3 RoadNerd/tools/run_prompt_suite.py --base-url http://localhost:8080`
- Aggregator: `python3 RoadNerd/tools/aggregate_llm_runs.py`
- Classifier test: `python3 RoadNerd/tools/test_classifier.py "My WiFi is not working"`
- Retrieval test: `python3 RoadNerd/tools/test_retrieval.py --query "dns failing" --category dns`
- End‑to‑end runner: `BASE_URL=http://localhost:8080 CLS_URL=http://127.0.0.1:7080 RN_LOG_DIR=$HOME/.roadnerd/logs bash RoadNerd/run-all.sh`
  (Runs prompt suite → aggregates logs → disambiguation → scans logs via Code‑Log‑Search MCP; writes a report under `$RN_LOG_DIR/e2e/`)

## Real-World Testing

- **Hardware**: BeeLink mini-PC ↔ MSI laptop via ethernet  
- **Location**: Resort with client-isolated WiFi (hostile environment)
- **Model**: Llama 3.2:3b (surprisingly capable!)
- **Result**: Successfully diagnosed network issues, DNS problems, interface configuration

## Key Insights

1. **Small models work well** for structured troubleshooting
2. **Connection flexibility** matters more than connection type
3. **Guided reasoning** > raw model size for many tasks
4. **Field constraints** drive robust design

## Getting Started

See [poc/docs/founders-story.md](poc/docs/founders-story.md) for the full development journey from USB dreams to ethernet reality.

## Roadmap

- **Immediate**: Bootstrap client download, model escalation ladder, ideas API (brainstorm→probe→judge), prompt templates with hot‑reload, disambiguation flow
- **Phase 2**: Command history with semantic search, shell integration  
- **Phase 3**: Boot-loop diagnostic system, collaborative intelligence

## Philosophy

*"The most sustainable AI is the one that uses just enough intelligence to solve the problem effectively."*

Following the **Cave Ancestor Wisdom**: practical solutions that work in the field beat theoretical perfection.

---

**Status**: Working POC with real-world validation. Ready for enhancement and broader deployment.

For detailed testing results and feedback from industry experts, see the [documentation](poc/docs/), the [Release Highlights](docs/marketing/RELEASE-HIGHLIGHTS.md), the [One‑Pager](docs/marketing/ONE-PAGER.md), and our [Escalation Results](ESCALATION-RESULTS.md).
