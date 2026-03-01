---
phase: 01-core-pipeline
plan: "05"
subsystem: infra
tags: [orchestrator, pipeline, gmail, smtp, anthropic, jinja2]

# Dependency graph
requires:
  - phase: 01-core-pipeline
    provides: "fetchers (rss, paul_graham, gwern, anthropic_blog), filter, summarize, render, send"
provides:
  - "orchestrator.py — single entry point that runs the complete AI newsletter pipeline end-to-end"
  - "fail-soft fetching: any source failure logs [WARN] but never blocks email delivery"
  - "pre-flight env check: fails fast with clear message if credentials missing"
affects: [02-premium-sources, 03-github-actions, 04-refinement]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "fail-soft collector: each fetcher wrapped in try/except, partial email preferred over no email"
    - "pre-flight validation: _check_env() runs before any network calls for fast failure"
    - "linear stage pipeline: fetch -> filter -> summarize -> render -> send with [OK]/[WARN]/[ERROR] logging"

key-files:
  created:
    - orchestrator.py
  modified: []

key-decisions:
  - "Fail-soft per source: individual fetcher exceptions log [WARN] and continue — partial email better than no email"
  - "Pre-flight env check before any network calls: ANTHROPIC_API_KEY, GMAIL_USER, GMAIL_APP_PASSWORD validated at startup"
  - "HTML size check: logs [WARN] if >102KB Gmail clip threshold, but does not abort send"

patterns-established:
  - "Pipeline stages called linearly in main(): fetch -> filter -> summarize -> render -> send"
  - "collect_all() is the fail-soft aggregation layer — each fetcher isolated in its own try/except"

requirements-completed: [PIPE-01, PIPE-04, RSS-05]

# Metrics
duration: 5min
completed: 2026-03-01
---

# Phase 1 Plan 05: Orchestrator Summary

**Single-file pipeline entry point (orchestrator.py) that wires all four fetchers and four pipeline stages into a fail-soft end-to-end flow with pre-flight credential validation**

## Performance

- **Duration:** ~5 min
- **Started:** 2026-03-01T18:55:10Z
- **Completed:** 2026-03-01T19:00:00Z
- **Tasks:** 1 of 2 (Task 2 is checkpoint:human-verify — awaiting email confirmation)
- **Files modified:** 1

## Accomplishments
- Created orchestrator.py at repo root — the single command to run the full pipeline
- collect_all() wraps each of the four fetchers in try/except; any source failure logs [WARN] but never blocks delivery
- _check_env() validates all three required env vars before any network calls, with actionable error message
- main() calls all five pipeline stages in sequence with [OK]/[WARN]/[ERROR] logging and article counts
- HTML size check warns (but does not abort) if output exceeds 102KB Gmail clip threshold

## Task Commits

Each task was committed atomically:

1. **Task 1: Create orchestrator.py — pipeline entry point** - `f21b06b` (feat)
2. **Task 2: Verify end-to-end pipeline delivers email to Gmail** - awaiting human verification

**Plan metadata:** (pending final commit)

## Files Created/Modified
- `orchestrator.py` — Pipeline entry point: wires all stages end-to-end, fail-soft per source, exits 0/1

## Decisions Made
- Fail-soft per source in collect_all() — any individual fetcher exception logs [WARN] and continues; partial email preferred over no email
- Pre-flight _check_env() validates credentials before any network calls for fast, clear failure
- HTML size checked and warned (not blocked) at 102KB threshold to preserve deliverability

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
Credentials must be configured before running. Requires:
- `ANTHROPIC_API_KEY` — Claude API key for summarization
- `GMAIL_USER` — Gmail address (sender and recipient)
- `GMAIL_APP_PASSWORD` — Gmail App Password (not account password)

For local runs: copy `.env.example` to `.env` and fill in values, then `set -a; source .env; set +a`.
For GitHub Actions: add all three as repository secrets.

## Next Phase Readiness
- orchestrator.py ready for end-to-end test once credentials are configured
- Phase 2 (premium sources: WSJ, The Information cookie-based scraping) can begin after email verification
- GitHub Actions workflow (Phase 3) can reference `python orchestrator.py` as the single pipeline command

---
*Phase: 01-core-pipeline*
*Completed: 2026-03-01*
