# Phase 1: Core Pipeline - Research

**Researched:** 2026-03-01
**Domain:** Python RSS pipeline — feedparser, Claude Haiku summarization, Gmail SMTP delivery
**Confidence:** HIGH

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| PIPE-01 | System fetches content from all sources once per day and produces a single email output | Linear pipeline architecture: fetch → filter → summarize → render → send; orchestrator.py drives all stages |
| PIPE-02 | System filters out any content older than 24 hours from time of run | feedparser `published_parsed` returns UTC-normalized struct_time; use 25-hour window to absorb Actions delay |
| PIPE-03 | System caps output at 5 items per source section | filter.py applies per-source cap after recency filter, before summarization |
| PIPE-04 | System degrades gracefully per source — a failed source produces an empty section, never blocks the email | Fail-soft collection pattern: each fetcher wrapped in try/except, returns `[]` on any exception |
| RSS-01 | System fetches new posts from all 20 personal bloggers via RSS/Atom feeds | feedparser 6.0.12 normalizes all feed formats; 18 of 20 bloggers have working RSS/Atom feeds |
| RSS-02 | System handles Paul Graham's broken official RSS via a community-maintained feed or custom HTML scraper | Unofficial feed: `https://raw.githubusercontent.com/olshansk/pgessays-rss/main/feed.xml` (updated nightly via GitHub Actions); fallback: scrape paulgraham.com/articles.html |
| RSS-03 | System handles Gwern Branwen's missing RSS via a custom HTML scraper | gwern.net has no native RSS (confirmed via GitHub issue #11 on gwern/gwern.net); scrape gwern.net/blog/index |
| RSS-04 | System fetches new posts from Anthropic's official news/blog channel | No official Anthropic RSS; use community feed: `https://raw.githubusercontent.com/taobojlen/anthropic-rss-feed/main/anthropic_news_rss.xml`; fallback: scrape anthropic.com/news |
| RSS-05 | System logs a warning per source when a feed is unavailable, without crashing | Per-source try/except + structured logging: `[WARN] {source}: {error}` to stdout |
| RSS-06 | System fetches top articles from WSJ via public RSS feed | WSJ public RSS at `https://feeds.a.wsj.com/rss/RSSWSJD.xml` — feedparser handles without auth |
| RSS-07 | System fetches top articles from The Information via subscriber RSS feed | `https://www.theinformation.com/feed` — subscriber RSS; may need auth cookie |
| SUMM-01 | System generates a 2-4 sentence summary for each article using Claude Haiku via the Batch API | Use sequential `client.messages.create()` with prompt caching, NOT async Batch API — Batch API completion can take up to 1 hour, incompatible with 30-minute Actions timeout |
| SUMM-02 | Every summary includes a distinct "Why it matters" section | Structured prompt with XML-tagged output sections; system prompt cached via `cache_control: ephemeral` |
| SUMM-03 | Each digest item includes article title, publication date, source name, and direct URL | Fields stored in `SummarizedArticle` dataclass; rendered by Jinja2 template |
| SUMM-04 | System handles Claude API failures gracefully | Per-article try/except around `client.messages.create()`; fall back to article title + URL only |
| EMAIL-03 | Email has clear section headers per source category | Jinja2 template groups articles by `source_category` (Personal Blogs / WSJ / The Information / Anthropic) |
| DEL-01 | Email is sent via Gmail SMTP using an App Password stored in GitHub Secrets | `smtplib.SMTP_SSL("smtp.gmail.com", 465)` + `GMAIL_APP_PASSWORD` env var |
| DEL-02 | Email is addressed to and from the same Gmail account (self-send) | `GMAIL_USER` used as both From and To |
| DEL-03 | Email subject line includes the current date | Subject: `f"AI Briefing — {datetime.now().strftime('%B %-d, %Y')}"` |
| DEL-04 | System logs a clear error when Gmail SMTP sending fails | Catch `smtplib.SMTPException`, log error, exit code 1 |
</phase_requirements>

---

## Summary

Phase 1 builds the complete end-to-end pipeline from RSS ingestion through Claude Haiku summarization to Gmail delivery. All components use well-established Python libraries with verified versions. The architectural pattern is a stateless linear pipeline: fetch → filter → summarize → render → send. Each stage produces typed output consumed by the next, with fail-soft collection ensuring a broken source never blocks email delivery.

Two sources require non-standard handling from day one and are Phase 1 blockers: Paul Graham (no official RSS since October 2023 — use community feed as primary, HTML scraper as fallback) and Gwern Branwen (no RSS ever — requires HTML scraper of gwern.net/blog/index). Anthropic's blog also lacks an official RSS feed and requires a community-maintained feed. These three non-standard sources must be implemented before Phase 1 is considered complete.

The most important implementation decision for Phase 1 is the Claude summarization approach: the project spec says "Batch API" but the Batch API is asynchronous with up to 1-hour processing time, which is incompatible with the 30-minute GitHub Actions timeout. The correct approach is sequential `client.messages.create()` calls with `cache_control: ephemeral` on the system prompt, which provides 90% cost reduction on repeated calls within a single run and completes synchronously. WSJ is available via a public RSS feed (no authentication needed for Phase 1 scope), while The Information's subscriber RSS feed requires testing.

