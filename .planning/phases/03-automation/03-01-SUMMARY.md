---
phase: 03-automation
plan: 01
subsystem: infra
tags: [github-actions, yaml, cron, workflow_dispatch, git-auto-commit, rss, env-vars]

# Dependency graph
requires:
  - phase: 02-polish-and-resilience
    provides: pipeline/deduplicate.py with save_seen_urls() called after send_email() success
provides:
  - .github/workflows/newsletter.yml — complete GitHub Actions workflow (cron + dispatch + timeout + secrets + .seen_urls commit-back)
  - fetchers/rss.py — WSJ and The Information URLs read from env vars with hardcoded fallbacks
  - .gitignore — .seen_urls no longer ignored, enabling git-auto-commit-action tracking
affects: [03-02, 03-03, any phase using GitHub Actions or RSS fetcher config]

# Tech tracking
tech-stack:
  added: [stefanzweifel/git-auto-commit-action@v7, actions/checkout@v4, actions/setup-python@v5]
  patterns: [step-level-secrets, env-var-rss-urls, skip-ci-commit, file-pattern-restricted-commit]

key-files:
  created:
    - .github/workflows/newsletter.yml
  modified:
    - fetchers/rss.py
    - .gitignore

key-decisions:
  - "Secrets (ANTHROPIC_API_KEY, GMAIL_USER, GMAIL_APP_PASSWORD) mapped at step level only — not job level — to prevent secret exposure to third-party actions"
  - "WSJ_RSS_URL and THE_INFO_RSS_URL set as plain env vars in the workflow env: block; fetchers/rss.py reads via os.environ.get() with original URLs as fallback"
  - ".seen_urls removed from .gitignore so stefanzweifel/git-auto-commit-action@v7 can commit deduplication state back to repo after each run"
  - "commit_message: 'chore: update seen URLs [skip ci]' prevents .seen_urls commit from re-triggering the workflow (avoids infinite loop)"
  - "No push: trigger in on: block — only schedule: and workflow_dispatch: to prevent double-send from .seen_urls commit-back"
  - "file_pattern: '.seen_urls' in git-auto-commit step restricts commits to deduplication state only — never accidentally commits .env or other files"

patterns-established:
  - "Step-level env: blocks for secrets (not job-level) to minimize secret exposure surface"
  - "RSS feed URLs as env vars in workflow, read in Python via os.environ.get() with hardcoded fallback — keeps Python source credential-free without breaking local runs"
  - "[skip ci] on auto-commit messages to prevent recursive workflow triggers"

requirements-completed: [INFRA-01, INFRA-02, INFRA-03, INFRA-05]

# Metrics
duration: 21min
completed: 2026-03-01
---

# Phase 3 Plan 1: GitHub Actions Newsletter Workflow Summary

**GitHub Actions workflow with daily cron at 12:00 UTC, 30-min timeout, step-level secrets, and git-auto-commit for .seen_urls persistence — plus RSS URL migration to env vars**

## Performance

- **Duration:** 21 min
- **Started:** 2026-03-01T19:49:26Z
- **Completed:** 2026-03-01T20:11:10Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments
- Created `.github/workflows/newsletter.yml` — the core automation artifact: daily schedule + manual dispatch, 30-min kill timeout, step-level secrets mapping, WSJ/The Information as plain env vars, and stefanzweifel/git-auto-commit-action@v7 to persist .seen_urls after each successful run
- Migrated WSJ and The Information RSS URLs from hardcoded Python strings to `os.environ.get()` with fallbacks — satisfies INFRA-05 without breaking local runs
- Removed `.seen_urls` from `.gitignore` — required so the git-auto-commit-action can track and commit the deduplication state file between workflow runs

## Task Commits

Each task was committed atomically:

1. **Task 1: Remove .seen_urls from .gitignore and migrate RSS URLs to env vars** - `8d065c9` (feat)
2. **Task 2: Create .github/workflows/newsletter.yml** - `9d4aedb` (feat)

**Plan metadata:** `(docs commit follows)`

## Files Created/Modified
- `.github/workflows/newsletter.yml` — Main newsletter workflow: cron `0 12 * * *`, `workflow_dispatch`, `timeout-minutes: 30`, `permissions: contents: write`, step-level secrets, RSS URL env vars, git-auto-commit with `[skip ci]` and `file_pattern: .seen_urls`
- `fetchers/rss.py` — Added `import os`; WSJ and The Information entries now use `os.environ.get("WSJ_RSS_URL", ...)` and `os.environ.get("THE_INFO_RSS_URL", ...)`
- `.gitignore` — Removed the `.seen_urls` entry and its comment block (2 lines removed)

## Decisions Made
- Secrets mapped at step level only (not job level) to prevent secret exposure to `git-auto-commit-action` — a third-party action that doesn't need API keys
- `[skip ci]` in the commit message prevents the `.seen_urls` update commit from triggering another newsletter run (no infinite send loop)
- `file_pattern: '.seen_urls'` restricts the auto-commit to deduplication state only — `.env` or other modified files are never accidentally committed
- No `push:` trigger added to the workflow — combined with the `.seen_urls` commit-back, a push trigger would cause infinite loop (commit -> run -> commit -> run...)

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
- PyYAML parses `on:` as boolean `True` (standard YAML spec behavior). The newsletter.yml content is correct for GitHub Actions; the verification script was adjusted to use `data[True]` as the key. No file changes required.

## User Setup Required

**External secrets require manual configuration in GitHub before the workflow can run:**

1. Go to repository Settings > Secrets and variables > Actions
2. Add these repository secrets:
   - `ANTHROPIC_API_KEY` — Claude API key (from console.anthropic.com)
   - `GMAIL_USER` — Gmail address (e.g. you@gmail.com)
   - `GMAIL_APP_PASSWORD` — Gmail App Password (16-char, from Google Account > Security > App Passwords)
3. Verification: Go to Actions tab, click "Run workflow" on "AI Newsletter" — job should start and complete within 30 minutes

## Next Phase Readiness
- Core automation is complete: push this branch to GitHub, add three secrets, and the newsletter will run every morning at 7am EST
- INFRA-01 (cron trigger), INFRA-02 (workflow_dispatch), INFRA-03 (30-min timeout), INFRA-05 (env var RSS URLs) all satisfied
- `.seen_urls` deduplication state will persist across runs via git-auto-commit-action
- Remaining phase 3 plans can build on this workflow foundation (e.g., failure notifications, scraper jobs)

---
*Phase: 03-automation*
*Completed: 2026-03-01*

## Self-Check: PASSED

- FOUND: .github/workflows/newsletter.yml
- FOUND: fetchers/rss.py
- FOUND: 03-01-SUMMARY.md
- FOUND: commit 8d065c9 (Task 1)
- FOUND: commit 9d4aedb (Task 2)
