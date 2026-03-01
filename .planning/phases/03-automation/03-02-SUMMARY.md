---
phase: 03-automation
plan: 02
subsystem: infra
tags: [github-actions, keepalive, cron, automation, secrets]

# Dependency graph
requires:
  - phase: 03-automation
    provides: ".github/workflows/newsletter.yml — daily cron and workflow_dispatch for newsletter pipeline"
provides:
  - ".github/workflows/keepalive.yml — prevents 60-day inactivity cron disable via GitHub API (v2)"
  - "GitHub Secrets configured: ANTHROPIC_API_KEY, GMAIL_USER, GMAIL_APP_PASSWORD (human step)"
  - "End-to-end automation verified via manual workflow_dispatch (human step)"
affects:
  - "Phase 3 completion — all automation requirements INFRA-04 fulfilled"

# Tech tracking
tech-stack:
  added:
    - "gautamkrishnar/keepalive-workflow@v2 — GitHub API keepalive, no dummy commits"
  patterns:
    - "Keepalive cron offset by 1 hour from primary cron to avoid peak-load collision"
    - "actions: write only permission (not contents: write) sufficient for v2 keepalive"
    - "time_elapsed: 45 provides 15-day buffer before GitHub's 60-day disable policy"

key-files:
  created:
    - ".github/workflows/keepalive.yml"
  modified: []

key-decisions:
  - "gautamkrishnar/keepalive-workflow@v2 uses GitHub API to signal activity — no git history pollution"
  - "Keepalive cron at 13:00 UTC (1 hour after newsletter at 12:00) avoids Actions scheduler collision"
  - "time_elapsed: 45 triggers keepalive 15 days before GitHub's 60-day inactivity cutoff"
  - "Only permissions: actions: write needed — v2 does not write to repo contents"

patterns-established:
  - "Keepalive-offset pattern: schedule secondary maintenance workflows 1+ hour after primary workflows"

requirements-completed:
  - INFRA-04

# Metrics
duration: 5min
completed: 2026-03-01
---

# Phase 3 Plan 02: Keepalive Workflow and End-to-End Verification Summary

**Keepalive workflow using gautamkrishnar/keepalive-workflow@v2 (GitHub API, no dummy commits) prevents the daily newsletter cron from being silently disabled after 60 days of repo inactivity.**

## Performance

- **Duration:** ~5 min (Task 1 automated; Task 2 is human verification checkpoint)
- **Started:** 2026-03-01T20:16:59Z
- **Completed:** 2026-03-01
- **Tasks:** 2 of 2 complete (Task 1 automated; Task 2 human-verified and approved)
- **Files modified:** 1

## Accomplishments
- Created `.github/workflows/keepalive.yml` with correct permissions and schedule
- Keepalive uses GitHub API (v2) — no dummy commits, no repository history pollution
- Cron offset 1 hour from newsletter (13:00 vs 12:00 UTC) to avoid scheduler collision
- 15-day buffer (time_elapsed: 45) before GitHub's 60-day inactivity cutoff
- Human verification confirmed: manual workflow_dispatch delivered email to Gmail inbox, all Actions steps green, .seen_urls committed back with [skip ci] tag
- Phase 3 fully verified end-to-end — complete automation is live

## Task Commits

Each task was committed atomically:

1. **Task 1: Create .github/workflows/keepalive.yml** - `6bd11b9` (feat)
2. **Task 2: Verify end-to-end automation via workflow_dispatch** - APPROVED (human verified: email received, all Actions steps green)

**Plan metadata:** See final commit below.

## Files Created/Modified
- `.github/workflows/keepalive.yml` — Keepalive workflow using gautamkrishnar/keepalive-workflow@v2, cron at 13:00 UTC, actions: write permission only

## Decisions Made
- Used v2 of keepalive-workflow (not v1): v2 uses the GitHub API to signal activity rather than making dummy commits that pollute git history
- Set time_elapsed: 45 (not 60) to create a 15-day safety buffer before GitHub disables the cron
- Cron at 13:00 UTC placed 1 hour after the newsletter cron (12:00 UTC) to reduce likelihood of both hitting Actions scheduler peak load simultaneously
- Only permissions: actions: write granted — v2 does not require contents: write

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] PyYAML parses 'on' key as Python boolean True**
- **Found during:** Task 1 (keepalive.yml verification)
- **Issue:** The verification script in the plan used `data['on']` but PyYAML 1.1 parses bare `on` as Python boolean `True`, causing a KeyError
- **Fix:** Ran verification with corrected key `data[True]` — the YAML file itself is correct and GitHub Actions parses it properly; the plan's verification script had a Python-side quirk
- **Files modified:** None (the keepalive.yml file is correct; only the inline verification command was adjusted)
- **Verification:** All 6 assertions pass with corrected key access
- **Committed in:** 6bd11b9 (Task 1 commit)

---

**Total deviations:** 1 auto-noted (PyYAML 'on' key quirk in verification script — file content is correct)
**Impact on plan:** Zero impact on delivered files. The keepalive.yml is valid YAML and GitHub Actions parses it correctly.

## Issues Encountered
- PyYAML (used by the verification script) parses bare `on` as Python boolean `True` per YAML 1.1 spec. This is a known Python PyYAML quirk, not a file content issue. GitHub Actions uses its own YAML parser which handles `on` correctly.

## User Setup Required

**External services require manual configuration before Task 2 (the human verification checkpoint):**

Go to: GitHub repo page -> Settings -> Secrets and variables -> Actions -> New repository secret

| Secret Name | Value Source |
|-------------|-------------|
| `ANTHROPIC_API_KEY` | https://console.anthropic.com/settings/keys |
| `GMAIL_USER` | Your Gmail address (same as GMAIL_USER in your .env file) |
| `GMAIL_APP_PASSWORD` | Google Account -> Security -> 2-Step Verification -> App Passwords |

Secret names are case-sensitive and must match exactly.

## Next Phase Readiness

Phase 3 is the final phase. The pipeline is fully operational and verified:
- Daily cron at 12:00 UTC delivers email automatically each morning (no manual action required)
- workflow_dispatch available for on-demand testing
- keepalive.yml prevents silent cron disable after 60 days of no commits
- .seen_urls deduplication committed back after each run with [skip ci] guard — no infinite loop
- No credentials hardcoded anywhere — all secrets via GitHub Secrets

No further phases planned. Ongoing maintenance to monitor: Paul Graham unofficial RSS feed (Olshansk/pgessays-rss may go stale — paulgraham.com/articles.html scraper is the fallback). Cookie-based scraping for WSJ/The Information may face IP blocking from GitHub datacenter ranges (medium confidence risk logged in STATE.md).

---
*Phase: 03-automation*
*Completed: 2026-03-01*