**Primary recommendation:** Build in dependency order — models.py first, then send.py to prove delivery, then RSS fetchers, then summarizer, then renderer, then orchestrator. This order lets you fail fast on the delivery mechanism before investing in content sources.

---

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| feedparser | 6.0.12 | RSS/Atom parsing for all 20 personal blogs + Anthropic feed | Only Python library that normalizes 20+ feed formats; auto-detects RSS 0.9x/1.0/2.0, Atom 0.3/1.0, RDF; handles malformed feeds from personal blogs; `published_parsed` normalizes all dates to UTC |
| beautifulsoup4 | 4.14.3 | HTML scraping for Paul Graham, Gwern, Anthropic fallback | Standard HTML parsing; lxml backend handles malformed HTML well; same dep used by premailer |
| lxml | latest stable | Parser backend for BeautifulSoup | Fastest BS4 parser; handles malformed HTML; dual-purpose (also used by premailer) |
| anthropic | 0.84.0 | Claude Haiku API calls for article summarization | Official Python SDK; type-safe; handles retries; supports prompt caching via `cache_control` |
| Jinja2 | 3.1.6 | HTML email template rendering | Industry standard Python templating; template inheritance, loops, conditionals |
| premailer | 3.10.0 | CSS inlining for Gmail compatibility | Converts `<style>` block CSS to inline `style=""` attributes; essential since Gmail strips head styles |
| smtplib | stdlib | Gmail SMTP delivery | Zero additional dependency; port 465 SSL with App Password is sufficient for single-recipient |
| email.mime | stdlib | MIME message construction | RFC-compliant `MIMEMultipart('alternative')` with plain-text + HTML parts |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| httpx | 0.28.1 | HTTP requests for Gwern/PG HTML scraping and Anthropic fallback scraping | When feedparser cannot access content; Phase 2 will use it for cookie-auth |
| python-dateutil | latest stable | Robust date parsing for edge-case pubDate formats | When feedparser's `published_parsed` returns None for unusual date formats |
| cssutils | latest stable | CSS parsing (premailer dependency) | Required by premailer; install automatically |
| cssselect | latest stable | CSS selector support (premailer dependency) | Required by premailer; install automatically |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| feedparser 6.0.12 | atoma, listparser | Smaller ecosystems; feedparser normalizes 20+ formats automatically |
| feedparser 6.0.12 | xml.etree directly | Re-implements normalization; fragile against malformed feeds from personal blogs |
| smtplib + App Password | Gmail OAuth2 | OAuth requires token refresh flow; App Password simpler for non-interactive servers |
| smtplib + App Password | SendGrid / Mailgun | Personal use; 1 recipient; no need for deliverability infrastructure or extra cost |
| sequential messages.create() | Batch API | Batch API is async (up to 1 hour); incompatible with 30-min Actions timeout; sequential + prompt caching achieves ~90% same-run cost savings |
| Jinja2 + premailer | MJML | MJML requires Node.js; adds non-Python runtime dependency |

**Installation:**
```bash
pip install feedparser==6.0.12 beautifulsoup4==4.14.3 lxml anthropic==0.84.0 Jinja2==3.1.6 premailer==3.10.0 httpx==0.28.1 python-dateutil cssutils cssselect
```

**Complete requirements.txt:**
```
feedparser==6.0.12
beautifulsoup4==4.14.3
lxml>=5.0.0
anthropic==0.84.0
Jinja2==3.1.6
premailer==3.10.0
httpx==0.28.1
python-dateutil
cssutils>=2.9.0
cssselect>=1.2.0
```

---

## Architecture Patterns

### Recommended Project Structure

```
/
├── orchestrator.py              # Entry point: drives all stages, collects partial results
├── models.py                    # RawArticle, FilteredArticle, SummarizedArticle dataclasses
├── requirements.txt
├── .github/
│   └── workflows/
│       ├── daily-newsletter.yml # Main cron workflow
│       └── keepalive.yml        # Prevent 60-day inactivity disable
├── fetchers/
│   ├── __init__.py
│   ├── rss.py                   # feedparser — handles all 20 standard RSS sources
│   ├── paul_graham.py           # Community feed + HTML scraper fallback
│   ├── gwern.py                 # Custom HTML scraper (no native RSS)
│   └── anthropic_blog.py        # Community RSS feed + anthropic.com/news fallback
├── pipeline/
│   ├── __init__.py
│   ├── filter.py                # 24h/25h recency + 5-item-per-source cap; pure Python
│   ├── summarize.py             # Sequential Claude Haiku calls with prompt caching
│   ├── render.py                # Jinja2 template rendering + premailer CSS inlining
│   └── send.py                  # smtplib Gmail SMTP delivery
└── templates/
    └── digest.html.j2           # Table-based email template with dark mode media query
```

### Pattern 1: Typed Data Flow with Dataclasses

**What:** Three dataclasses carry all inter-stage data. Each stage inputs the previous type and returns the next.
**When to use:** Always — prevents silent data corruption between stages, provides IDE completion.

