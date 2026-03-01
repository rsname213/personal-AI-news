---
phase: 01-core-pipeline
plan: "03"
subsystem: pipeline
tags: [anthropic, claude-haiku, prompt-caching, filtering, summarization]

# Dependency graph
requires:
  - phase: 01-01
    provides: RawArticle, FilteredArticle, SummarizedArticle dataclass definitions in models.py

provides:
  - Recency + per-source-cap filter (pipeline/filter.py, filter_articles function)
  - Sequential Claude Haiku summarizer with prompt caching (pipeline/summarize.py, summarize_articles function)
  - RawArticle[] -> FilteredArticle[] -> SummarizedArticle[] typed transformation pipeline

affects:
  - 01-04 (email renderer needs SummarizedArticle list)
  - 01-05 (main orchestrator calls filter_articles then summarize_articles)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Sequential API calls (not Batch API) for synchronous GitHub Actions compatibility"
    - "Prompt caching via cache_control ephemeral on system prompt — ~90% cost savings after first call"
    - "API key read at call time (os.environ['ANTHROPIC_API_KEY']) not module load time — import without key"
    - "Never-raise summarization — all exceptions caught; summarization_failed=True preserves article"

key-files:
  created:
    - pipeline/filter.py
    - pipeline/summarize.py
  modified: []

key-decisions:
  - "Sequential client.messages.create() chosen over Batch API — Batch API can take up to 1 hour, incompatible with 30-min GitHub Actions timeout"
  - "25-hour recency window (not 24h) absorbs GitHub Actions cron scheduling delays without silently dropping recent articles"
  - "ANTHROPIC_API_KEY read inside summarize_articles() body, not at module import — allows tests to import module without API key"
  - "System prompt marked cache_control: ephemeral — 5-min cache provides ~90% cost reduction on repeat calls in same run"

patterns-established:
  - "Filter-before-summarize pattern: recency + cap filter reduces API cost by excluding stale/excess articles"
  - "Graceful degradation: summarization_failed=True preserves title/URL on API failure so renderer can still include the article"

requirements-completed: [PIPE-02, PIPE-03, SUMM-01, SUMM-02, SUMM-03, SUMM-04]

# Metrics
duration: 2min
completed: 2026-03-01
---

# Phase 1 Plan 03: Filter and Summarizer Summary

**25-hour recency filter with 5-item per-source cap + sequential Claude Haiku summarizer using prompt caching for ~90% cost savings**

## Performance

- **Duration:** ~2 min
- **Started:** 2026-03-01T18:48:23Z
- **Completed:** 2026-03-01T18:49:51Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments

- Implemented `filter_articles()` — filters RawArticle list to recent articles (25h window) and caps at 5 per source, returning sorted FilteredArticle list
- Implemented `summarize_articles()` — sequentially calls Claude Haiku via `client.messages.create()` with `cache_control: ephemeral` on the system prompt, never raises, returns SummarizedArticle per input article
- Both modules verified: import cleanly, handle edge cases (empty list, API failure), and produce correct typed outputs

## Task Commits

Each task was committed atomically:

1. **Task 1: Create pipeline/filter.py** - `fe7bc92` (feat)
2. **Task 2: Create pipeline/summarize.py** - `307a12c` (feat)

## Files Created/Modified

- `pipeline/filter.py` - 25-hour recency filter with 5-item per-source cap; pure stdlib; exports `filter_articles`
- `pipeline/summarize.py` - Sequential Claude Haiku summarizer with prompt caching; graceful failure handling; exports `summarize_articles`

## Decisions Made

- Sequential `client.messages.create()` over Batch API: Batch API is async (up to 1 hour) — incompatible with 30-minute GitHub Actions timeout. Sequential calls + prompt caching achieve ~90% cost savings.
- 25-hour window (not 24h): Absorbs GitHub Actions cron jitter without silently dropping recent articles.
- API key at call time: `os.environ["ANTHROPIC_API_KEY"]` read inside `summarize_articles()` body, not at module level — allows importing the module in tests without a real key.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required at this stage. `ANTHROPIC_API_KEY` is consumed at runtime and will be configured as a GitHub Actions secret in Phase 1 plan 05.

## Next Phase Readiness

- `filter_articles(RawArticle[]) -> FilteredArticle[]` ready for orchestrator
- `summarize_articles(FilteredArticle[]) -> SummarizedArticle[]` ready for orchestrator
- Plan 04 (email renderer) can now depend on `SummarizedArticle` list as input
- Plan 05 (main pipeline orchestrator) can wire all stages together

---
*Phase: 01-core-pipeline*
*Completed: 2026-03-01*
