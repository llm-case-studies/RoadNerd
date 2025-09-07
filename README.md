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

- **Immediate**: Bootstrap client download, model escalation ladder
- **Phase 2**: Command history with semantic search, shell integration  
- **Phase 3**: Boot-loop diagnostic system, collaborative intelligence

## Philosophy

*"The most sustainable AI is the one that uses just enough intelligence to solve the problem effectively."*

Following the **Cave Ancestor Wisdom**: practical solutions that work in the field beat theoretical perfection.

---

**Status**: Working POC with real-world validation. Ready for enhancement and broader deployment.

For detailed testing results and feedback from industry experts, see the [documentation](poc/docs/).