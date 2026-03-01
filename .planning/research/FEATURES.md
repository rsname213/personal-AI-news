# Feature Landscape

**Domain:** Personal automated daily newsletter digest (self-sent)
**Researched:** 2026-03-01
**Overall confidence:** MEDIUM-HIGH (RSS/email patterns HIGH from multiple sources; WSJ/paywall patterns MEDIUM due to ToS complexity)

---

## Table Stakes

Features without which the product fails to deliver its core value. Missing any of these = no usable digest.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| RSS ingestion for personal blogs | Core data pipeline — no RSS, no content | Low | `feedparser 6.0.12` is the standard. Handles RSS 0.9x/1.0/2.0 and Atom. Normalizes formats. |
| 24-hour freshness filter | Stale content defeats the "what happened today" premise | Low | Compare `entry.published_parsed` against `datetime.now(UTC) - timedelta(hours=24)`. Use `python-dateutil` for robustness — feedparser has known DST double-application bugs. |
| AI summarization with "why it matters" | The core value proposition — not just headlines, but interpretation | Medium | Two-section output per item: (1) 2-3 sentence factual summary, (2) "Why it matters" framing. The Rundown AI pattern: what happened → why it matters → implication. |
| HTML email generation | Email is the delivery mechanism | Medium | Jinja2 templates rendered to HTML. Must stay under 102KB to avoid Gmail clipping. Inline CSS only — Gmail strips `<style>` blocks aggressively. |
| Gmail SMTP delivery | The actual delivery | Low | `smtplib` + App Password. Well-documented pattern. Store `GMAIL_USER` and `GMAIL_APP_PASSWORD` as GitHub Secrets. |
| GitHub Actions cron scheduling | "Zero manual effort" is the entire point | Low | `.github/workflows/*.yml` with `schedule: cron: '0 12 * * *'` (noon UTC = 7am ET). Add `workflow_dispatch` for manual test triggers. |
| Per-source section grouping | Digest structure — reader knows where to look | Low | Separate sections: Personal Blogs / Bloggers, Anthropic Official. Each section independently capped. |
| Source cap (5 items per section) | Prevents email from becoming overwhelming | Low | Hard cap in the aggregation layer, not the prompt. Apply before calling the AI to control cost and length. |

---

## Differentiators

Features that make this personal digest exceptional rather than merely functional.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Structured "why it matters" framing | The insight layer most digests lack — contextualizes news for the owner's specific interests | Medium | Prompt engineering: "You are briefing an AI/tech founder. For each article: (1) summarize factually in 2-3 sentences, (2) explain why this matters specifically for someone tracking AI progress, startup strategy, and deep work. Avoid generic observations." |
| Per-blogger attribution with voice awareness | Personal blogs have distinct author voices — knowing who said what matters | Low | Include author name and blog name as header per item. The 20 bloggers are specifically chosen for their perspective, so attribution is part of the value. |
| Fallback chain for broken/missing feeds | Many of the 20 bloggers have unreliable or missing RSS feeds (Paul Graham's feed broke after Oct 2023; Gwern's is structurally unusual) | High | Priority chain: (1) native RSS, (2) Substack RSS (for Substack blogs), (3) HTML scraping with BeautifulSoup for blogs with no feed, (4) log warning and skip. This is per-source configuration. |
| Freshness-aware "quiet day" handling | If a source publishes nothing in 24h, suppress the section rather than show an empty header | Low | Check item count after filtering; if zero, omit section entirely from email. Include a footer "Sources checked: X / X active today." |
| Wispr Flow-styled visual design | Clean, minimal, modern aesthetic that doesn't feel like a corporate newsletter | High | Single-column, generous white space, muted color palette, consistent section headers. Design via UI/UX Pro agent. The constraint: everything must be inline CSS (Gmail). |
| Cost-bounded AI calls | AI calls are per-item — uncapped fetching → uncapped cost | Medium | Pre-filter to max 5 items per source before sending to Claude API. Set max token budget per summary (e.g., 200 tokens). Estimate: 5 sources × 5 items × ~300 tokens = ~7,500 tokens/day, well within practical budget. |
| WSJ/The Information authenticated content | Full article access vs headline-only — significantly higher value summaries | High | Use `requests.Session` with subscriber cookies stored as GitHub Secrets. Cookies expire — build cookie health check that logs warnings when 403s are returned. See Anti-Features section for ToS notes. |
| Anthropic official channel monitoring | Owner works in AI — Anthropic announcements are tier-1 content | Low | `anthropic.com/news` has an RSS feed. Straightforward feedparser ingestion. |
| Deduplication across sources | Same story from multiple sources → one entry | Medium | Track by (normalized URL, title hash). For personal bloggers this is rare but possible when they cross-post. Primary dedup key: `entry.id` GUID; fallback: URL normalization stripping tracking params. |

