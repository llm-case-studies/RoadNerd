# BACKLOG++ Proposal: Brainstorm → Judge Evaluation Framework

## Motivation
- Shrink the test–change–test loop for small LLMs by making evaluation structured, fast, and reproducible.
- Separate exploration (idea generation) from decision (ranking + execution) to keep safety and determinism.
- Accumulate comparable evidence across models/prompts/creativity levels to guide prompt and model tuning.

## Summary
Introduce two explicit modes wired into the API and client:
- Brainstorming mode: high exploration, N structured ideas, no side effects.
- Judging mode: deterministic scoring and ranking using a rubric; optional safe probing before judgment.
Capture every run as JSONL so we can compare models, prompts, and “improvisation” settings over time.

## Design Overview
- Modes
  - brainstorm: temperature/top_p↑, return structured candidates; block destructive suggestions server‑side.
  - judge: temperature=0, rubric scores (safety, success likelihood, cost, determinism), ranked shortlist.
  - probe (optional): run read‑only checks (ip/nmcli/dig/journalctl|head) to attach evidence to ideas.
- Improvisation knob (0–3)
  - 0 strict → 3 creative; determines brainstorm diversity (N, temperature/top_p). Judge always strict.
- Tiered prompts per model family/size (1B/3B/7B), with tight structure for small models.

## API Specs (Option A: Add modes to diagnose)
- POST `/api/diagnose`
  - request: `{ issue, mode: "brainstorm"|"judge", creativity?:0..3, n?:int, ideas?:Idea[], evidence?:Evidence[], client_context?:[], profile_name?:str }`
  - response (brainstorm): `{ ideas: Idea[], meta }`
  - response (judge): `{ ranked: RankedIdea[], rationale, meta }`

## API Specs (Option B: New endpoints)
- POST `/api/ideas/generate` → brainstorm
- POST `/api/ideas/probe` → run safe checks, attach summaries
- POST `/api/ideas/judge` → score/rank

Idea schema (minimal)
```
{
  id, category, hypothesis, why, 
  checks: ["nmcli dev status", "ip addr show"],
  fixes:  ["sudo systemctl restart NetworkManager"],
  risk: "low|medium|high"
}
```

## Logging & Metrics
- Storage: JSONL under `RoadNerd/logs/llm_runs/YYYYMMDD.jsonl` (one record per session/attempt).
- Record: timestamp, issue_id/session_id, model/backend, template_version, creativity, temp/top_p/num_predict, profile_name, brainstorm ideas, evidence digests, judge scores/ranking, selected idea, approval/execution result, tokens/time.
- Metrics: Success@1/@K, time‑to‑solution, steps‑to‑solution, safety incidents, token/latency budgets, escalation efficiency, per‑category accuracy.

## Implementation Plan
- Phase 0 (Instrumentation now)
  - Add JSONL logging for current `/api/diagnose` runs (mode="legacy") with model/env metadata.
  - Provide a minimal runner that replays YAML test cases and writes JSONL + Markdown summary.
- Phase 1 (Core modes)
  - Add brainstorm/judge (Option A or B). Enforce read‑only checks in probe. Filter dangerous fixes.
  - Client commands: `brainstorm <issue>`, `ideas`, `judge`, `execute <id>`.
  - Expose `creativity`, `model` via API and client flags; surface in `/api-docs` console.
- Phase 2 (Prompt suites + leaderboards)
  - Externalize prompt templates (hot‑reload) keyed by model tier.
  - Aggregator to compute leaderboards by model/template/creativity; JUnit/Markdown reports.
  - MCP/Playwright glue to run suites on demand.

## Enable & Use
- Server env (deterministic defaults for judge): `RN_TEMP=0 RN_NUM_PREDICT=128 RN_LLM_BACKEND=ollama RN_MODEL=llama3.2`
- Brainstorm example (API):
  - `POST /api/ideas/generate` → `{ issue, n:5, creativity:2 }`
- Probe example:
  - `POST /api/ideas/probe` → `{ ideas, run_checks:true }` (server whitelists read‑only commands)
- Judge example:
  - `POST /api/ideas/judge` → `{ ideas, evidence }` (returns ranked shortlist)
- Logs: inspect `logs/llm_runs/*.jsonl`; aggregate with a small script to summarize KPIs.

## Knowledge Accumulation
- Treat each JSONL record as a datapoint in an evaluation corpus.
- Attach outcomes to machine profiles (`profile_manager`) for environment‑sensitive guidance.
- Curate “prompt cards” (template_version → rationale, diffs, win conditions) and keep a leaderboard.
- Feed “winning” fixes into the KB or profile‑specific solutions.

## Comparison to Prior Strategy
- Before: manual interactive tests + ad‑hoc scripts → slower, less comparable, harder to regress‑test prompts.
- Now: standardized JSON outputs, deterministic judge, controlled creativity, easy cross‑model comparisons, and automated suites. Manual testing remains useful for UX and boundary conditions, but not the main evaluation engine.

## Fit with Current Repo
- Aligns with `profile_manager` (profile_name in logs, profile‑aware judging), `real_server_integration.py`, `local_flask_e2e.py`, and `/api-docs`.
- Uses existing env overrides for model/backend/temperature.
- Adds prompt hot‑reload (small server change) and new endpoints or modes.

## Risks & Mitigations
- Safety: brainstorm might suggest risky commands → server blocks non‑read‑only in probe; fixes always require approval.
- Variance: creative mode adds noise → judge at temp=0; compare on Success@K and cost.
- Data bloat/PII: log digests/summaries for evidence; redact sensitive paths.
- Overfitting to test set: rotate and grow case corpus; evaluate on unseen cases regularly.

## KPIs & Success Criteria
- >20% improvement in Success@1 for target categories (WiFi/DNS) over baseline.
- Median time‑to‑solution reduced by X%.
- Zero safety incidents in judge/execution path.
- Reproducible judge decisions at temp=0 across runs.

## Next Steps
1) Decide API shape (Option A single endpoint vs Option B dedicated ideas endpoints).
2) Add JSONL logging now (Phase 0) and a tiny aggregator script.
3) Externalize prompt templates and add hot‑reload.
4) Implement brainstorm/judge + client commands; update `/api-docs` to exercise new flows.
5) Integrate with MCP/Playwright to run suites on this machine against local LLMs.
