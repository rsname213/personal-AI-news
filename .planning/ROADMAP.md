# Roadmap: Personal AI News Newsletter

## Overview

Three phases that build a working daily email digest from the ground up. Phase 1 proves the full pipeline end-to-end — all RSS sources (personal blogs, WSJ, The Information, Anthropic) fetched, summarized by Claude, and delivered to Gmail. Phase 2 applies the visual design, deduplication, and resilience details that make the tool trustworthy long-term. Phase 3 automates everything on GitHub Actions with proper scheduling, keepalive, and secrets management.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (1.1, 1.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [ ] **Phase 1: Core Pipeline** - All RSS sources fetched, Claude-summarized, and delivered to Gmail end-to-end
- [ ] **Phase 2: Polish and Resilience** - Wispr Flow design, deduplication, empty-section handling, Gmail compatibility, and dark mode
- [ ] **Phase 3: Automation** - GitHub Actions cron, workflow_dispatch, timeout, keepalive, and secrets management for fully hands-off daily delivery

## Phase Details

### Phase 1: Core Pipeline
**Goal**: Owner receives a working daily email with summaries from all sources — personal blogs, WSJ, The Information, and Anthropic — every source fetched via RSS, filtered, summarized by Claude, and delivered to Gmail
**Depends on**: Nothing (first phase)
**Requirements**: PIPE-01, PIPE-02, PIPE-03, PIPE-04, RSS-01, RSS-02, RSS-03, RSS-04, RSS-05, RSS-06, RSS-07, SUMM-01, SUMM-02, SUMM-03, SUMM-04, EMAIL-03, DEL-01, DEL-02, DEL-03, DEL-04
**Success Criteria** (what must be TRUE):
  1. Running the pipeline script produces an email in the owner's Gmail inbox with summaries from personal blogs, WSJ, The Information, and Anthropic published in the last 24 hours
  2. Each digest item shows the article title, source name, publication date, direct URL, a 2-4 sentence summary, and a "Why it matters" section
  3. If a specific RSS feed is unavailable (e.g., network error), the pipeline completes and sends the email with that source omitted — no crash, a warning logged
  4. No article older than 24 hours appears in the email; each source section is capped at 5 items
  5. The email subject line includes the current date (e.g., "AI Briefing — March 1, 2026")
**Plans**: TBD

### Phase 2: Polish and Resilience
**Goal**: The email is visually polished, never duplicates articles seen in recent runs, suppresses empty sections, and renders correctly in Gmail including dark mode
**Depends on**: Phase 1
**Requirements**: PIPE-05, EMAIL-01, EMAIL-02, EMAIL-04, EMAIL-05, EMAIL-06
**Success Criteria** (what must be TRUE):
  1. An article that appeared in yesterday's digest does not appear again in today's digest
  2. A source section with no new content is silently suppressed — the email only shows sections with at least one article
  3. The email renders with the Wispr Flow-inspired visual design (clean, minimal, table-based layout) in Gmail desktop and Gmail Mobile without broken styles
  4. The total email HTML size stays under 102KB (Gmail clip threshold)
  5. On Apple Mail and Gmail Mobile, the email renders correctly in both light mode and dark mode via the prefers-color-scheme media query
**Plans**: TBD

### Phase 3: Automation
**Goal**: The pipeline runs automatically every morning at 7am ET via GitHub Actions, can be triggered manually for testing, times out if stuck, stays active indefinitely, and uses only GitHub Secrets for all credentials
**Depends on**: Phase 2
**Requirements**: INFRA-01, INFRA-02, INFRA-03, INFRA-04, INFRA-05
**Success Criteria** (what must be TRUE):
  1. The owner receives the email digest automatically each morning at 7-8am ET with no manual action required
  2. The workflow can be triggered manually via workflow_dispatch for testing without waiting for the cron schedule
  3. If the pipeline hangs or runs longer than expected, the GitHub Actions job terminates automatically at 30 minutes
  4. After 60+ days of no repository commits, the scheduled cron workflow is not disabled — the keepalive workflow prevents this
  5. No credentials (Gmail password, API key) are hardcoded anywhere in the repository — all are read from GitHub Secrets at runtime
**Plans**: TBD

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2 → 3

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Core Pipeline | 0/TBD | Not started | - |
| 2. Polish and Resilience | 0/TBD | Not started | - |
| 3. Automation | 0/TBD | Not started | - |
