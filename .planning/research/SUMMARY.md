# Project Research Summary

**Project:** Personal AI News Newsletter
**Domain:** Personal automated daily digest — RSS/scraping pipeline to email
**Researched:** 2026-03-01
**Confidence:** MEDIUM-HIGH

## Executive Summary

This is a stateless, single-run daily automation pipeline: fetch articles from 20+ personal blogs plus two paywalled sources (WSJ, The Information), filter to the past 24 hours, summarize with Claude AI, render an HTML email, and deliver via Gmail SMTP. The project runs entirely on GitHub Actions (free tier), uses Python 3.12 as its only runtime, and has no persistent server or database. The recommended approach follows a strict linear pipeline — fetch, filter, summarize, render, send — with graceful per-source degradation so a broken feed never blocks the email from going out. Total runtime cost is approximately $0.05/day in API fees; GitHub Actions minutes are negligible.

The most important architectural decision is sourcing strategy: the 20+ personal blog sources are straightforward RSS via feedparser, but two specific sources (Paul Graham and Gwern) have broken or non-existent feeds that require custom scrapers from day one. The paywalled sources (WSJ, The Information) require cookie-based authenticated HTTP requests stored as GitHub Secrets, with an explicit fallback for when cookies expire or anti-bot systems block datacenter IP ranges. These authenticated sources are the highest-maintenance component of the system and must degrade gracefully — detecting paywall redirects and logging clear warnings rather than summarizing login pages.

The main risk cluster is reliability over time: GitHub Actions cron silently stops after 60 days of repo inactivity, cookies for WSJ/The Information expire every 30–90 days, and RSS feeds silently go stale. All three risks are solvable at build time — a Keepalive workflow, cookie health checks on every run, and per-source article count monitoring. If these are built into Phase 1 and Phase 2, the system will self-report problems rather than silently degrade. The AI summarization component (Claude Haiku via the Batch API) is low risk: well-documented, cost-predictable, and straightforwardly integrated.

## Key Findings

### Recommended Stack

The stack is entirely Python with zero optional runtimes (no Node.js, no separate database server). All components are well-established libraries with verified recent releases. The heavy-lift choices — feedparser for RSS normalization, httpx for cookie-authenticated HTTP, Playwright as a fallback for JS-rendered paywalls, BeautifulSoup4/lxml for HTML parsing, Anthropic SDK for Claude, Jinja2+premailer for HTML email, and smtplib for delivery — are the correct tools for each job with strong ecosystem support. Sync/sequential execution is sufficient; no async framework is needed given the single-daily-run, low-concurrency nature of the pipeline.

**Core technologies:**
- `feedparser 6.0.12`: RSS/Atom parsing — normalizes 20+ different feed formats automatically; handles malformed feeds from personal blogs
- `httpx 0.28.1`: Authenticated HTTP for paywalled sources — modern requests successor with clean cookie injection
- `playwright 1.58.0`: Browser fallback for JS-gated paywall content — only if httpx cookie approach fails
- `beautifulsoup4 4.14.3` + `lxml`: HTML content extraction — standard, dual-purpose with premailer
- `anthropic 0.84.0` + `claude-haiku-4-5-20251001`: AI summarization — cheapest capable model; Batch API for efficiency
- `Jinja2 3.1.6` + `premailer 3.10.0`: HTML email rendering — template engine with automatic CSS inlining for Gmail compatibility
- `smtplib` (stdlib): Email delivery — zero dependencies; Gmail App Password + port 465 SSL

See `/workspaces/personal-AI-news/.planning/research/STACK.md` for full requirements.txt, code patterns, and alternatives considered.

### Expected Features

**Must have (table stakes):**
- RSS ingestion for 20+ personal blogs via feedparser
- 24-hour freshness filter (UTC-aware, 25-hour window to absorb Actions scheduling variance)
- Per-source 5-item cap applied before AI calls to control cost and email length
- AI summarization with "why it matters" framing — the core value proposition
- Section-grouped HTML email (blogs / paywalled sources / Anthropic), rendered under 102KB
- Gmail SMTP delivery via App Password
- GitHub Actions cron scheduling at 12:00 UTC (7am EST / 8am EDT — acceptable per spec)
- Graceful per-source failure: failed source returns empty list, never aborts the run
- `workflow_dispatch` trigger for manual testing