```python
# Source: models.py
from dataclasses import dataclass, field
from datetime import datetime

@dataclass
class RawArticle:
    id: str              # stable hash of URL (hashlib.md5(url.encode()).hexdigest())
    url: str
    title: str
    content_text: str    # RSS feed content or scraped body text
    published_at: datetime   # UTC-aware datetime
    source_name: str     # e.g., "Ben Kuhn", "WSJ", "Anthropic"
    source_category: str # "Personal Blogs" | "WSJ" | "The Information" | "Anthropic"

@dataclass
class FilteredArticle(RawArticle):
    pass  # Inherits all fields; filter.py just selects from RawArticle

@dataclass
class SummarizedArticle(FilteredArticle):
    summary: str = ""
    why_it_matters: str = ""
    summarization_failed: bool = False  # True if API call failed; renders without summary
```

### Pattern 2: Fail-Soft Source Collection

**What:** Each fetcher is wrapped in try/except at the orchestrator level. Any failure returns an empty list and logs a warning. The orchestrator always produces an email.
**When to use:** Always — a single bad feed URL must never block delivery.

```python
# Source: orchestrator.py pattern
import sys
from fetchers import rss, paul_graham, gwern, anthropic_blog

FETCHERS = [
    (rss.fetch_all, "RSS feeds (20 sources)"),
    (paul_graham.fetch, "Paul Graham"),
    (gwern.fetch, "Gwern Branwen"),
    (anthropic_blog.fetch, "Anthropic Blog"),
]

def collect_all() -> list[RawArticle]:
    results = []
    for fetch_fn, source_name in FETCHERS:
        try:
            articles = fetch_fn()
            results.extend(articles)
            print(f"[OK] {source_name}: {len(articles)} articles")
        except Exception as e:
            print(f"[WARN] {source_name} failed: {e}")
            # Continue — partial email > no email
    return results
```

### Pattern 3: feedparser with UTC-Safe Date Filtering

**What:** Use `published_parsed` (returns UTC struct_time, not raw string). Convert to UTC-aware datetime. Use 25-hour window (not 24h) to absorb GitHub Actions scheduling delays.
**When to use:** All RSS fetchers.

```python
# Source: feedparser 6.0.12 official docs — published_parsed is UTC-normalized
import feedparser
from datetime import datetime, timezone, timedelta
import hashlib

def fetch_feed(feed_url: str, source_name: str, source_category: str) -> list[RawArticle]:
    cutoff = datetime.now(timezone.utc) - timedelta(hours=25)  # 25h, not 24h
    feed = feedparser.parse(feed_url)
    articles = []
    for entry in feed.entries:
        # published_parsed may be None if feed omits dates
        if not hasattr(entry, 'published_parsed') or entry.published_parsed is None:
            continue
        published_at = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
        if published_at < cutoff:
            continue
        url = getattr(entry, 'link', '')
        content = getattr(entry, 'content', [{}])[0].get('value', '')
        if not content:
            content = getattr(entry, 'summary', '')
        articles.append(RawArticle(
            id=hashlib.md5(url.encode()).hexdigest(),
            url=url,
            title=getattr(entry, 'title', 'Untitled'),
            content_text=content,
            published_at=published_at,
            source_name=source_name,
            source_category=source_category,
        ))
    return articles
```

### Pattern 4: Sequential Claude Summarization with Prompt Caching

**What:** Call `client.messages.create()` once per article in a loop. Mark the system prompt with `cache_control: ephemeral` — after the first call, subsequent calls in the same run pay only 10% of system-prompt tokens.
**When to use:** All summarization in Phase 1. Do NOT use Batch API — it is async and can take up to 1 hour, incompatible with 30-minute Actions timeout.

```python
# Source: Official Anthropic SDK docs — prompt caching with ephemeral cache_control
import anthropic
import os

client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

SYSTEM_PROMPT = """You are a concise AI/tech newsletter editor. For each article, output exactly:

<summary>2-3 sentences explaining what the article covers. Be specific and factual.</summary>
<why_it_matters>1-2 sentences on the non-obvious significance for AI/tech practitioners.</why_it_matters>

No preamble. No "the author argues" constructions. Be direct."""

def summarize_article(article: FilteredArticle) -> SummarizedArticle:
    try:
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=400,
            system=[
                {
                    "type": "text",
                    "text": SYSTEM_PROMPT,
                    "cache_control": {"type": "ephemeral"},  # Cache for 5 minutes
                }
            ],
            messages=[{
                "role": "user",
                "content": (
                    f"<article>\n"
                    f"Title: {article.title}\n\n"
                    f"Content:\n{article.content_text[:3000]}\n"
                    f"</article>"
                )
            }],
        )
        text = response.content[0].text
        # Parse XML tags from response
        import re
        summary = re.search(r'<summary>(.*?)</summary>', text, re.DOTALL)
        why = re.search(r'<why_it_matters>(.*?)</why_it_matters>', text, re.DOTALL)
        return SummarizedArticle(
            **{k: v for k, v in article.__dict__.items()},
            summary=summary.group(1).strip() if summary else text[:300],
            why_it_matters=why.group(1).strip() if why else "",
            summarization_failed=False,
        )
    except Exception as e:
        print(f"[WARN] Summarization failed for '{article.title}': {e}")
        return SummarizedArticle(
            **{k: v for k, v in article.__dict__.items()},
            summary="",
            why_it_matters="",
            summarization_failed=True,
        )
```

