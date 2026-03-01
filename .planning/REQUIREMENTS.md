# Requirements: Personal AI News Newsletter

**Defined:** 2026-03-01
**Core Value:** Every morning, a single curated briefing of what matters in AI and tech — already summarized, zero manual effort.

## v1 Requirements

### Pipeline

- [ ] **PIPE-01**: System fetches content from all sources once per day and produces a single email output
- [ ] **PIPE-02**: System filters out any content older than 24 hours from time of run
- [ ] **PIPE-03**: System caps output at 5 items per source section to keep email scannable
- [ ] **PIPE-04**: System degrades gracefully per source — a failed source produces an empty section, never blocks the email
- [ ] **PIPE-05**: System deduplicates content so the same article never appears twice across consecutive runs

### Sources — RSS Feeds

- [ ] **RSS-01**: System fetches new posts from all 20 personal bloggers via RSS/Atom feeds
- [ ] **RSS-02**: System handles Paul Graham's broken official RSS via a community-maintained feed or custom HTML scraper
- [ ] **RSS-03**: System handles Gwern Branwen's missing RSS via a custom HTML scraper
- [ ] **RSS-04**: System fetches new posts from Anthropic's official news/blog channel
- [ ] **RSS-05**: System logs a warning per source when a feed is unavailable, without crashing

### Sources — Authenticated Paywalled

- [ ] **PAY-01**: System fetches top articles from WSJ using subscriber cookies stored in GitHub Secrets
- [ ] **PAY-02**: System fetches top articles from The Information using subscriber cookies stored in GitHub Secrets
- [ ] **PAY-03**: System detects expired/invalid cookies (403 response) and logs a clear warning, falling back to empty section
- [ ] **PAY-04**: Subscriber cookie strings can be rotated by updating a single GitHub Secret (no code changes required)

### Summarization

- [ ] **SUMM-01**: System generates a 2-4 sentence summary for each article using Claude Haiku via the Batch API
- [ ] **SUMM-02**: Every summary includes a distinct "Why it matters" section (1-2 sentences) explaining the non-obvious significance
- [ ] **SUMM-03**: Each digest item includes the article title, publication date, source name, and direct URL
- [ ] **SUMM-04**: System handles Claude API failures gracefully (include article title + URL without summary, do not crash)

### Email — Rendering

- [ ] **EMAIL-01**: Email renders correctly in Gmail (inline CSS, table-based layout, no unsupported CSS properties)
- [ ] **EMAIL-02**: Email is visually designed based on Wispr Flow's aesthetic (wisprflow.ai) — clean, minimal, modern
- [ ] **EMAIL-03**: Email has clear section headers per source category (Personal Blogs, WSJ, The Information, Anthropic)
- [ ] **EMAIL-04**: Email total size stays under 102KB to prevent Gmail clipping
- [ ] **EMAIL-05**: Email supports dark mode on Apple Mail and Gmail Mobile via `@media (prefers-color-scheme: dark)`
- [ ] **EMAIL-06**: If all sources in a section return no new content, that section is suppressed (not shown as empty)

### Email — Delivery

- [ ] **DEL-01**: Email is sent via Gmail SMTP using an App Password stored in GitHub Secrets
- [ ] **DEL-02**: Email is addressed to and from the same Gmail account (self-send)
- [ ] **DEL-03**: Email subject line includes the current date (e.g., "AI Briefing — March 1, 2026")
- [ ] **DEL-04**: System logs a clear error when Gmail SMTP sending fails

### Infrastructure

- [ ] **INFRA-01**: Full pipeline runs automatically via GitHub Actions on a daily cron at 12:00 UTC (7am EST / 8am EDT)
- [ ] **INFRA-02**: Pipeline can be triggered manually via `workflow_dispatch` for testing without waiting for cron
- [ ] **INFRA-03**: GitHub Actions workflow includes a 30-minute timeout to prevent runaway jobs
- [ ] **INFRA-04**: A GitHub Actions keepalive workflow prevents the cron from being disabled after 60 days of repo inactivity
- [ ] **INFRA-05**: All secrets (GMAIL_USER, GMAIL_APP_PASSWORD, WSJ_COOKIES, THE_INFO_COOKIES, ANTHROPIC_API_KEY) are stored as GitHub Secrets, never hardcoded

## v2 Requirements

### Enhanced Sourcing

- **SRC-01**: Fetch from Twitter/X accounts of curated follows (requires API access)
- **SRC-02**: Support Reddit aggregation from specified subreddits (r/MachineLearning, r/artificial)
- **SRC-03**: YouTube channel monitoring for new AI-related video uploads

### Delivery Enhancements

- **DEL-05**: Web archive version of each email (hosted on GitHub Pages)
- **DEL-06**: Pushover or Slack notification if email send fails
- **DEL-07**: Weekly digest variant (summary of the week's most-linked articles)

### Intelligence

- **INT-01**: Cross-article theme detection ("3 articles this week touched on model alignment")
- **INT-02**: Article importance scoring to prioritize top 5 when more than 5 are available
- **INT-03**: Reading time estimates per article summary

## Out of Scope

| Feature | Reason |
|---------|--------|
| Multi-recipient email list | Personal tool — not a newsletter platform |
| Subscription management UI | No end-users other than the owner |
| Database for article storage | Stateless per-run is sufficient; deduplication via URL hash file |
| OAuth 2.0 for Gmail | App Password is sufficient for single-user self-send |
| Mobile app | Email is the delivery mechanism |
| Real-time alerts | Daily cadence is intentional — not a news ticker |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| PIPE-01 | Phase 1 | Pending |
| PIPE-02 | Phase 1 | Pending |
| PIPE-03 | Phase 1 | Pending |
| PIPE-04 | Phase 1 | Pending |
| PIPE-05 | Phase 3 | Pending |
| RSS-01 | Phase 1 | Pending |
| RSS-02 | Phase 1 | Pending |
| RSS-03 | Phase 1 | Pending |
| RSS-04 | Phase 1 | Pending |
| RSS-05 | Phase 1 | Pending |
| PAY-01 | Phase 2 | Pending |
| PAY-02 | Phase 2 | Pending |
| PAY-03 | Phase 2 | Pending |
| PAY-04 | Phase 2 | Pending |
| SUMM-01 | Phase 1 | Pending |
| SUMM-02 | Phase 1 | Pending |
| SUMM-03 | Phase 1 | Pending |
| SUMM-04 | Phase 1 | Pending |
| EMAIL-01 | Phase 3 | Pending |
| EMAIL-02 | Phase 3 | Pending |
| EMAIL-03 | Phase 1 | Pending |
| EMAIL-04 | Phase 3 | Pending |
| EMAIL-05 | Phase 3 | Pending |
| EMAIL-06 | Phase 3 | Pending |
| DEL-01 | Phase 1 | Pending |
| DEL-02 | Phase 1 | Pending |
| DEL-03 | Phase 1 | Pending |
| DEL-04 | Phase 1 | Pending |
| INFRA-01 | Phase 4 | Pending |
| INFRA-02 | Phase 4 | Pending |
| INFRA-03 | Phase 4 | Pending |
| INFRA-04 | Phase 4 | Pending |
| INFRA-05 | Phase 4 | Pending |

**Coverage:**
- v1 requirements: 34 total
- Mapped to phases: 34
- Unmapped: 0

---
*Requirements defined: 2026-03-01*
*Last updated: 2026-03-01 after roadmap creation (EMAIL-06 moved from Phase 1 to Phase 3)*
