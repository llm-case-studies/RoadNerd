# BACKLOG++ Disambiguation Plan: Uncertainty‑Aware Routing

## Motivation
When the classifier returns multiple low‑confidence categories (e.g., wifi/dns/routing), a single large brainstorm wastes tokens and adds noise. We need a compact loop that quickly reduces ambiguity, works with small LLMs, and remains safe.

## Vision (Small‑LLM Friendly)
- Faceted brainstorm across top‑k categories (k=2–3) with a category hint.
- Judge deterministically and favor “information gain” — checks that best separate categories.
- Probe only whitelisted, read‑only commands (≤3 checks total, 5s timeout, truncated output).
- Re‑judge with evidence; if still ambiguous, ask 1–2 clarifying questions or escalate creativity/model modestly.
- Hard budget: ideas ≤6, probes ≤3, ≤60s end‑to‑end.

## Flow (2 Passes Max)
1) Inputs: issue, top‑k categories + confidences (low).
2) Faceted brainstorm: for each category, request N=2 ideas with discriminative checks.
3) Judge: rank ideas, select top 2–3 discriminative checks overall.
4) Probe: run checks (read‑only whitelist) and attach evidence.
5) Judge again: pick winner; if ambiguous, ask clarifying question(s) or escalate creativity by +1 once.

## API & Engine Notes
- Current endpoints (works today):
  - `POST /api/ideas/brainstorm { issue, n, creativity }`
  - `POST /api/ideas/probe { ideas[], run_checks }`
  - `POST /api/ideas/judge { issue, ideas[] }`
- Near‑term enhancements (planned):
  - Add optional `category_hint` to brainstorm prompt.
  - Add `info_gain` scoring term in JudgeEngine.
  - Optional `RN_API_TOKEN` gating for probe/force when surface grows.

## Testing Strategy
- Manual (browser): `/api-docs`
  - Run brainstorm with category‑focused issue text (e.g., “Focus on wifi; distinguish from dns/routing”).
  - Probe the top checks; re‑judge.
- Scripted (fast loop): `tools/run_disambiguation_flow.py`
  - Inputs: `--issue`, `--categories wifi,dns,network`, `--base-url`, `--creativity`, `--n`.
  - Prints selected discriminative checks, probe results summary, and final ranking.
- Metrics to track:
  - Time‑to‑resolution, number of ideas/probes used, Success@1, token usage, and escalation rate.

## Safety & Budgets
- Probe whitelist only; 3 checks max; 5s timeout; ≤2KB output per check.
- Keep safe mode on; never auto‑execute fixes.
- Always present commented commands and require explicit approval.

## Fit with Current Work
- Complements BACKLOG++ brainstorm→probe→judge and prompt suite logging.
- Works with small models by adding structure, retrieval, and guardrails; escalates only when needed.

## Next Steps
1) Try the runner script on ambiguous issues and capture JSONL logs.
2) Add `category_hint` and `info_gain` in server.
3) Extend prompt suites with ambiguous cases; report Success@1 and time budgets by creativity/model.
