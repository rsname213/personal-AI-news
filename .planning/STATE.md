# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-03-01)

**Core value:** Every morning, a single curated briefing of what matters in AI and tech — already summarized, zero manual effort.
**Current focus:** Phase 1 - Core Pipeline

## Current Position

Phase: 1 of 4 (Core Pipeline)
Plan: 4 of 5 in current phase
Status: In progress
Last activity: 2026-03-01 — Completed plan 01-04 (Jinja2 email template, render_email(), send_email() via Gmail SMTP_SSL)

Progress: [███░░░░░░░] 20%

## Performance Metrics

**Velocity:**
- Total plans completed: 4
- Average duration: ~2 min
- Total execution time: 0.13 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 01-core-pipeline | 4 | ~8 min | ~2 min |

**Recent Trend:**
- Last 5 plans: 01-01 (2 min), 01-02 (skipped/wave-1), 01-03 (2 min), 01-04 (2 min)
- Trend: consistent ~2 min/plan

*Updated after each plan completion*

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- [Init]: GitHub Actions only — no persistent server; stateless execution per run
- [Init]: Gmail App Password (not OAuth) — simpler, sufficient for single-user self-send
- [Init]: Claude Haiku via Batch API for summarization — cost-predictable (~$0.05/day)
- [Init]: Cookie-based scraping for WSJ/The Information — user has subscriptions; isolated to Phase 2
- [01-01]: Three-stage inheritance chain (RawArticle -> FilteredArticle -> SummarizedArticle) for typed, no-duplication pipeline contracts
- [01-01]: SummarizedArticle defaults (summary="", summarization_failed=False) allow graceful render on API failure
- [01-01]: source_category constrained to exactly 4 strings matching email template section headers
- [01-03]: Sequential client.messages.create() chosen over Batch API — Batch API can take up to 1 hour, incompatible with 30-min GitHub Actions timeout
- [01-03]: 25-hour recency window (not 24h) absorbs GitHub Actions cron scheduling delays without silently dropping recent articles
- [01-03]: System prompt uses cache_control: ephemeral — ~90% cost reduction on repeat calls within same run
- [01-03]: ANTHROPIC_API_KEY read at call time, not module import — allows module import in tests without real key
- [01-04]: SMTP_SSL port 465 over STARTTLS/587 — simpler, no explicit starttls() call, sufficient for Gmail App Password
- [01-04]: GMAIL_USER and GMAIL_APP_PASSWORD read at send_email() call time, not module import — allows import without env vars
- [01-04]: SECTION_ORDER constant in render.py controls section sequence (Personal Blogs, WSJ, The Information, Anthropic)
- [01-02]: Gwern scraper uses <a id="YYYY-MM-DD"> attributes for precise date parsing — verified against live gwern.net/blog/index HTML (not year-only approximation as plan skeleton suggested)
- [01-02]: Anthropic scraper fallback parses date strings ("Feb 27, 2026" regex) from anthropic.com/news card text — enables proper 25h recency filtering
- [01-02]: FEED_URLS dict (20 sources) is the single place to fix broken feed URLs — no code logic changes needed

### Pending Todos

None yet.

### Blockers/Concerns

- [Phase 2 risk]: Cookie-based scraping from GitHub Actions IP ranges is MEDIUM confidence — GitHub datacenter IPs may be blocked by WSJ/The Information anti-bot systems. Playwright stealth fallback planned but unvalidated. Test against live site as first Phase 2 implementation step.
- [Ongoing maintenance]: Paul Graham unofficial RSS feed (Olshansk/pgessays-rss) is itself a scraper that may go stale. Custom HTML scraper of paulgraham.com/articles.html is the fallback.

## Session Continuity

Last session: 2026-03-01T18:51:44Z
Stopped at: Completed 01-02-PLAN.md (backfill) — fetchers/rss.py (20-source FEED_URLS), fetchers/paul_graham.py, fetchers/gwern.py, fetchers/anthropic_blog.py
Resume file: None