**Should have (differentiators):**
- Structured "why it matters" framing per article (not just headline summary)
- Per-blogger attribution in each section header
- Fallback chain for broken/missing feeds (Paul Graham, Gwern) — required from Phase 1 or these sources simply never work
- "Quiet day" handling: suppress empty sections, include footer "X of Y sources active today"
- Cookie health check: detect paywall redirects, log loud warning, include "WSJ unavailable — cookie refresh needed" in email
- Wispr Flow-inspired minimal visual design with inline CSS
- Keepalive workflow to prevent GitHub disabling the cron after 60 days of inactivity
- Deduplication store (committed JSON file) to prevent repeated articles across runs

**Defer (v2+):**
- Everything in the anti-features list: multi-recipient subscription, persistent database, read/click tracking, Twitter/X ingestion, ML relevance scoring, automatic source discovery

See `/workspaces/personal-AI-news/.planning/research/FEATURES.md` for source-specific complexity notes and legal analysis of authenticated scraping.

### Architecture Approach

The architecture is a stateless linear pipeline: fetch (parallel per source) → filter (24h + cap) → summarize (Claude Batch API) → render (Jinja2 + premailer) → send (smtplib). Each stage produces a typed output consumed by the next. The key patterns are source isolation with fail-soft collection (each fetcher returns `List[RawArticle]` or empty list, never raises), typed dataclasses for inter-stage data (`RawArticle` → `FilteredArticle` → `SummarizedArticle`), Batch-then-Map for Claude (submit all articles in one batch call, poll for completion, map results by `custom_id`), and cookie string injection via environment variable for authenticated sources. The Jinja2 template uses table-based layout with premailer-inlined CSS to survive Gmail's aggressive style stripping.

**Major components:**
1. `orchestrator.py` — entry point; drives all stages, collects partial results, handles top-level failures
2. `fetchers/` (rss.py, wsj.py, theinfo.py, anthropic_blog.py) — independent source fetchers returning typed article lists
3. `pipeline/filter.py` — 24-hour recency filter + 5-item-per-source cap; pure Python, no external deps
4. `pipeline/summarize.py` — Claude Batch API submission and polling; maps results back via custom_id
5. `pipeline/render.py` — Jinja2 template rendering + premailer CSS inlining
6. `pipeline/send.py` — smtplib Gmail SMTP delivery
7. `models.py` — shared dataclasses imported by all modules
8. `templates/digest.html.j2` — single email template with table layout + dark mode media query

See `/workspaces/personal-AI-news/.planning/research/ARCHITECTURE.md` for full file structure, code patterns, build order, and anti-patterns.

### Critical Pitfalls

1. **RSS feeds silently go dead (Paul Graham, Gwern, others)** — Build per-source article count logging from day one; treat zero articles from a known-active source as a warning, not success. Paul Graham's official feed broke in Oct 2023 and requires an unofficial scraper or community RSS proxy. Gwern has no native RSS. These are Phase 1 blockers.

2. **Paywalled source scraping breaks silently** — Cookie-based WSJ/The Information scraping can return a login-page HTML that looks like article content. Detect this explicitly by checking for login form indicators, redirect URLs, or sub-500-character response bodies. Return empty list + loud warning on failure. Never pass login pages to Claude for summarization.

3. **GitHub Actions cron silently disabled after 60 days of inactivity** — A personal automation repo with no commits will have its scheduled workflow disabled by GitHub. Install a Keepalive workflow at project initialization, before the repo enters maintenance mode.

4. **Gmail CSS stripping collapses email layout** — Gmail strips `<head>` style blocks, flexbox sub-properties, grid, external stylesheets, and any style block with a single invalid property. Use table-based layout with inline CSS only. Apply premailer to automate inlining. Keep total HTML under 102KB.

5. **Workflow "succeeds" but email never arrives** — SMTP acceptance is not delivery. Wrap SMTP send in explicit try/except, log the SMTP response code, and design the failure case to exit with code 1 so the Actions run turns red.

See `/workspaces/personal-AI-news/.planning/research/PITFALLS.md` for 12 documented pitfalls with phase-specific warnings.

## Implications for Roadmap

The architecture research prescribes a clear build order based on dependencies: data models before anything else, delivery proof before content sources, simple RSS before authenticated scraping, summarization before rendering. The pitfalls research reinforces this order by identifying which problems must be solved early (feed health monitoring, deduplication, keepalive) versus which can be deferred (visual polish, empty-section handling). The features research confirms a clean Phase 1 / Phase 2 / Phase 3 structure.

### Phase 1: Foundation and Core RSS Pipeline

**Rationale:** Build the end-to-end email path with simple content first to prove delivery works before adding complexity. Feedparser, filter, basic template, and Gmail SMTP are low-risk, well-documented components. Must also solve two immediate blockers: the Paul Graham/Gwern feed problem and the GitHub cron keepalive issue.

