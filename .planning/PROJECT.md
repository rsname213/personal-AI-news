# Personal AI News Newsletter

## What This Is

A fully automated daily email newsletter sent to the owner each morning at 7-8am ET. It aggregates new content from 20 curated personal blogs, WSJ, The Information, and Anthropic's official channels — summarizing each item with a "why it matters" section — and delivers it as a beautifully designed email styled after the Wispr Flow aesthetic.

## Core Value

Every morning, the owner has a single, curated briefing of what matters in AI and tech — already read, already interpreted, zero manual effort.

## Requirements

### Validated

(None yet — ship to validate)

### Active

- [ ] Fetch new posts from 20 personal bloggers via RSS (last 24 hours only)
- [ ] Fetch top articles from WSJ (authenticated, subscriber access, top 5)
- [ ] Fetch top articles from The Information (authenticated, subscriber access, top 5)
- [ ] Fetch new posts/updates from Anthropic Official channels
- [ ] Summarize each item with AI (summary + "why it matters")
- [ ] Generate a Wispr Flow-styled HTML email using the UI/UX Pro agent design
- [ ] Send email via Gmail (App Password auth) to owner each day at 7am ET
- [ ] Run automatically on GitHub Actions (daily cron schedule)
- [ ] Never include articles older than 24 hours
- [ ] Cap at 5 items per source section

### Out of Scope

- Multi-recipient delivery — this is a personal newsletter, not a platform
- User management or subscription system — not needed
- Storing article history in a database — stateless per-run is sufficient for v1
- Twitter/X aggregation — not in source list
- Mobile app — email is the delivery mechanism

## Context

**Bloggers to monitor (RSS feeds):**
- Andrew Bosworth (boz.com)
- Ben Kuhn (benkuhn.net)
- Ava Huang
- Brie Wolfson
- Calvin French-Owen
- Holden Karnofsky — Cold Takes (cold-takes.com)
- Graham Duncan
- Gwern Branwen (gwern.net)
- Henrik Karlsson (escapingflatland.substack.com)
- Justin Meiners
- James Somers (jsomers.net)
- Kevin Kwok (kwokchain.com)
- Tyler Cowen — Marginal Revolution (marginalrevolution.com)
- Max Hodak
- Nabeel Qureshi (nabeelqu.co)
- Nadia Asparouhova (nadia.xyz)
- Paul Graham (paulgraham.com)
- Sam Altman (blog.samaltman.com)
- Scott Alexander — Slate Star Codex / Astral Codex Ten (astralcodexten.com)
- Tom Tunguz (tomtunguz.com)

**Paid news sources:**
- WSJ — authenticated scraping using subscriber cookies (stored as GitHub Secret)
- The Information — authenticated scraping using subscriber cookies (stored as GitHub Secret)

**Official channels:**
- Anthropic blog (anthropic.com/news or RSS)

**Email design:** Based on Wispr Flow visual identity (https://wisprflow.ai) — designed via UI/UX Pro agent

**Delivery:** Gmail via SMTP with App Password (stored as GitHub Secret: GMAIL_USER, GMAIL_APP_PASSWORD)

**Schedule:** GitHub Actions cron — 7am ET daily (12:00 UTC)

## Constraints

- **Hosting**: GitHub Actions only — no persistent server, stateless execution per run
- **Auth**: Gmail App Password for sending; subscriber cookies for WSJ/The Information
- **Recency**: Strict 24-hour window — stale content is excluded, not buffered
- **Volume**: Max 5 items per source section to keep email scannable
- **Timezone**: 7-8am US Eastern (UTC-5 in winter, UTC-4 in summer)
- **Language**: Python preferred for scraping/RSS/email ecosystem

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| GitHub Actions for scheduling | Free, no server to maintain, secrets management built-in | — Pending |
| Gmail App Password (not OAuth) | Simpler setup, sufficient for single-user case | — Pending |
| Authenticated cookie scraping for WSJ/The Info | User has subscriptions; full summaries require access | — Pending |
| AI summarization via Claude API | Anthropic-native, high quality, already in ecosystem | — Pending |
| HTML email with Wispr Flow design | Visual identity is clean, minimal, modern | — Pending |

---
*Last updated: 2026-03-01 after initialization*