### Pattern 5: Gmail SMTP Delivery with Explicit Error Handling

**What:** Use `smtplib.SMTP_SSL` on port 465. Wrap in try/except that exits with code 1 on failure (turns the Actions run red).
**When to use:** `pipeline/send.py`.

```python
# Source: Official Python smtplib docs + Gmail SMTP configuration
import smtplib, ssl, os
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

def send_email(subject: str, html_body: str, text_body: str) -> None:
    gmail_user = os.environ["GMAIL_USER"]
    gmail_password = os.environ["GMAIL_APP_PASSWORD"]

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = gmail_user
    msg["To"] = gmail_user   # self-send per DEL-02
    msg.attach(MIMEText(text_body, "plain"))
    msg.attach(MIMEText(html_body, "html"))

    try:
        context = ssl.create_default_context()
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context) as server:
            server.login(gmail_user, gmail_password)
            server.sendmail(gmail_user, gmail_user, msg.as_string())
            print("[OK] Email sent successfully")
    except smtplib.SMTPAuthenticationError as e:
        print(f"[ERROR] Gmail authentication failed: {e}")
        raise SystemExit(1)
    except smtplib.SMTPException as e:
        print(f"[ERROR] SMTP error: {e}")
        raise SystemExit(1)
```

### Pattern 6: GitHub Actions Workflow Structure

**What:** Single job, sequential steps, all secrets as env vars, 30-minute timeout, keepalive companion workflow.
**When to use:** `.github/workflows/daily-newsletter.yml`

```yaml
# Source: GitHub Actions official docs
name: Daily AI Newsletter

on:
  schedule:
    - cron: '0 12 * * *'  # 12:00 UTC = 7am EST (winter) / 8am EDT (summer)
  workflow_dispatch:        # Manual trigger for testing

jobs:
  send-newsletter:
    runs-on: ubuntu-latest
    timeout-minutes: 30     # Hard cap — prevents runaway jobs

    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'
          cache: 'pip'      # Cache keyed to requirements.txt hash

      - name: Install dependencies
        run: pip install -r requirements.txt

      - name: Run newsletter pipeline
        env:
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
          GMAIL_USER: ${{ secrets.GMAIL_USER }}
          GMAIL_APP_PASSWORD: ${{ secrets.GMAIL_APP_PASSWORD }}
        run: python orchestrator.py
```

**Keepalive workflow** (prevents 60-day inactivity disable):
```yaml
# .github/workflows/keepalive.yml
name: Keepalive

on:
  schedule:
    - cron: '0 0 1 * *'  # Monthly — well within 60-day window

jobs:
  keepalive:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: gautamkrishnar/keepalive-workflow@v2
```

### Anti-Patterns to Avoid

- **Using the Batch API for Phase 1 summarization:** The Batch API is asynchronous — results take up to 1 hour. A 30-minute Actions timeout means the job would timeout waiting for results. Use sequential `client.messages.create()` instead.
- **Passing article content directly to Claude without XML wrapping:** Reduces prompt injection risk. Always wrap in `<article>...</article>` tags in the user message.
- **Crashing on source failure:** Any exception in a fetcher must be caught at the orchestrator level. Returning `[]` + warning is always correct for individual sources.
- **Using external CSS or `<link>` stylesheets in email HTML:** Gmail strips them. Use premailer to inline all CSS.
- **Comparing naive datetimes:** Always use `timezone.utc` aware datetimes. feedparser's `published_parsed` is UTC struct_time — convert with `datetime(*parsed[:6], tzinfo=timezone.utc)`.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| RSS format normalization | Custom XML parser per blog | feedparser 6.0.12 | 20+ different feed formats; malformed XML; date format variants; feedparser handles all |
| CSS inlining for Gmail | String-replace CSS into style attrs | premailer 3.10.0 | CSS specificity, inheritance, shorthand expansion are non-trivial to replicate correctly |
| HTML parsing for scrapers | String regexes | BeautifulSoup4 + lxml | Handles malformed HTML that breaks naive regex; structured navigation |
| Email MIME structure | Manually format email headers | `email.mime` stdlib | RFC 2822 compliance; multipart boundary handling; encoding |
| Date parsing edge cases | Strptime with format string | feedparser's `published_parsed` | Handles RFC 2822, ISO 8601, locale strings, missing timezone info |

**Key insight:** In this domain, every "obvious" custom implementation has subtle edge cases that the libraries handle and you won't anticipate until they hit production.

---

## Source-Specific Implementation Notes

### Standard RSS Sources (18 sources — feedparser works directly)

All the following bloggers have working RSS/Atom feeds accessible via feedparser. Use a shared `fetch_feed()` function with each URL:

| Blogger | Feed URL (MEDIUM confidence — verify before coding) |
|---------|-----------------------------------------------------|
| Andrew Bosworth | `https://boz.com/feed` |
| Ben Kuhn | `https://www.benkuhn.net/rss/` |
| Ava Huang | Likely Substack: check avahu.substack.com/feed |
| Brie Wolfson | Likely Substack or personal blog RSS |
| Calvin French-Owen | `https://calv.info/rss.xml` or Substack |
| Holden Karnofsky (Cold Takes) | `https://www.cold-takes.com/rss/` |
| Graham Duncan | Check grahambduncan.com or Substack |
| Henrik Karlsson (Escaping Flatland) | Substack: `https://www.henrikkarlsson.xyz/feed` |
| Justin Meiners | Check personal site for feed |
| James Somers | `https://jsomers.net/feed.xml` |
| Kevin Kwok | Check kwokchain.com for feed |
| Tyler Cowen (Marginal Revolution) | `https://marginalrevolution.com/feed` |
| Max Hodak | Check maxhodak.com or Substack |
| Nabeel Qureshi | Check nabeelqu.co or Substack |
| Nadia Asparouhova | Check nadia.xyz or Substack |
| Sam Altman | `https://blog.samaltman.com/posts.atom` |
| Scott Alexander (Astral Codex Ten) | `https://astralcodexten.substack.com/feed/` |
| Tom Tunguz | `https://tomtunguz.com/feed/` |

NOTE: These feed URLs are MEDIUM confidence. Each URL must be verified by fetching before implementation. Several bloggers have moved platforms. Build the feed URL list as a config dict in `fetchers/rss.py` so URLs can be corrected without code changes.

### Paul Graham (RSS-02) — Community Feed + Scraper Fallback

**Primary:** `https://raw.githubusercontent.com/olshansk/pgessays-rss/main/feed.xml` — updated nightly via GitHub Actions; feedparser-compatible. HIGH confidence for content; MEDIUM confidence for long-term reliability (it is itself a scraper).

**Fallback:** Scrape `https://paulgraham.com/articles.html` with BeautifulSoup4. Parse `<table>` links, check dates from article page, filter to last 25 hours.

```python
# fetchers/paul_graham.py — primary approach
import feedparser

PG_COMMUNITY_FEED = "https://raw.githubusercontent.com/olshansk/pgessays-rss/main/feed.xml"

def fetch() -> list[RawArticle]:
    return fetch_feed(PG_COMMUNITY_FEED, "Paul Graham", "Personal Blogs")
```

### Gwern Branwen (RSS-03) — HTML Scraper Required

