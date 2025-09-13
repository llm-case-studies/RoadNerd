# RoadNerd Additional Feature Proposal: Meaningful Command History + Guided Self‑Help

## Summary
Add a local‑first, privacy‑preserving command history system with semantic search and an LLM “self‑help” assistant. The assistant suggests commented commands (never auto‑executes); users review, edit, and run by uncommenting. All commands and suggestions are indexed for recall, learning, and cross‑machine sync.

## Goals
- Fast recall: fuzzy/semantic search over past commands with context (host, dir, exit, time).
- Safety first: suggestions are inserted as commented lines (e.g., `# llm: ...`). No auto‑run.
- Local‑first: run without network; optional sync and E2E encryption.
- Minimal friction: one keybinding (Ctrl+g) to request help; Ctrl+r to search.

Non‑Goals (initial)
- Shell output capture/collection; we only store commands + metadata.
- Remote execution/agent control.

## User Experience
- Suggest: press Ctrl+g → buffer prefilled with lines like:
  - `# llm: scp -r build/ deploy@ionos-4c8g:/srv/app/`
  - `# why: Sync build artifacts to pre‑prod`
  - User removes `# ` to run, or edits first.
- Search: Ctrl+r shows history with filters (`host:`, `dir:`, `exit:`, `after:`). Enter to paste or run.
- Logging: each command stores ts, dir, host, duration, exit. Suggestions store prompt, rationale, accepted/edited/declined.

## Architecture Overview
- Shell bindings: bash/zsh widgets to capture commands and invoke the assistant.
- Local store: SQLite with FTS5 (keyword/fuzzy) and optional sqlite‑vec embeddings (semantic).
- Suggestion engine: pluggable LLM client (Ollama by default). Offline by design.
- Sync (optional): git/Syncthing for simple cases; or small HTTPS service with E2E encryption.

## Data Model (SQLite)
- `commands(id, ts, host, user, shell, dir, text, exit_code, duration_ms, tags)`
- `suggestions(id, ts, host, dir, prompt, suggestion, rationale, accepted, edited_text, command_id)`
- `commands_fts(text, tags)` (FTS5 virtual table)
- `commands_vec(embedding BLOB)` (optional, via sqlite‑vec)

## Bash/Zsh Integration
- Capture (bash):
  - `trap 'RN_CMD=$BASH_COMMAND; RN_TS=$(date +%s%3N)' DEBUG`
  - `PROMPT_COMMAND='RN_RET=$?; RN_DUR=$(($(date +%s%3N)-RN_TS)); roadnerd-log "$RN_CMD" "$RN_RET" "$RN_DUR"'`
- Suggest keybinding (bash):
  - `bind -x '"\C-g": roadnerd-suggest'`
  - `roadnerd-suggest` calls `roadnerd suggest` and sets `READLINE_LINE` to a commented proposal; point at current cwd, git branch, last command.
- Zsh: equivalent `zle` widget to prefill buffer.

## LLM Suggestion Engine
- Provider: Ollama HTTP (`http://localhost:11434/api/generate`) with small instruct models (e.g., `qwen2.5:7b-instruct`). Swappable to vLLM or OpenAI.
- Prompt context: cwd, git branch/status, last 5 commands, host, tags. Hard rule in system prompt: “Only output shell commands; never execute; use commented lines `# llm:` and `# why:`.”
- Token/PII safety: redact using patterns (e.g., `AWS[_-]?SECRET|ghp_[A-Za-z0-9]{36}`) before sending to the model.

## Search & Retrieval
- CLI: `roadnerd search '<query>' [--host H --dir D --after T --exit 0]` prints ranked commands.
- Interactive: `roadnerd search ... | fzf` to insert into buffer.
- Semantic: on enable, compute 384‑dim embeddings (e.g., MiniLM) and hybrid rank (BM25 + cosine).

## Sync Options
- Simple: sync the SQLite DB with Syncthing or git (single‑user).
- Multi‑user server: REST endpoints `POST /events` (encrypted blob), `GET /events/since`. Clients E2E‑encrypt with user keypair; server stores ciphertext + minimal metadata.

## Security & Privacy
- Never auto‑execute. Commented suggestions only; user must edit/uncomment.
- Redaction/ignore: leading space to skip logging; ignore patterns in config; command‑class allowlist (opt‑in).
- Local encryption (optional): SQLCipher or file‑system encryption for the DB.
- Sync encryption: E2E; rotate keys; no plaintext on server.

## Configuration
- File: `~/.config/roadnerd/config.toml`
  - `[store] path="~/.local/share/roadnerd/history.db"`
  - `[suggest] provider="ollama" model="qwen2.5:7b-instruct" max_suggestions=3`
  - `[ignore] patterns=["ghp_[A-Za-z0-9]{36}", "AWS[_-]?SECRET"]`
  - `[ui] prefer_paste=true`  (enter pastes into prompt instead of running)

## CLI Surface (MVP)
- `roadnerd log <text> --exit N --duration MS` — append to DB (used by PROMPT_COMMAND).
- `roadnerd suggest [--context auto]` — emit commented suggestions and rationale.
- `roadnerd search <query> [filters]` — list prior commands.
- `roadnerd doctor` — validate perms, DB, shell hooks.

## Rollout Plan
1) MVP: SQLite + FTS, bash/zsh hooks, Ctrl+g suggest, Ctrl+r search integration, redaction rules.
2) Semantic search: embeddings + hybrid rank.
3) Sync: git/Syncthing profile; then E2E server for multi‑user.
4) Hardening: tests, perf profile, config UI, export/import.

## Risks & Mitigations
- Suggestion drift or dangerous commands → comment‑only insertion, safe filters, require manual edit.
- Secret leakage → on‑device LLM by default, redaction, ignore patterns, allowlist mode.
- DB growth → periodic vacuum/retention policy (e.g., keep last N=100k commands).

## Success Metrics
- Median time‑to‑recall prior command < 2s.
- >70% suggestions accepted or lightly edited in week 2 of use.
- Zero incidents of unintended execution; no secrets stored (CI lints redaction).
