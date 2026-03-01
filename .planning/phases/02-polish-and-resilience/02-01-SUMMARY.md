---
phase: 02-polish-and-resilience
plan: 01
subsystem: pipeline
tags: [deduplication, url-normalization, json-persistence, pytest, tdd]

# Dependency graph
requires:
  - phase: 01-core-pipeline
    provides: orchestrator.py pipeline stages, FilteredArticle/SummarizedArticle types with .url attribute

provides:
  - pipeline/deduplicate.py with load_seen_urls, save_seen_urls, purge_old_entries, filter_duplicates, mark_as_seen
  - URL normalization stripping UTM params, lowercasing scheme+host, sorting query params, dropping fragment
  - .seen_urls JSON store with 7-day rolling window purge
  - Orchestrator Stage 2b wired between filter and summarize; save wired after send_email success only

affects:
  - 02-02 (template/render improvements may reference dedup output counts)
  - future phases using orchestrator.py pipeline order

# Tech tracking
tech-stack:
  added: [pytest]
  patterns: [TDD red-green, URL normalization via urllib.parse, JSON flat-file persistence]

key-files:
  created:
    - pipeline/deduplicate.py
    - tests/__init__.py
    - tests/test_deduplicate.py
  modified:
    - orchestrator.py
    - .gitignore

key-decisions:
  - "save_seen_urls called only after send_email() returns without exception — natural exception propagation guarantees no false-marking on SMTP failure (no try/except wrapping needed)"
  - "UTM_PARAMS set = {utm_source, utm_medium, utm_campaign, utm_term, utm_content} strips tracking noise before URL comparison"
  - "Non-UTM query params sorted with sorted() for stable normalized form regardless of original param order"
  - "SEEN_URLS_PATH derived from __file__ so module works correctly from any working directory"
  - "purge_old_entries uses datetime.now(timezone.utc).date() — UTC-aware, consistent with pipeline's UTC convention"
  - "7-day retention window balances dedup coverage vs storage growth; configurable via window_days param"

patterns-established:
  - "Dedup pattern: load → purge → filter → (pipeline) → mark → save — atomic save only on success"
  - "URL normalization: lowercase, strip UTM, sort remaining params, strip trailing slash, drop fragment"
  - "Corrupt/missing file gracefully returns {} — overwritten on next successful save"

requirements-completed: [PIPE-05]

# Metrics
duration: 2min
completed: 2026-03-01
---

# Phase 2 Plan 01: URL Deduplication Summary

**URL-based deduplication via .seen_urls JSON store with UTM-stripping normalization, 7-day rolling purge, and orchestrator wiring that saves only after successful send**

## Performance

- **Duration:** 2 min
- **Started:** 2026-03-01T19:27:04Z
- **Completed:** 2026-03-01T19:29:00Z
- **Tasks:** 2 (Task 1 TDD with 3 commits, Task 2 with 1 commit)
- **Files modified:** 5

## Accomplishments

- Implemented `pipeline/deduplicate.py` with all 5 public functions: `load_seen_urls`, `save_seen_urls`, `purge_old_entries`, `filter_duplicates`, `mark_as_seen`
- URL normalization strips all 5 UTM params, lowercases scheme+host, sorts remaining query params, strips trailing slash, drops fragment
- TDD with 26 tests covering all edge cases: missing file, corrupt JSON, OS error, UTM variants, window boundary conditions, sorted params, empty inputs
- Wired Stage 2b into orchestrator between filter (Stage 2) and summarize (Stage 3); `save_seen_urls` positioned after `send_email()` on success path only
- `__pycache__/` and `*.pyc` already present in .gitignore; added `.seen_urls` entry

## Task Commits

Each task was committed atomically:

1. **TDD RED: Failing tests for deduplicate** - `e5e48a4` (test)
2. **Task 1: pipeline/deduplicate.py implementation** - `cde1000` (feat)
3. **Task 2: orchestrator.py + .gitignore** - `f7e534e` (feat)

_Note: TDD task produced test commit (RED) then implementation commit (GREEN)._

## Files Created/Modified

- `pipeline/deduplicate.py` - URL deduplication module with 5 public functions and private _normalize_url
- `tests/__init__.py` - Test package marker
- `tests/test_deduplicate.py` - 26 tests across 6 test classes covering all behavior
- `orchestrator.py` - Added Stage 2b dedup block and post-send save_seen_urls call
- `.gitignore` - Added .seen_urls entry

## Decisions Made

- `save_seen_urls` called immediately after `send_email()` with no surrounding try/except — if send_email raises, the exception propagates naturally and save is skipped, preventing false-marking. This matches the plan's CRITICAL ordering constraint without requiring additional error handling.
- `SEEN_URLS_PATH` constructed from `os.path.dirname(os.path.dirname(__file__))` so the module resolves the project root correctly when imported from any working directory.
- `purge_old_entries` uses inclusive cutoff: entries dated exactly `window_days` ago are retained. An 8-day-old entry is purged; a 7-day-old entry is kept.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

- `pytest` not pre-installed in environment — installed via `pip install pytest` (Rule 3 auto-fix, no user action needed).

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Deduplication is live in the pipeline: articles seen in run N will not appear in run N+1
- `.seen_urls` file will be created on first successful pipeline run; `.gitignore` ensures it stays local
- Phase 2 Plan 02 (remaining polish items) can proceed immediately

## Self-Check: PASSED

- FOUND: pipeline/deduplicate.py
- FOUND: tests/test_deduplicate.py
- FOUND: tests/__init__.py
- FOUND: e5e48a4 (test: failing tests)
- FOUND: cde1000 (feat: deduplicate.py implementation)
- FOUND: f7e534e (feat: orchestrator + .gitignore)
