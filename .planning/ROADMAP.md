# Roadmap: Personal AI News Newsletter

## Overview

Four phases that build a working daily email digest from the ground up. Phase 1 proves the full pipeline end-to-end with simple RSS sources. Phase 2 adds the high-risk authenticated paywalled sources in isolation. Phase 3 applies the visual design, deduplication, and resilience details that make the tool trustworthy long-term. Phase 4 automates everything on GitHub Actions with proper scheduling, keepalive, and secrets management.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [ ] **Phase 1: Core Pipeline** - RSS ingestion, Claude summarization, basic HTML email, and Gmail delivery prove the end-to-end path works
- [ ] **Phase 2: Authenticated Sources** - WSJ and The Information added via cookie-based scraping, fully isolated from Phase 1
- [ ] **Phase 3: Polish and Resilience** - Wispr Flow design, deduplication, empty-section handling, Gmail compatibility, and dark mode
- [ ] **Phase 4: Automation** - GitHub Actions cron, workflow_dispatch, timeout, keepalive, and secrets management for fully hands-off daily delivery

## Phase Details

### Phase 1: Core Pipeline
**Goal**: Owner receives a working daily email with personal blog and Anthropic summaries — every source fetched, filtered, summarized by Claude, and delivered to Gmail
**Depends on**: Nothing (first phase)
**Requirements**: PIPE-01, PIPE-02, PIPE-03, PIPE-04, RSS-01, RSS-02, RSS-03, RSS-04, RSS-05, SUMM-01, SUMM-02, SUMM-03, SUMM-04, EMAIL-03, DEL-01, DEL-02, DEL-03, DEL-04
**Success Criteria** (what must be TRUE):
  1. Running the pipeline script produces an email in the owner's Gmail inbox containing summaries of posts from personal bloggers and Anthropic published in the last 24 hours
  2. Each digest item shows the article title, source name, publication date, direct URL, a 2-4 sentence summary, and a "Why it matters" section
  3. If a specific RSS feed is unavailable (e.g., network error), the pipeline completes and sends the email with that source omitted — no crash, a warning logged
  4. No article older than 24 hours appears in the email; each source section is capped at 5 items
  5. The email subject line includes the current date (e.g., "AI Briefing — March 1, 2026")
**Plans**: TBD

### Phase 2: Authenticated Sources
**Goal**: WSJ and The Information articles appear in the digest when cookies are valid; when cookies are expired or blocked, the email still sends with a clear notice to refresh them
**Depends on**: Phase 1
**Requirements**: PAY-01, PAY-02, PAY-03, PAY-04
**Success Criteria** (what must be TRUE):
  1. When valid subscriber cookies are present, up to 5 articles each from WSJ and The Information appear in the digest with full summaries
  2. When cookies return a 403 or login-page redirect, the email sends without those sections and includes a visible "WSJ unavailable — cookie refresh needed" notice in the email body
  3. Rotating cookies requires only updating a single environment variable or secret — no code changes
  4. The pipeline never passes login-page HTML to Claude for summarization
**Plans**: TBD

### Phase 3: Polish and Resilience
**Goal**: The email is visually polished, never duplicates articles seen in recent runs, suppresses empty sections, and renders correctly in Gmail including dark mode
**Depends on**: Phase 2
**Requirements**: PIPE-05, EMAIL-01, EMAIL-02, EMAIL-04, EMAIL-05, EMAIL-06
**Success Criteria** (what must be TRUE):
  1. An article that appeared in yesterday's digest does not appear again in today's digest
  2. A source section with no new content is silently suppressed — the email only shows sections with at least one article
  3. The email renders with the Wispr Flow-inspired visual design (clean, minimal, table-based layout) in Gmail desktop and Gmail Mobile without broken styles
  4. The total email HTML size stays under 102KB (Gmail clip threshold)
  5. On Apple Mail and Gmail Mobile, the email renders correctly in both light mode and dark mode via the prefers-color-scheme media query
**Plans**: TBD

### Phase 4: Automation
**Goal**: The pipeline runs automatically every morning at 7am ET via GitHub Actions, can be triggered manually for testing, times out if stuck, stays active indefinitely, and uses only GitHub Secrets for all credentials
**Depends on**: Phase 3
**Requirements**: INFRA-01, INFRA-02, INFRA-03, INFRA-04, INFRA-05
**Success Criteria** (what must be TRUE):
  1. The owner receives the email digest automatically each morning at 7-8am ET with no manual action required
  2. The workflow can be triggered manually via workflow_dispatch for testing without waiting for the cron schedule
  3. If the pipeline hangs or runs longer than expected, the GitHub Actions job terminates automatically at 30 minutes
  4. After 60+ days of no repository commits, the scheduled cron workflow is not disabled — the keepalive workflow prevents this
  5. No credentials (Gmail password, API keys, cookie strings) are hardcoded anywhere in the repository — all are read from GitHub Secrets at runtime
**Plans**: TBD

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2 → 3 → 4

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Core Pipeline | 0/TBD | Not started | - |
| 2. Authenticated Sources | 0/TBD | Not started | - |
| 3. Polish and Resilience | 0/TBD | Not started | - |
| 4. Automation | 0/TBD | Not started | - |