**Delivers:** A working daily email containing personal blog summaries and Anthropic updates, delivered to the owner's inbox automatically each morning.

**Addresses features:**
- RSS ingestion (feedparser, all standard feeds)
- 24-hour freshness filter with 25-hour window
- Per-source 5-item cap
- Claude Haiku summarization with "why it matters" framing (Batch API)
- Basic HTML email (Jinja2 + premailer + table layout)
- Gmail SMTP delivery (port 465 SSL)
- GitHub Actions cron + workflow_dispatch
- Keepalive workflow (anti-cron-disable)
- Per-source article count logging (feed health monitoring)
- Custom scraper for Paul Graham (unofficial feed or HTML scrape)
- Custom scraper for Gwern (HTML scrape)
- UTC-aware date parsing with 25-hour window

**Avoids pitfalls:** Pitfall 1 (silent feed death), Pitfall 3 (cron disabled after inactivity), Pitfall 6 (timezone/DST bugs), Pitfall 10 (off-by-one date filtering).

### Phase 2: Authenticated Paywalled Sources

**Rationale:** WSJ and The Information require a completely different fetching pattern (cookie-based authenticated HTTP) and are the highest-risk component. Isolate them in their own phase so Phase 1 delivery is already proven before adding this complexity. Building paywall detection is non-negotiable before this phase ships.

**Delivers:** Full article content from WSJ and The Information included in the digest, when cookies are valid. When cookies are expired or blocked, the email still goes out with a clear notice to refresh cookies.

**Addresses features:**
- WSJ authenticated scraping (httpx cookie injection)
- The Information authenticated scraping (same pattern)
- Cookie health check: detect login redirects, <500-char responses, form presence
- "Source unavailable — cookie refresh needed" section in email
- GitHub Secrets for WSJ_COOKIES and THE_INFORMATION_COOKIES

**Uses:** httpx 0.28.1, Playwright 1.58.0 (fallback), GitHub Secrets

**Avoids pitfalls:** Pitfall 2 (silent paywall failure and login-page summarization).

**Research flag:** This phase may benefit from a quick research pass on current WSJ anti-bot detection state before implementation. Cookie-based access from GitHub Actions datacenter IPs carries MEDIUM confidence that it will work in practice.

### Phase 3: Polish and Resilience

**Rationale:** With content flowing and delivery proven, address the quality and reliability details that make this a trustworthy daily tool rather than a fragile experiment.

**Delivers:** A visually polished email with consistent design, silent source failures handled gracefully, duplicate articles prevented, and clear monitoring output.

**Addresses features:**
- Wispr Flow-inspired visual design (minimal, table-based, inline CSS, dark mode via @media prefers-color-scheme)
- Deduplication store (committed JSON, URL-based, 7-day window)
- "Quiet day" / empty section suppression with "X of Y sources active" footer
- Minimum article threshold (skip send if < 3 articles total)
- Litmus/Email on Acid testing of final template
- SMTP failure handling: exit code 1 on auth failure; log SMTP response code

**Avoids pitfalls:** Pitfall 4 (SMTP silent success), Pitfall 7 (duplicate articles across days), Pitfall 8 (Gmail CSS stripping layout), Pitfall 9 (workflow succeeds but email not delivered), Pitfall 11 (empty email sent on slow news day).

### Phase Ordering Rationale

- Models and filter come first because every other module imports from them; filter has no external deps and validates logic with mock data
- Email delivery (send.py) is built before content sources because if Gmail rejects the App Password, you want to know before building 5 fetchers
- Simple RSS sources before authenticated scraping: faster to ship, lower risk, proves the pipeline structure before adding the highest-complexity component
- Summarization before rendering: need real summaries to validate the template looks correct
- Visual design last: correct behavior beats correct appearance; polish after reliability is proven
- Keepalive workflow must be installed before the first week, not at "polish" phase — it will be too late once inactivity accrues

### Research Flags

Phases likely needing deeper research during planning:
- **Phase 2 (Authenticated Sources):** Cookie-based scraping from GitHub Actions IP ranges is MEDIUM confidence. Test against WSJ from an Actions runner as the first implementation step. Anti-bot behavior (Cloudflare, Akamai, DataDome) changes frequently — the Playwright stealth fallback may need evaluation if httpx is consistently blocked.

