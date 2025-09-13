UI Testing with Playwright (for Gemini Flash)

Purpose
- Provide ready-to-run prompts and test ideas for Gemini Flash to exercise the RoadNerd UI with Playwright.
- Keep runs small, fast, and artifact-rich (screenshots + network + console).

Assumptions
- Server base URL provided by a human (Alex/Claude) before tests (e.g., http://localhost:8080 or http://10.55.0.1:8080).
- If API routes are gated, a human provides RN_API_TOKEN and Gemini includes `Authorization: Bearer <token>` in requests that require it.
- Playwright MCP is available with the following tools: browser_install, browser_navigate, browser_evaluate, browser_take_screenshot, browser_network_requests, browser_console_messages, browser_snapshot.

Quick Start Prompt (one-shot)
"""
You are Gemini Flash with Playwright tools. Please run a short UI smoke on RoadNerd.

Inputs:
- baseUrl: <PASTE_BASE_URL_HERE>, e.g., http://localhost:8080
- token (optional): <PASTE_IF_REQUIRED>

Plan:
1) Install Chromium
2) Navigate to {baseUrl}/api-docs and capture a screenshot
3) From the page, fetch GET {baseUrl}/api/status and show JSON
4) Validate the API console loads external JS: /static/js/api-console.js
5) Navigate to {baseUrl}/bundle-ui, take a screenshot, and call /api/bundle/status
6) Collect network log and console messages

Please use these MCP calls (in order):
- browser_install { browser: "chromium" }
- browser_navigate { url: "{baseUrl}/api-docs" }
- browser_take_screenshot { filename: "api-docs.png" }
- browser_evaluate with function: `() => fetch('/api/status').then(r=>r.json())`
- browser_network_requests
- browser_console_messages
- browser_navigate { url: "{baseUrl}/bundle-ui" }
- browser_take_screenshot { filename: "bundle-ui.png" }
- browser_evaluate with function: `() => fetch('/api/bundle/status').then(r=>r.json())`

Output:
- Summarize: status JSON, bundle status JSON, and top 3 console messages.
- Attach both screenshots. Note any obvious UI/JS errors.
"""

Modular Prompts (step-by-step)

1) Setup + Navigate
"""
Install Chromium and open the API console page.
1. browser_install { browser: "chromium" }
2. browser_navigate { url: "{baseUrl}/api-docs" }
3. browser_take_screenshot { filename: "01-api-docs.png" }
Return: "navigated" when done.
"""

2) Status + Headers
"""
From the current page context, fetch and show server status.
1. browser_evaluate function: `() => fetch('/api/status').then(r=>r.json())`
2. browser_network_requests
3. browser_console_messages
Check: a request for /api-docs (or /) includes Content-Security-Policy in response headers.
Return: status JSON, whether CSP header is present, and the first 5 console messages.
"""

3) API Console Buttons (functional smoke)
"""
Use browser_evaluate to simulate the same calls as the console buttons:
- Diagnose: `fetch('/api/diagnose',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({issue:'My WiFi is not working',debug:true})}).then(r=>r.json())`
- Ideas (brainstorm): `fetch('/api/ideas/brainstorm',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({issue:'DNS resolution is failing on Ubuntu.',n:3,creativity:1})}).then(r=>r.json())`
- Probe: `fetch('/api/ideas/probe',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({ideas:[{"hypothesis":"DNS misconfiguration","category":"dns","why":"resolv.conf wrong","checks":["dig example.com"]}],run_checks:true})}).then(r=>r.json())`
Return: small summaries for each call: HTTP ok, keys present, counts.
"""

4) Model Section (graceful behavior)
"""
Call /api/model/list and /api/model/switch with a harmless value.
- `fetch('/api/model/list').then(r=>r.json())`
- If available_models exists, pick the current or a small model (e.g., 'llama3.2') and POST to /api/model/switch:
  `fetch('/api/model/switch',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({model:'llama3.2'})}).then(r=>r.json())`
Return: whether list call succeeded and whether switch call responded with success or a clear error.
Note: If Ollama is not running or models are missing, capture the error JSON (this is expected on some machines).
"""

5) Bundle UI
"""
Navigate to {baseUrl}/bundle-ui.
1. browser_navigate { url: "{baseUrl}/bundle-ui" }
2. browser_take_screenshot { filename: "02-bundle-ui.png" }
3. browser_evaluate function: `() => fetch('/api/bundle/status').then(r=>r.json())`
Return: screenshot and current bundle status JSON. Note if `status`='running' or 'completed'.
"""

6) Artifacts and Report
"""
Collect and summarize:
- browser_network_requests
- browser_console_messages
Output a short report:
- URL tested, server status (ok/error)
- API console checks (diagnose, ideas, probe) with pass/fail
- Model list/switch result
- Bundle UI screenshot present and bundle status JSON
- Notable console errors (first 5 lines)
Include the two screenshots in the final output if your environment allows attachments.
"""

Negative/Edge Cases (optional prompts)
- Missing server: Expect navigation failure/timeout; report clearly and ask for a valid base URL.
- CSP violation: Check if inline scripts exist (should not). Note if CSP header missing.
- Safe mode: Execute endpoint with force flag (expect 403 unless RN_ALLOW_FORCE is set). Report that safety is enforced.
- No storage devices: Bundle scan returns empty `drives` array; report gracefully.

Hints for Humans (to start server)
- Typical start: `RN_SAFE_MODE=true RN_PORT=8080 python3 RoadNerd/poc/core/roadnerd_server.py`
- If using a different host/port, share the exact base URL with Gemini and mention any RN_API_TOKEN.

What “Good” Looks Like
- GET /api/status returns JSON with keys: server, system, connectivity, model
- /api-docs loads and references /static/js/api-console.js (no inline JS errors)
- Basic POST endpoints return 200 JSON (or an informative error if deps missing)
- /bundle-ui renders and /api/bundle/status responds with a JSON object
- CSP header present and no blocked inline scripts

Notes
- The Playwright run should prefer small payloads (n=3, creativity=1) to keep tests quick.
- If Ollama is down or models aren’t present, treat failures as environment findings, not UI failures.