gwern.net has no native RSS feed (confirmed: GitHub issue #11 on gwern/gwern.net, opened 2015, still open 2026). The Substack newsletter (`gwern.substack.com`) is an alternative but publishes infrequently and is not guaranteed to capture new essays.

**Approach:** Scrape `https://gwern.net/blog/index` for new entries. Parse publication dates from the index. Follow links to check recency.

```python
# fetchers/gwern.py — HTML scraper skeleton
import httpx
from bs4 import BeautifulSoup
from datetime import datetime, timezone, timedelta

GWERN_BLOG_INDEX = "https://gwern.net/blog/index"

def fetch() -> list[RawArticle]:
    cutoff = datetime.now(timezone.utc) - timedelta(hours=25)
    try:
        response = httpx.get(GWERN_BLOG_INDEX, timeout=15)
        response.raise_for_status()
    except Exception as e:
        print(f"[WARN] Gwern fetch failed: {e}")
        return []

    soup = BeautifulSoup(response.text, "lxml")
    # Inspect actual page structure during implementation — date format and link structure
    # must be validated against live site before finalizing
    articles = []
    # ... parse soup, filter by date, return RawArticle list
    return articles
```

NOTE: The actual HTML structure of gwern.net/blog/index must be inspected before implementing the scraper. The skeleton above shows the correct pattern; the selector logic is implementation-specific.

### Anthropic Blog (RSS-04) — Community Feed + Scraper Fallback

**Primary:** `https://raw.githubusercontent.com/taobojlen/anthropic-rss-feed/main/anthropic_news_rss.xml` — community-maintained, updated regularly. MEDIUM confidence (community-maintained).

**Fallback:** Scrape `https://www.anthropic.com/news` with BeautifulSoup4. Parse article cards for title, date, URL.

### WSJ (RSS-06) — Public RSS, No Auth Needed for Phase 1

The WSJ public RSS at `https://feeds.a.wsj.com/rss/RSSWSJD.xml` returns headlines and teasers without authentication. Per the requirements, Phase 1 only needs "headline, teaser, and direct link" — this is available from the public feed. Full article scraping (requiring cookies) is Phase 2.

```python
WSJ_RSS = "https://feeds.a.wsj.com/rss/RSSWSJD.xml"
# fetch_feed(WSJ_RSS, "WSJ", "WSJ") — standard feedparser call
```

### The Information (RSS-07) — Subscriber RSS

`https://www.theinformation.com/feed` is listed as a subscriber RSS feed. Test during implementation whether this requires authentication. If it does, treat it as a Phase 2 item (cookie-based auth) and log a warning in Phase 1 if the feed returns no articles or a login redirect.

---

## Common Pitfalls

### Pitfall 1: Using Batch API Instead of Sequential Calls

**What goes wrong:** Submitting all articles to Batch API, then polling — the job hits the 30-minute timeout before results arrive (Batch API can take up to 1 hour per official docs).
**Why it happens:** The existing research (ARCHITECTURE.md) recommends Batch API, but that recommendation conflicts with the 30-minute Actions timeout. Sequential + prompt caching is the correct approach.
**How to avoid:** Use `client.messages.create()` in a loop. Mark system prompt with `cache_control: ephemeral`. First call: full cost. Subsequent calls (same run): 10% of system-prompt input tokens.
**Warning signs:** Actions job times out at exactly 30 minutes while in the polling loop.

### Pitfall 2: Paul Graham and Gwern Return Zero Articles (Silent)

**What goes wrong:** Both sources lack standard RSS. If the fetcher is not implemented, they return zero articles with no error. The email sends anyway with no PG/Gwern content — silently broken.
**Why it happens:** feedparser returns empty `entries` list for invalid feed URLs rather than raising an exception.
**How to avoid:** Implement PG and Gwern fetchers before marking Phase 1 done. Log article count for every source on every run. Zero from an expected-active source is a warning.
**Warning signs:** `[OK] Paul Graham: 0 articles` appearing in logs for weeks.

### Pitfall 3: feedparser published_parsed Is None

**What goes wrong:** Some feeds (especially personal blogs or older formats) omit `<pubDate>`. `published_parsed` returns `None`. The filter crashes with `TypeError` when converting to datetime.
**Why it happens:** Not all feeds include publication dates; feedparser returns `None` for missing optional fields.
**How to avoid:** Always check `entry.published_parsed is not None` before conversion. Skip articles with no date — they cannot be reliably filtered to 24 hours.
**Warning signs:** `TypeError: argument of type 'NoneType' is not iterable` in logs.

### Pitfall 4: GitHub Actions Cron Disabled After 60 Days

**What goes wrong:** The newsletter stops arriving with no notification. Repo has no commits for 60 days; GitHub silently disables scheduled workflows.
**Why it happens:** GitHub's documented policy for scheduled workflows on inactive repos.
**How to avoid:** Install the keepalive workflow (`.github/workflows/keepalive.yml`) before the repo enters maintenance mode. Must be done in Phase 1.
**Warning signs:** No email for 3+ days; Actions tab shows no recent runs.

### Pitfall 5: Gmail CSS Stripping Collapses Layout

**What goes wrong:** Email design works in browser preview but collapses in Gmail — fonts revert to defaults, spacing disappears.
**Why it happens:** Gmail strips `<head>` style blocks and all linked CSS. Only inline `style=""` attributes survive.
**How to avoid:** Use table-based layout in Jinja2 template. Run premailer's `transform()` on rendered HTML before sending. Never use Flexbox or Grid in email HTML.
**Warning signs:** Email looks correct in browser but broken in Gmail inbox.

### Pitfall 6: DST Timing Confusion

**What goes wrong:** Developer expects "7am ET" but email arrives at 7am in winter and 8am in summer. Causes confusion when debugging.
**Why it happens:** GitHub Actions cron has no timezone support; `0 12 * * *` is always UTC. EST = UTC-5 (7am), EDT = UTC-4 (8am).
**How to avoid:** Document in the workflow file: `# 12:00 UTC = 7am EST (winter) / 8am EDT (summer)`. The 7-8am window is intentional and acceptable per spec.
**Warning signs:** "Why did the email come at 8am today?" confusion in March/November.

### Pitfall 7: Anthropic Community Feed Goes Stale

**What goes wrong:** The community-maintained Anthropic RSS feed at `taobojlen/anthropic-rss-feed` stops being updated. Anthropic publishes new content but the feed doesn't reflect it.
**Why it happens:** Community feeds are third-party scrapers that may not be maintained long-term.
**How to avoid:** Build the Anthropic fetcher with a fallback: if community feed returns 0 articles, scrape `anthropic.com/news` directly. Log a warning when falling back.
**Warning signs:** Community feed's `<lastBuildDate>` is more than 48 hours old.

---

## Code Examples

### Per-Source Article Count Logging (Required for Health Monitoring)

```python
# orchestrator.py — log counts for every source, every run
for fetch_fn, source_name in FETCHERS:
    try:
        articles = fetch_fn()
        count = len(articles)
        print(f"[OK] {source_name}: {count} article{'s' if count != 1 else ''}")
        if count == 0:
            print(f"[WARN] {source_name}: returned 0 articles — check feed health")
        results.extend(articles)
    except Exception as e:
        print(f"[WARN] {source_name} fetch failed: {e}")
```

### Filter: 25-Hour Window + Per-Source Cap

```python
# pipeline/filter.py
from collections import defaultdict
from datetime import datetime, timezone, timedelta

def filter_articles(articles: list[RawArticle], hours: int = 25, cap: int = 5) -> list[FilteredArticle]:
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    recent = [a for a in articles if a.published_at >= cutoff]

    # Sort by recency, then cap per source
    recent.sort(key=lambda a: a.published_at, reverse=True)

    counts: dict[str, int] = defaultdict(int)
    filtered = []
    for article in recent:
        if counts[article.source_name] < cap:
            filtered.append(FilteredArticle(**article.__dict__))
            counts[article.source_name] += 1

    return filtered
```

### Jinja2 Rendering + Premailer Inlining

```python
# pipeline/render.py
from jinja2 import Environment, FileSystemLoader
from premailer import transform
from datetime import datetime

env = Environment(loader=FileSystemLoader("templates"), autoescape=True)

def render_email(articles: list[SummarizedArticle]) -> tuple[str, str]:
    """Returns (html_body, text_body)"""
    # Group by source_category
    from collections import defaultdict
    sections: dict[str, list[SummarizedArticle]] = defaultdict(list)
    for article in articles:
        sections[article.source_category].append(article)

    template = env.get_template("digest.html.j2")
    today = datetime.now().strftime("%B %-d, %Y")
    raw_html = template.render(sections=dict(sections), date=today)
    inlined_html = transform(raw_html)  # Inline all CSS for Gmail

    # Simple plaintext fallback
    text_lines = [f"AI Briefing — {today}\n"]
    for category, arts in sections.items():
        text_lines.append(f"\n{category.upper()}\n{'='*len(category)}")
        for a in arts:
            text_lines.append(f"\n{a.title}\n{a.url}\n{a.summary}\n")
    text_body = "\n".join(text_lines)

    return inlined_html, text_body
```

### Digest Email Template (Minimal Jinja2 Skeleton)

```html
{# templates/digest.html.j2 #}
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <meta name="color-scheme" content="light dark">
  <style>
    /* Dark mode — survives premailer because @media is not inlineable */
    @media (prefers-color-scheme: dark) {
      .email-bg { background-color: #1a1a1a !important; }
      .email-text { color: #e5e5e5 !important; }
      .section-header { color: #a0a0a0 !important; }
    }
    /* Keep style block under 8,192 chars to avoid Gmail truncation */
  </style>
</head>
<body class="email-bg" style="background-color: #f9f9f9; margin: 0; padding: 0;">
  <table width="600" align="center" style="max-width: 600px; margin: 0 auto; padding: 24px;">
    <tr><td>
      <h1 style="font-size: 20px; color: #111; margin-bottom: 4px;">AI Briefing</h1>
      <p style="color: #888; font-size: 14px; margin: 0 0 32px 0;">{{ date }}</p>

      {% for category, articles in sections.items() %}
      {% if articles %}
      <h2 class="section-header" style="font-size: 13px; letter-spacing: 0.08em; text-transform: uppercase; color: #666; border-bottom: 1px solid #e5e5e5; padding-bottom: 8px; margin-top: 32px;">{{ category }}</h2>
      {% for article in articles %}
      <table width="100%" style="margin-bottom: 24px;">
        <tr>
          <td>
            <a href="{{ article.url }}" style="font-size: 16px; font-weight: 600; color: #111; text-decoration: none;">{{ article.title }}</a>
            <p style="font-size: 12px; color: #888; margin: 4px 0 8px 0;">{{ article.source_name }} · {{ article.published_at.strftime('%b %-d') }}</p>
            {% if not article.summarization_failed %}
            <p style="font-size: 14px; color: #333; line-height: 1.6; margin: 0 0 8px 0;">{{ article.summary }}</p>
            <p style="font-size: 13px; color: #555; border-left: 3px solid #ddd; padding-left: 10px; margin: 0; line-height: 1.5;"><strong>Why it matters:</strong> {{ article.why_it_matters }}</p>
            {% else %}
            <p style="font-size: 13px; color: #888; font-style: italic;">Summary unavailable — see article for details.</p>
            {% endif %}
          </td>
        </tr>
      </table>
      {% endfor %}
      {% endif %}
      {% endfor %}

      <p style="font-size: 11px; color: #aaa; margin-top: 40px; border-top: 1px solid #eee; padding-top: 16px;">Generated {{ date }}</p>
    </td></tr>
  </table>
</body>
</html>
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Batch API for summarization | Sequential messages.create() with prompt caching | Phase 1 clarification | Batch API is async (up to 1 hour); sequential + caching achieves same-run results at ~10x lower cost on repeated calls |
| feedparser with naive datetime | feedparser with UTC-aware datetime | Python 3.2+ | Prevents comparison errors; `published_parsed` is already UTC |
| External CSS + `<link>` in email | Inline CSS via premailer | Gmail's CSS stripping (ongoing) | Gmail strips head styles; premailer automates inlining |
| App Password stored in code | App Password in GitHub Secrets | Security baseline | Never hardcode secrets; `os.environ` reads from Actions env |
| Port 587 STARTTLS | Port 465 SSL (SMTP_SSL) | Preference | Both work; 465 is simpler (no explicit starttls() call) |

**Deprecated/outdated:**
- Claude Haiku 3 (`claude-3-haiku-20240307`): Deprecated by Anthropic, retiring April 19, 2026. Use `claude-haiku-4-5-20251001` exclusively.
- Python 3.10 on GitHub Actions: Use Python 3.12 (`python-version: '3.12'` in setup-python@v5) — better performance, available on ubuntu-latest.

---

## Open Questions

1. **The Information RSS-07 authentication requirement**
   - What we know: `https://www.theinformation.com/feed` is listed as a subscriber RSS. It is possible that feedparser can fetch it directly with no auth if the subscriber session cookie is not needed.
   - What's unclear: Whether this feed returns full content, teasers, or a paywall redirect without cookies.
   - Recommendation: Test `feedparser.parse("https://www.theinformation.com/feed")` as the first Phase 1 implementation step. If it returns articles with content — great, no auth needed. If it redirects or returns empty — treat as Phase 2 (cookie-based).

2. **Feed URLs for Ava Huang, Brie Wolfson, Graham Duncan, Justin Meiners, Kevin Kwok, Max Hodak, Nabeel Qureshi**
   - What we know: These bloggers write but their specific feed URLs were not verified in this research pass.
   - What's unclear: Current platform (Substack vs. personal site) and feed URL for each.
   - Recommendation: Build a `FEED_URLS` config dict. Verify each URL by running `feedparser.parse(url)` and checking `feed.entries`. Document verified vs. unverified status. For any blogger not found, log as "feed URL unknown" rather than crashing.

3. **gwern.net/blog/index HTML structure**
   - What we know: Gwern has no RSS. The blog index at gwern.net/blog/index is the correct scraping target.
   - What's unclear: The exact HTML structure, how dates are formatted, whether posts are sorted by date.
   - Recommendation: Inspect the live page and hardcode selectors based on observed structure. Add a comment in the scraper noting the structure was captured on a specific date (since it may change).

4. **Anthropic community RSS feed reliability**
   - What we know: `taobojlen/anthropic-rss-feed` is community-maintained with last build February 24, 2026.
   - What's unclear: Update frequency and how quickly new Anthropic announcements appear in the feed.
   - Recommendation: Implement with fallback scraper of `anthropic.com/news`. If community feed returns 0 articles, scrape directly.

---

## Sources

### Primary (HIGH confidence)
- Anthropic models overview: https://platform.claude.com/docs/en/about-claude/models/overview — `claude-haiku-4-5-20251001` model ID verified March 2026; Haiku 3 deprecation confirmed
- Anthropic Batch Processing API: https://platform.claude.com/docs/en/build-with-claude/batch-processing — "most batches finishing in less than 1 hour," async behavior confirmed; polling pattern verified
- feedparser 6.0.12 PyPI: https://pypi.org/project/feedparser/ — version 6.0.12, released September 10, 2025; `published_parsed` UTC normalization confirmed
- feedparser date parsing docs: https://feedparser.readthedocs.io/en/stable/ — UTC 9-tuple behavior confirmed
- Anthropic Python SDK PyPI: https://pypi.org/project/anthropic/ — version 0.84.0, released February 25, 2026
- Keepalive Workflow GitHub Action: https://github.com/marketplace/actions/keepalive-workflow — confirmed solution for 60-day inactivity

### Secondary (MEDIUM confidence)
- Paul Graham community RSS (Olshansk/pgessays-rss): https://github.com/Olshansk/pgessays-rss — feed URL confirmed, "updated nightly" per README; 556 commits
- Paul Graham feed alternative (filipesilva): https://github.com/filipesilva/paulgraham-rss — alternative feed, `https://filipesilva.github.io/paulgraham-rss/feed.rss`
- Gwern RSS GitHub issue: https://github.com/gwern/gwern.net/issues/11 — confirmed: no native RSS feed, issue open since 2015
- Anthropic community RSS feed: https://github.com/taobojlen/anthropic-rss-feed — last build February 24, 2026; community-maintained
- Scott Alexander ACX: https://astralcodexten.substack.com/ — Substack feed at `https://astralcodexten.substack.com/feed/` confirmed
- Tyler Cowen / Marginal Revolution: https://marginalrevolution.com/ — active blog with daily posts confirmed 2026; standard WordPress RSS
- Henrik Karlsson / Escaping Flatland: https://www.henrikkarlsson.xyz/ — Substack-based publication confirmed
- Calvin French-Owen: https://calv.info/ and https://calvinfo.substack.com/ — personal site + Substack

### Tertiary (LOW confidence)
- Individual feed URLs for Ava Huang, Brie Wolfson, Graham Duncan, Justin Meiners, Kevin Kwok, Max Hodak, Nabeel Qureshi — not individually verified; must be confirmed during implementation
- The Information RSS-07 authentication requirement — unknown until tested in actual GitHub Actions environment

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all library versions verified via PyPI; API model ID verified via official Anthropic docs
- Architecture: HIGH — linear pipeline pattern is standard for this class of tool; all patterns derived from official library documentation
- Summarization approach: HIGH — Batch API async behavior confirmed via official docs; sequential + caching approach resolves ARCHITECTURE.md/STACK.md conflict definitively
- Pitfalls: MEDIUM-HIGH — GitHub inactivity rule confirmed via official docs; Gmail CSS behavior confirmed; Paul Graham/Gwern feed status confirmed via primary sources
- Feed URLs: MEDIUM — only highest-traffic blogs individually verified; personal bloggers require verification during implementation

**Research date:** 2026-03-01
**Valid until:** 2026-04-01 (stable libraries; Anthropic model IDs may change if new Haiku releases)

**Key conflict resolved:** ARCHITECTURE.md recommends Batch API for summarization. STACK.md recommends sequential calls. Official Batch API docs confirm async processing (up to 1 hour). With a 30-minute Actions timeout, Batch API polling will fail. Use sequential `client.messages.create()` with `cache_control: ephemeral` on system prompt. This is faster to implement, synchronous within one run, and achieves ~90% cost reduction on the system prompt via prompt caching.