---

## Anti-Features

Things to deliberately NOT build. Scope creep for a personal tool.

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| Multi-recipient / subscription system | This is a personal digest, not a newsletter platform. Adding subscribers means GDPR, unsubscribe flows, bounce handling. | Keep recipient hardcoded as env var. One line of config. |
| Persistent database / article history | State across runs adds infrastructure (SQLite file in repo, or external DB). For a stateless GitHub Actions run, it adds failure modes with no clear benefit. | Run is stateless. Re-fetch all sources each run. 24h window is the only "memory" needed. |
| Read/click tracking | Means embedding tracking pixels or link redirects. Not appropriate for a self-sent personal digest. | Not needed. The owner reads what they want. |
| Twitter/X or social media ingestion | Anti-scraping posture on X is severe (API access closed 2023, defenses shift every 2-4 weeks). High maintenance, unreliable. | Stick to RSS and authenticated HTTP. The 20 bloggers cover the ideas that surface on X anyway. |
| User preferences / interest scoring | ML-based relevance scoring adds complexity with marginal gain when the source list IS the curation. | The 20-blogger list is hand-curated. That IS the filter. |
| Retry/buffer for 0-article days | Buffering stale content to "fill" a quiet day is worse than an empty section. | Log "no new content" and omit the section. Empty days are valid signal. |
| Storing cookies in the repo | GitHub Secrets exist for exactly this purpose. Cookies in the codebase = credential leak risk. | `GITHUB_SECRETS`: `WSJ_COOKIES_JSON`, `THE_INFORMATION_COOKIES_JSON`. |
| Over-engineering email template | Complex responsive layouts with media queries do not work in Gmail desktop. | Single-column, inline CSS, 500-600px max width. Simplicity is the right choice. |
| Automatic source discovery | Auto-detecting new blogs the owner should follow is scope creep. | Owner curates sources manually in config. |

---

## Feature Dependencies

```
GitHub Actions cron
  └── Python script entry point
        ├── RSS ingestion (feedparser)
        │     └── 24-hour freshness filter (python-dateutil)
        │           └── Deduplication (GUID tracking within run)
        │                 └── Source cap (5 items/section)
        │
        ├── Authenticated HTTP (requests.Session + cookies)
        │     └── WSJ article fetching
        │     └── The Information article fetching
        │           └── Cookie health check → warn on 403
        │
        ├── Claude API summarization
        │     └── Requires: filtered + capped article list
        │     └── Produces: (summary, why_it_matters) per item
        │
        ├── Jinja2 HTML template rendering
        │     └── Requires: summarized items grouped by source
        │     └── Produces: HTML email string
        │     └── Constraint: inline CSS, <102KB total
        │
        └── Gmail SMTP delivery
              └── Requires: rendered HTML, GMAIL_USER, GMAIL_APP_PASSWORD
              └── Sends to: hardcoded owner email
```

