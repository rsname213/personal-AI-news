---
phase: 01-core-pipeline
plan: "05"
subsystem: infra
tags: [orchestrator, pipeline, dotenv, gmail, smtp, anthropic, jinja2]

# Dependency graph
requires:
  - phase: 01-core-pipeline
    provides: "fetchers (rss, paul_graham, gwern, anthropic_blog), filter, summarize, render, send"
provides:
  - "orchestrator.py — single entry point that runs the complete AI newsletter pipeline end-to-end"
  - "fail-soft fetching: any source failure logs [WARN] but never blocks email delivery"
  - "pre-flight env check: fails fast with clear message if credentials missing"
  - "python-dotenv auto-load: .env loaded at startup for local development ergonomics"
  - "verified live delivery: email sent to rsname213@gmail.com with 5 articles, 10,590 bytes HTML"
affects: [02-premium-sources, 03-github-actions, 04-refinement]

# Tech tracking
tech-stack:
  added: [python-dotenv>=1.0.0]
  patterns:
    - "fail-soft collector: each fetcher wrapped in try/except, partial email preferred over no email"
    - "pre-flight validation: _check_env() runs before any network calls for fast failure"
    - "linear stage pipeline: fetch -> filter -> summarize -> render -> send with [OK]/[WARN]/[ERROR] logging"
    - "optional dotenv: try/except ImportError allows GitHub Actions (no dotenv) and local (.env) to share same entry point"

key-files:
  created:
    - orchestrator.py
  modified:
    - requirements.txt

key-decisions:
  - "Fail-soft per source: individual fetcher exceptions log [WARN] and continue — partial email better than no email"
  - "Pre-flight env check before any network calls: ANTHROPIC_API_KEY, GMAIL_USER, GMAIL_APP_PASSWORD validated at startup"
  - "HTML size check: logs [WARN] if >102KB Gmail clip threshold, but does not abort send"
  - "python-dotenv loaded via try/except ImportError — GitHub Actions unaffected; local .env auto-loaded without shell source step"

patterns-established:
  - "Pipeline stages called linearly in main(): fetch -> filter -> summarize -> render -> send"
  - "collect_all() is the fail-soft aggregation layer — each fetcher isolated in its own try/except"

requirements-completed: [PIPE-01, PIPE-04, RSS-05]

# Metrics
duration: 15min
completed: 2026-03-01
---

# Phase 1 Plan 05: Orchestrator Summary

**orchestrator.py wires all 5 pipeline stages into a working end-to-end daily email — verified live: 5 articles, 10,590-byte HTML delivered to Gmail**

## Performance

- **Duration:** ~15 min (including human-verify checkpoint wait)
- **Started:** 2026-03-01T18:55:10Z
- **Completed:** 2026-03-01
- **Tasks:** 2 of 2 (both complete)
- **Files modified:** 2

## Accomplishments
- Created orchestrator.py at repo root — single `python3 orchestrator.py` command runs the full pipeline
- collect_all() wraps each of the four fetchers in try/except; any source failure logs [WARN] but never blocks delivery
- _check_env() validates all three required env vars before any network calls, with actionable error message
- main() calls all five pipeline stages in sequence with [OK]/[WARN]/[ERROR] logging and article counts
- Verified live end-to-end delivery: email sent to rsname213@gmail.com, 5 articles, subject "AI Briefing — March 1, 2026", HTML 10,590 bytes
- Added python-dotenv auto-load so local runs work without a manual `source .env` shell step

## Task Commits

Each task was committed atomically:

1. **Task 1: Create orchestrator.py — pipeline entry point** - `f21b06b` (feat)
2. **Task 2 deviation: load .env via python-dotenv for local runs** - `d2e71f2` (fix)

**Plan metadata:** (this SUMMARY.md + STATE.md + ROADMAP.md commit)

## Files Created/Modified
- `orchestrator.py` — Pipeline entry point: wires all stages end-to-end, fail-soft per source, exits 0/1
- `requirements.txt` — Added python-dotenv>=1.0.0

## Decisions Made
- Fail-soft per source in collect_all() — any individual fetcher exception logs [WARN] and continues; partial email preferred over no email
- Pre-flight _check_env() validates credentials before any network calls for fast, clear failure
- HTML size checked and warned (not blocked) at 102KB threshold to preserve deliverability
- python-dotenv loaded via try/except ImportError — GitHub Actions (env vars injected directly) and local (.env file) share the same entry point without any conditional logic

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical] Added python-dotenv auto-load for local development**
- **Found during:** Task 2 (checkpoint:human-verify — post-approval cleanup)
- **Issue:** orchestrator.py required `set -a; source .env; set +a` before running locally — error-prone manual step not noted in plan
- **Fix:** Added `from dotenv import load_dotenv; load_dotenv()` wrapped in try/except ImportError at module startup; added python-dotenv>=1.0.0 to requirements.txt
- **Files modified:** orchestrator.py, requirements.txt
- **Verification:** Pipeline ran successfully after fix — email delivered to Gmail inbox
- **Committed in:** d2e71f2

---

**Total deviations:** 1 auto-fixed (1 missing critical — developer ergonomics)
**Impact on plan:** Essential for local development workflow. No scope creep. GitHub Actions path unaffected (try/except ImportError handles missing dotenv gracefully).

## Issues Encountered
None — checkpoint verification confirmed pipeline ran cleanly. 5 articles fetched, filtered, summarized, rendered (10,590 bytes HTML), and delivered to Gmail inbox with correct subject format.

## User Setup Required
Credentials must be configured before running. Requires:
- `ANTHROPIC_API_KEY` — Claude API key for summarization
- `GMAIL_USER` — Gmail address (sender and recipient)
- `GMAIL_APP_PASSWORD` — Gmail App Password (not account password)

For local runs: copy `.env.example` to `.env`, fill in values — orchestrator.py auto-loads it via python-dotenv.
For GitHub Actions: add all three as repository secrets (Phase 3 work).

## Next Phase Readiness
- Phase 1 complete: all 5 plans executed, end-to-end email delivery verified live
- Phase 2 (Polish and Resilience) can begin: orchestrator.py is the stable entry point
- Phase 3 (Automation) is unblocked: `python orchestrator.py` is the exact command GitHub Actions will invoke

---
*Phase: 01-core-pipeline*
*Completed: 2026-03-01*
