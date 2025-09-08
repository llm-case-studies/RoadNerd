# Conversational Testing Scenarios (Patient Box)

Use these after completing the basic recipe in `client-testing-recipe.md`. Run `python3 RoadNerd/poc/core/roadnerd_client.py` and follow the prompts.

## 1) Multi‑Turn Context Use
- Paste OS info (end with empty line):
  - `PRETTY_NAME="Ubuntu 24.04.3 LTS"\nNAME="Ubuntu"\nVERSION_ID="24.04"` → Expect: intent=information, context stored.
- Ask: `What version of Ubuntu is this?` → Expect: Uses recent context to answer.

## 2) Problem → Info → Fix Flow
- Say: `My WiFi is not working on this laptop.` → Expect: intent=problem, diagnosis starts.
- Paste `nmcli dev status` output → Expect: intent=information, context grows.
- Ask: `What should I try next?` → Expect: LLM suggests steps or KB solution.

## 3) Code Fence / END / EOF Enders
- Paste log snippet and finish with ````` or `END` on its own line → Expect: input ends cleanly; no loops.

## 4) Large Paste Guardrail
- Paste ~200 lines of syslog. Then ask a question. Expect: client responsive, no memory spikes. If laggy, break into chunks and observe consistent context use.

## 5) Command Execution With Approval
- Ask a diagnostic question that elicits a KB suggestion. When prompted: `Execute suggested fix? (y/n)` choose `n` first, then re‑run and choose `y`.
- Manual exec tests:
  - `execute whoami` → Expect: returns the server’s user.
  - `execute id` → Expect: numeric uid/gid.
  - `execute ping -c 1 1.1.1.1` → Expect: success with latency.

## 6) Safety / Denylist (Sanity)
- Try: `execute rm -rf /tmp/should_not_exist` (harmless path) → Expect: server policy response or refusal. Do NOT try destructive commands.

## 7) Connectivity Context
- Ask: `Am I online?` → Expect: connectivity summary (DNS, gateway, interfaces) included in output if available.

## 8) Recovery & Edge Cases
- Press Ctrl‑D at prompt → Expect: “Input closed (EOF). Exiting.”
- Type `help` → Expect: help prints once (no recursion).

## Notes
- Server: `10.55.0.1:8080` must be reachable.
- For intermittent network: retry `status` or reconnect USB tethering.
- Share results using the template at the end of `client-testing-recipe.md`.