Phases with well-documented patterns (skip research-phase):
- **Phase 1 (Core RSS Pipeline):** feedparser, smtplib, Jinja2, GitHub Actions cron, and Claude Batch API are all high-confidence, well-documented components with verified code patterns in the research files.
- **Phase 3 (Polish):** Deduplication via committed JSON, premailer CSS inlining, and table-based email layout are all standard patterns with clear implementation paths.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | All library versions verified via PyPI; GitHub Actions patterns confirmed via official docs; Claude Haiku model ID confirmed via Anthropic API docs |
| Features | MEDIUM-HIGH | RSS/email patterns HIGH confidence from multiple independent sources; WSJ/paywall patterns MEDIUM due to ToS ambiguity and anti-bot unknowns |
| Architecture | HIGH | Claude Batch API from official docs; pipeline pattern is standard for this class of tool; email rendering from multiple verified 2025-2026 sources |
| Pitfalls | MEDIUM-HIGH | GitHub inactivity rule and cron behavior confirmed via official docs; Gmail CSS stripping confirmed by multiple 2026 sources; cookie expiry behavior inferred from documented scraping patterns |

**Overall confidence:** MEDIUM-HIGH

### Gaps to Address

- **WSJ/The Information scraping viability from Actions IPs:** Cannot confirm until tested in an actual GitHub Actions environment. The technical approach is correct but whether GitHub's datacenter IP ranges are blocked by WSJ's anti-bot systems is unknown. Plan for the Playwright stealth fallback before Phase 2 ships.
- **Paul Graham feed solution longevity:** Community-maintained unofficial feeds (Olshansk/pgessays-rss) are themselves scrapers that may go stale. If they break, a custom `paulgraham.com/articles.html` scraper is needed. This is a known ongoing maintenance responsibility.
- **Gwern feed structure:** Research confirmed no native RSS; actual scraping approach needs validation against the live site before Phase 1 is complete.
- **Cookie expiry timeline:** Documented range of 30–90 days is based on general browser session patterns, not WSJ/The Information specific measurements. Real expiry timeline will only be known after the first production run.
- **premailer maintenance status:** Last PyPI release was August 2021. The library appears feature-complete but may have compatibility issues with newer CSS. Validate during Phase 3 template development.

## Sources

### Primary (HIGH confidence)
- feedparser PyPI + GitHub: https://pypi.org/project/feedparser/ — RSS parsing, feed format handling, DST bugs
- Anthropic models page: https://platform.claude.com/docs/en/about-claude/models/overview — claude-haiku-4-5-20251001 model ID verified
- Anthropic SDK PyPI: https://pypi.org/project/anthropic/ — version 0.84.0 verified Feb 25, 2026
- Anthropic Batch Processing API: https://platform.claude.com/docs/en/build-with-claude/batch-processing — Batch API patterns and polling
- Anthropic Rate Limits: https://platform.claude.com/docs/en/api/rate-limits — Tier 1 limits, Haiku vs Sonnet differences
- GitHub Actions schedule docs: https://docs.github.com/en/actions/writing-workflows/choosing-when-your-workflow-runs/events-that-trigger-workflows#schedule — cron, inactivity rule
- Keepalive Workflow GitHub Action: https://github.com/marketplace/actions/keepalive-workflow — confirmed solution for 60-day inactivity issue
- httpx PyPI: https://pypi.org/project/httpx/ — version 0.28.1 verified
- playwright PyPI: https://pypi.org/project/playwright/ — version 1.58.0 verified Jan 30, 2026
- beautifulsoup4 PyPI: https://pypi.org/project/beautifulsoup4/ — version 4.14.3 verified Nov 30, 2025
- Jinja2 PyPI: https://pypi.org/project/Jinja2/ — version 3.1.6 verified Mar 5, 2025
- Paul Graham RSS broken: https://news.ycombinator.com/item?id=41474088 — confirmed feed breakage Oct 2023
- Unofficial PG RSS: https://github.com/Olshansk/pgessays-rss — confirmed community workaround

### Secondary (MEDIUM confidence)
- Email on Acid — Gmail CSS stripping behaviors confirmed 2025
- DEV Community (2026) — Complete guide to email client rendering differences
- n8n.io workflow templates — RSS-to-email pipeline pattern validation
- sureshjoshi.com — GitHub Actions cron gotchas
- scrapfly.io — cookie handling patterns for authenticated scraping
- Anthropic prompt caching docs — cache_control ephemeral pattern for repeated system prompts

### Tertiary (LOW confidence)
- Cookie-based WSJ scraping working reliably — technical approach validated, real-world anti-bot effectiveness untested from GitHub Actions IPs
- Long-term WSJ/The Information cookie viability — cookies expire; sites actively update defenses; requires ongoing monitoring

---
*Research completed: 2026-03-01*
*Ready for roadmap: yes*