**Critical path:** RSS ingestion → freshness filter → AI summarization → HTML render → send. Each step is blocking. A failure at any step = no email that day. Design with `try/except` at each stage with graceful degradation (skip failed source, don't abort entire run).

---

## MVP Recommendation

**Phase 1 — Core pipeline (ship and validate):**
1. RSS ingestion for personal bloggers via feedparser (table stakes)
2. 24-hour freshness filter with UTC-aware datetime (table stakes)
3. Anthropic official channel (simple RSS, tier-1 content)
4. Claude API summarization with "why it matters" framing (core value)
5. Basic HTML email via Jinja2 + Gmail SMTP (table stakes)
6. GitHub Actions cron (table stakes)

**Phase 2 — Authenticated sources:**
7. WSJ authenticated scraping (high value, elevated complexity)
8. The Information authenticated scraping (same pattern as WSJ)
9. Cookie health check / expiry warnings

**Phase 3 — Polish and resilience:**
10. Fallback chain for missing/broken RSS feeds (Paul Graham, Gwern)
11. Wispr Flow visual design (differentiator)
12. Deduplication across sources
13. Graceful per-source error handling ("quiet day" empty section suppression)

**Defer indefinitely:**
- All anti-features above

---

## Source-Specific Complexity Notes

| Source | Feed Type | Reliability | Special Handling |
|--------|-----------|-------------|-----------------|
| Paul Graham (paulgraham.com) | RSS broken since Oct 2023 | LOW | Requires HTML scraping or community-maintained unofficial feed (github.com/Olshansk/pgessays-rss pattern) |
| Gwern (gwern.net) | Has RSS but structurally unusual for wiki-style site | MEDIUM | Test before assuming standard feedparser works |
| Substack blogs (escapingflatland, etc.) | Native Substack RSS — highly reliable | HIGH | `[subdomain].substack.com/feed` pattern |
| Tom Tunguz (tomtunguz.com) | Standard blog RSS | HIGH | Standard feedparser |
| Marginal Revolution | Standard blog RSS | HIGH | Standard feedparser |
| WSJ | No public RSS for subscriber content | N/A | Requires authenticated `requests.Session` with subscriber cookies |
| The Information | No public RSS | N/A | Requires authenticated `requests.Session` with subscriber cookies |
| Anthropic (anthropic.com/news) | Has RSS/Atom | HIGH | Standard feedparser |

---

## Legal and Ethical Notes on Authenticated Scraping

**WSJ and The Information:** Using subscriber session cookies to fetch content the owner has paid for is a legal gray area. The owner's personal subscription gives them a right to read the content. Using cookies to automate that reading for personal use (self-only digest) is a common pattern. The project explicitly limits this to the owner's own subscriptions, non-redistributed, self-consumed. This is not the same as scraping and republishing.

However: both outlets' Terms of Service likely prohibit automated scraping regardless. The CFAA (US) applies to "unauthorized" access — the owner's cookies represent authorized access under the subscriber's account. The risk is ToS violation leading to account suspension, not criminal liability, for a single-user personal digest.

**Recommendation:** Implement as designed (PROJECT.md decision already made). Build cookie health monitoring so the owner knows promptly when cookies expire and can refresh them manually.

---

## Sources

- [Readless — Best Newsletter Management Tools 2026](https://www.readless.app/blog/best-newsletter-management-tools-2026) — MEDIUM confidence (marketing site but covers ecosystem accurately)
- [n8n — Personalized AI Tech Newsletter workflow](https://n8n.io/workflows/3986-personalized-ai-tech-newsletter-using-rss-openai-and-gmail/) — HIGH confidence (real workflow template)
- [feedparser — PyPI](https://pypi.org/project/feedparser/) — HIGH confidence (official)
- [feedparser — GitHub (kurtmckee)](https://github.com/kurtmckee/feedparser) — HIGH confidence (official)
- [Building an AI-Powered Morning Digest (BUSN4400, Feb 2026)](https://busn4400.wordpress.com/2026/02/16/building-an-ai-powered-morning-digest/) — HIGH confidence (real implementation)
- [Design Email Digest Templates — EmailMavlers](https://www.emailmavlers.com/blog/design-email-digest-templates/) — MEDIUM confidence
- [The Rundown AI](https://www.therundown.ai/) — HIGH confidence (primary "why it matters" pattern)
- [Paul Graham Essays RSS — Hacker News thread](https://news.ycombinator.com/item?id=41474088) — HIGH confidence (confirms RSS breakage)
- [Unofficial Paul Graham RSS — GitHub](https://github.com/Olshansk/pgessays-rss) — HIGH confidence (real workaround)
- [No RSS Feed? No Problem — Olshansky Substack](https://olshansky.substack.com/p/no-rss-feed-no-problem-using-claude) — MEDIUM confidence
- [RSS Feed Integration with Freshness Filtering — zread.ai](https://zread.ai/sansan0/TrendRadar/25-rss-feed-integration-with-freshness-filtering) — MEDIUM confidence
- [feedparser timezone issue — GitHub #321](https://github.com/kurtmckee/feedparser/issues/321) — HIGH confidence (official issue thread)
- [Complete Guide to Email Client Rendering Differences 2026 — DEV Community](https://dev.to/aoifecarrigan/the-complete-guide-to-email-client-rendering-differences-in-2026-243f) — HIGH confidence (current, comprehensive)
- [Stop Using "Summarize" — Tom's Guide](https://www.tomsguide.com/ai/stop-using-summarize-this-claude-prompt-extracts-the-insights-you-actually-need) — MEDIUM confidence
- [Schedule Python Scripts with GitHub Actions — davidmuraya.com](https://davidmuraya.com/blog/schedule-python-scripts-github-actions/) — HIGH confidence
- [Send Email using GitHub Actions — paulie.dev, 2025](https://www.paulie.dev/posts/2025/02/how-to-send-email-using-github-actions/) — HIGH confidence
- [Cookie handling for authenticated scraping — scrapfly.io](https://scrapfly.io/blog/posts/how-to-handle-cookies-in-web-scraping) — MEDIUM confidence
