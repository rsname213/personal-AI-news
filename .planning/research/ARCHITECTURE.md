# Architecture Patterns: Personal AI News Newsletter

**Domain:** Personal daily digest / newsletter automation pipeline
**Researched:** 2026-03-01
**Confidence:** HIGH (Claude Batch API from official docs; GitHub Actions patterns from official docs + community verification; email HTML from multiple verified sources; Python scraping from well-established libraries)

---

## Recommended Architecture

This is a stateless, single-run pipeline executed on a schedule. No database, no persistent server, no user state. Each run is hermetic: fetch → filter → summarize → render → send.

```
GitHub Actions Cron (12:00 UTC / 7am ET)
        |
        v
  [orchestrator.py]          # Main entry point — drives all stages
        |
   +---------+--------+-----------+----------+
   |         |        |           |          |
[rss.py] [wsj.py] [theinfo.py] [anthropic.py] [render.py]
   |         |        |           |          |
   +---------+--------+-----------+          |
        |                                    |
   [filter.py]  <-- 24h window, 5-item cap  |
        |                                    |
   [summarize.py]  <-- Claude Batch API -----+
        |
   [render.py]  <-- Jinja2 + inline CSS
        |
   [send.py]  <-- smtplib, Gmail SMTP
```

---

## Component Boundaries

| Component | File | Responsibility | Input | Output | Communicates With |
|-----------|------|---------------|-------|--------|-------------------|
| Orchestrator | `orchestrator.py` | Drives pipeline, handles top-level failures, collects partial results | env vars / secrets | exit code 0/1 | All components |
| RSS Fetcher | `fetchers/rss.py` | Fetches 20 personal blogs via feedparser | List of feed URLs | List of `RawArticle` objects | Filter |
| WSJ Fetcher | `fetchers/wsj.py` | Authenticated cookie scraping of WSJ | Cookie string (from env) | List of `RawArticle` objects | Filter |
| The Information Fetcher | `fetchers/theinfo.py` | Authenticated cookie scraping of The Information | Cookie string (from env) | List of `RawArticle` objects | Filter |
| Anthropic Fetcher | `fetchers/anthropic_blog.py` | RSS or HTML scrape of Anthropic news | Feed URL | List of `RawArticle` objects | Filter |
| Filter | `pipeline/filter.py` | Enforces 24h recency window, 5-item-per-source cap | List of `RawArticle` | List of `FilteredArticle` | Summarizer |
| Summarizer | `pipeline/summarize.py` | Submits all articles to Claude Batch API, polls for results | List of `FilteredArticle` | List of `SummarizedArticle` | Renderer |
| Renderer | `pipeline/render.py` | Produces final HTML email from Jinja2 template | List of `SummarizedArticle` | HTML string | Sender |
| Sender | `pipeline/send.py` | Sends HTML email via Gmail SMTP (smtplib) | HTML string | None (side effect) | External: Gmail SMTP |

---

## Data Flow

```
Stage 1 — FETCH (parallel per source)
  Each fetcher runs independently.
  Returns: List[RawArticle] or empty list on failure.
  RawArticle fields: {url, title, published_at, content_text, source_name, source_type}

  +--> rss.py         -> [RawArticle, ...]     # Up to 20 sources
  +--> wsj.py         -> [RawArticle, ...]     # Up to 5 items
  +--> theinfo.py     -> [RawArticle, ...]     # Up to 5 items
  +--> anthropic_blog -> [RawArticle, ...]     # Uncapped (small volume)

Stage 2 — FILTER
  All RawArticle lists merged.
  filter.py applies:
    - 24h recency cutoff (published_at >= now() - 24h)
    - Per-source cap: top 5 by recency
  Returns: List[FilteredArticle]
  FilteredArticle fields: same as RawArticle + {included: bool, reason: str}

Stage 3 — SUMMARIZE
  summarize.py bundles all FilteredArticles into a single Claude Batch API call.
  Each article = one request in the batch, keyed by custom_id = article URL hash.
  Prompt per article: "Summarize this article (2-3 sentences). Then write 'Why it matters:' (1-2 sentences)."
  Polls until batch status == "ended" (sleep 30s between polls, max 20 polls = 10 min).
  Returns: List[SummarizedArticle]
  SummarizedArticle fields: FilteredArticle + {summary: str, why_it_matters: str}

Stage 4 — RENDER
  render.py loads Jinja2 template.
  Groups articles by source_name.
  Renders to full HTML string with inline CSS (using premailer or manual inlining).
  Returns: str (HTML)

Stage 5 — SEND
  send.py connects to smtp.gmail.com:587 with STARTTLS.
  Authenticates with GMAIL_USER + GMAIL_APP_PASSWORD secrets.
  Sends MIMEMultipart message: plain text fallback + HTML part.
  Logs success or raises exception.
```

---

## GitHub Actions Job Structure

Use a **single job with sequential steps** — not multiple jobs. This avoids artifact passing overhead for a single-user pipeline this size.

```yaml
name: Daily AI Newsletter

on:
  schedule:
    - cron: '0 12 * * *'     # 12:00 UTC = 7:00 AM ET (winter). Adjust to 11:00 UTC for summer.
  workflow_dispatch:           # Manual trigger for testing

jobs:
  run-newsletter:
    runs-on: ubuntu-latest
    timeout-minutes: 30        # Hard cap — batch processing should finish well within this

    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.12'
          cache: 'pip'

      - name: Install dependencies
        run: pip install -r requirements.txt

      - name: Fetch, summarize, render and send newsletter
        env:
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
          GMAIL_USER: ${{ secrets.GMAIL_USER }}
          GMAIL_APP_PASSWORD: ${{ secrets.GMAIL_APP_PASSWORD }}
          WSJ_COOKIES: ${{ secrets.WSJ_COOKIES }}
          THE_INFORMATION_COOKIES: ${{ secrets.THE_INFORMATION_COOKIES }}
          RECIPIENT_EMAIL: ${{ secrets.RECIPIENT_EMAIL }}
        run: python orchestrator.py
```

**Key decisions:**
- `workflow_dispatch` is mandatory — it allows manual test runs without waiting for the cron schedule.
- `timeout-minutes: 30` prevents runaway runs if the Claude Batch API is slow.
- All secrets are injected as environment variables — Python reads them with `os.environ`.
- `cache: 'pip'` reduces install time on repeated runs.

---

## Secrets Management

All sensitive values stored as GitHub Repository Secrets (Settings > Secrets and variables > Actions).

| Secret Name | What It Stores | How Used |
|-------------|----------------|----------|
| `ANTHROPIC_API_KEY` | Claude API key | `os.environ["ANTHROPIC_API_KEY"]` in summarize.py |
| `GMAIL_USER` | Gmail address (e.g. you@gmail.com) | SMTP login in send.py |
| `GMAIL_APP_PASSWORD` | 16-char Gmail App Password | SMTP auth in send.py |
| `RECIPIENT_EMAIL` | Destination email address | To: header in send.py |
| `WSJ_COOKIES` | Cookie header string for WSJ authenticated session | requests.Session cookie injection in wsj.py |
| `THE_INFORMATION_COOKIES` | Cookie header string for The Information session | requests.Session cookie injection in theinfo.py |

**Cookie storage pattern:**
Store the full `Cookie:` header value as a single string in the secret. In Python:
```python
import os, requests

session = requests.Session()
session.headers.update({
    "Cookie": os.environ["WSJ_COOKIES"],
    "User-Agent": "Mozilla/5.0 ...",
})
```

**Cookie rotation concern:** Browser session cookies for paywalled sites expire. The WSJ_COOKIES and THE_INFORMATION_COOKIES secrets must be manually refreshed when sessions expire (typically every 30-90 days). Build the WSJ/TheInfo fetchers to detect a 401/403/redirect response and return empty list with a logged warning — never crash the run.

---

## Error Handling: Graceful Degradation

**Principle:** A failed source returns an empty list, never an exception. The orchestrator always produces an email, even if some sections are empty or say "No content available today."

```python
# orchestrator.py — collect partial results
sources = []

for fetcher_fn, source_name in FETCHERS:
    try:
        articles = fetcher_fn()
        sources.extend(articles)
    except Exception as e:
        print(f"[WARN] {source_name} fetch failed: {e}")
        # Continue — partial email is better than no email

filtered = filter_articles(sources)

if not filtered:
    send_email(render_empty_digest())   # Send "Nothing new today" message
    sys.exit(0)

summarized = summarize_with_claude(filtered)
html = render(summarized)
send_email(html)
```

**Source-level failure modes and responses:**

| Failure Mode | Response |
|---|---|
| RSS feed unreachable (timeout, DNS) | Return `[]`, log warning, continue |
| RSS feed returns malformed XML | feedparser handles gracefully; returns partial results |
| WSJ/TheInfo cookies expired (401/403) | Return `[]`, log "cookie may be expired", continue |
| WSJ/TheInfo rate-limited (429) | Return `[]`, log warning, do not retry (single daily run) |
| Claude Batch API times out (24h limit) | Fall back to sequential Messages API calls with exponential backoff, max 3 retries per article |
| Claude Batch API returns `errored` result for one article | Skip that article, include the rest |
| Gmail SMTP fails | Raise exception — email delivery is the final output, a hard failure is appropriate here |

**Empty section handling:** The Jinja2 template should render each source section conditionally. If a section has zero articles, show a subtle "No new content from [Source] today" line rather than omitting the section entirely — helps diagnose cookie expiry.

---

## Claude API Call Patterns

**Use the Message Batches API, not sequential Messages API calls.** With 20 RSS sources (up to 5 articles each) + WSJ (5) + The Information (5) + Anthropic blog (variable), a run may have up to 115 articles. Sequential API calls at ~1-2s each would take 2-4 minutes and consume rate limit quota. The Batch API handles all of these in parallel at 50% cost.

**Batch architecture:**
```python
import anthropic
from anthropic.types.message_create_params import MessageCreateParamsNonStreaming
from anthropic.types.messages.batch_create_params import Request

client = anthropic.Anthropic()

SUMMARIZE_SYSTEM_PROMPT = """You are a news briefing assistant.
For each article, write:
1. A 2-3 sentence summary (neutral, factual)
2. "Why it matters:" followed by 1-2 sentences on significance for AI/tech professionals.
Be concise. No preamble."""

def build_batch_requests(articles: list[FilteredArticle]) -> list[Request]:
    return [
        Request(
            custom_id=article.id,   # stable hash of URL
            params=MessageCreateParamsNonStreaming(
                model="claude-haiku-4-5",   # Fast, cheap — summarization doesn't need Opus
                max_tokens=300,
                system=SUMMARIZE_SYSTEM_PROMPT,
                messages=[{
                    "role": "user",
                    "content": f"Title: {article.title}\n\nContent:\n{article.content_text[:3000]}"
                }]
            )
        )
        for article in articles
    ]

def poll_until_complete(batch_id: str, max_polls: int = 20, interval_s: int = 30):
    import time
    for _ in range(max_polls):
        batch = client.messages.batches.retrieve(batch_id)
        if batch.processing_status == "ended":
            return batch
        time.sleep(interval_s)
    raise TimeoutError(f"Batch {batch_id} did not complete in {max_polls * interval_s}s")
```

**Model choice for summarization:** Use `claude-haiku-4-5` (Batch price: $0.125/MTok input, $0.625/MTok output). Summarization is a straightforward task that does not require Opus-class reasoning. At 115 articles x ~800 input tokens + ~300 output tokens: estimated cost is under $0.05 per daily run.

**Content truncation:** Truncate each article's content to 3,000 characters before sending to the API. This is sufficient for meaningful summarization and prevents oversized batch requests.

**Custom ID mapping:** Use a stable hash of the article URL as `custom_id`. Batch results return in arbitrary order — the `custom_id` is the only way to match results back to articles.

---

## HTML Email Template Architecture

**Template engine:** Jinja2. Renders a single `digest.html.j2` template file.

**CSS strategy:** Hybrid approach — inline critical styles (font, color, padding, width) directly in HTML attributes/style tags; use a `<head>` `<style>` block for dark mode (`@media (prefers-color-scheme: dark)`) and responsive overrides.

**Inlining tool:** Use `premailer` (Python library) to automatically inline all `<style>` block CSS into element `style=""` attributes before sending. This ensures compatibility with Gmail Web which strips `<head>` styles.

```
Template structure: digest.html.j2
  <html>
    <head>
      <meta name="color-scheme" content="light dark">
      <meta name="supported-color-schemes" content="light dark">
      <style>
        /* Dark mode overrides */
        @media (prefers-color-scheme: dark) {
          .email-body { background-color: #1a1a1a !important; }
          .text-primary { color: #e5e5e5 !important; }
          /* etc. */
        }
        /* Responsive */
        @media only screen and (max-width: 600px) {
          .email-container { width: 100% !important; }
        }
      </style>
    </head>
    <body>
      <table width="600" align="center" class="email-container">
        <!-- Header: date + "Your Daily AI Briefing" -->
        <!-- For each source section: -->
          <!-- Source name header -->
          <!-- For each article: -->
            <!-- Title (linked) -->
            <!-- Summary paragraph -->
            <!-- "Why it matters:" callout block -->
          <!-- End for -->
        <!-- End for -->
        <!-- Footer: unsubscribe note, generation timestamp -->
      </table>
    </body>
  </html>
```

**Width:** 600px fixed container, fluid inner content. No `max-width` tricks needed for this personal use case.

**Dark mode:** Use `@media (prefers-color-scheme: dark)` in `<head>` style block. Apple Mail (48-53% market share) fully supports this. Gmail mobile supports it. Gmail desktop does not — acceptable degradation for a personal newsletter.

**Email size limit:** Keep total HTML under 100KB including all content. With 100 articles at ~300 chars each + template overhead, this is comfortably achievable.

---

## File Structure (Suggested)

```
/
├── orchestrator.py              # Entry point
├── requirements.txt
├── .github/
│   └── workflows/
│       └── daily-newsletter.yml
├── fetchers/
│   ├── __init__.py
│   ├── rss.py                   # feedparser-based, handles all 20 RSS sources
│   ├── wsj.py                   # requests.Session with cookie injection
│   ├── theinfo.py               # requests.Session with cookie injection
│   └── anthropic_blog.py        # RSS or HTML scrape
├── pipeline/
│   ├── __init__.py
│   ├── filter.py                # 24h cutoff + per-source cap
│   ├── summarize.py             # Claude Batch API
│   ├── render.py                # Jinja2 + premailer
│   └── send.py                  # smtplib SMTP
├── templates/
│   └── digest.html.j2           # Main email template
└── models.py                    # RawArticle, FilteredArticle, SummarizedArticle dataclasses
```

---

## Patterns to Follow

### Pattern 1: Source Isolation with Fail-Soft Collection
**What:** Each fetcher is an independent function returning `List[RawArticle]`. All failures are caught at the orchestrator level, never propagated.
**When:** Always. A single broken RSS feed or expired cookie must never block delivery.
**Example:**
```python
def collect_all(fetchers) -> List[RawArticle]:
    results = []
    for name, fn in fetchers:
        try:
            articles = fn()
            results.extend(articles)
            print(f"[OK] {name}: {len(articles)} articles")
        except Exception as e:
            print(f"[WARN] {name}: {e}")
    return results
```

### Pattern 2: Typed Data Model with Dataclasses
**What:** Use Python `@dataclass` for `RawArticle`, `FilteredArticle`, `SummarizedArticle`. Each stage receives the previous stage's type and returns the next.
**When:** Always. Prevents silent data corruption between stages.
```python
from dataclasses import dataclass
from datetime import datetime

@dataclass
class RawArticle:
    id: str               # hash of URL
    url: str
    title: str
    content_text: str
    published_at: datetime
    source_name: str

@dataclass
class SummarizedArticle(RawArticle):
    summary: str
    why_it_matters: str
```

### Pattern 3: Batch-then-Map for Claude API
**What:** Submit all articles in one batch call. Poll for completion. Map results back to articles using `custom_id`.
**When:** Whenever you have 5+ articles to summarize. Sequential calls are slow and waste quota.

### Pattern 4: Cookie String Injection via Environment Variable
**What:** Store the full `Cookie:` header value as a single GitHub Secret. Inject into `requests.Session` headers directly.
**When:** For WSJ and The Information authenticated access.
**Note:** Add a cookie validity check on session construction — if the first request redirects to a login page, log a clear warning and return empty list.

---

## Anti-Patterns to Avoid

### Anti-Pattern 1: Sequential Claude API Calls per Article
**What:** Calling `client.messages.create()` once per article in a loop.
**Why bad:** 100 articles x 1-2s per call = 2-3 minutes, hits rate limits, wastes quota at 2x the batch price.
**Instead:** Bundle all articles into a single Batch API call.

### Anti-Pattern 2: Crashing on Source Failure
**What:** Letting a `requests.exceptions.ConnectionError` from one RSS feed propagate to the top level.
**Why bad:** One bad blog URL stops the entire newsletter from sending.
**Instead:** Wrap each fetcher call in try/except, return empty list on any exception.

### Anti-Pattern 3: Using External CSS Files or `<link>` Tags in Email
**What:** Referencing a stylesheet via `<link rel="stylesheet">`.
**Why bad:** Email clients strip external stylesheets. Gmail strips `<head>` styles. Styles silently disappear.
**Instead:** Inline all critical styles. Use `premailer` to automate this.

### Anti-Pattern 4: Storing Cookie Values in Code or Config Files
**What:** Hardcoding cookie strings in `config.json` or source files committed to git.
**Why bad:** Exposes subscriber credentials in git history. Repository is public.
**Instead:** Store only in GitHub Secrets, access via `os.environ`.

### Anti-Pattern 5: Fetching Full Article Content for All Sources
**What:** Following every link and scraping the full page for all 20 RSS blogs.
**Why bad:** Many personal blogs have no stable HTML structure; rate limiting; significant added complexity.
**Instead:** Use RSS feed content as-is. Most personal blogs include full post content in their RSS feeds. For those that do not, use the feed excerpt only — it is still sufficient for summarization.

---

## Suggested Build Order

Build in dependency order — each stage must work before the next can be tested.

```
Phase 1: Foundation
  models.py          <- Defines data types used everywhere
  pipeline/filter.py <- Pure Python, no external dependencies, testable immediately
  pipeline/send.py   <- Proves Gmail SMTP works; can test with hardcoded HTML
  Deliverable: Can send a hardcoded test email to yourself

Phase 2: Content Sources
  fetchers/rss.py           <- feedparser; feeds the bulk of content
  fetchers/anthropic_blog.py <- RSS; simple, no auth
  Deliverable: Can print a list of today's articles to stdout

Phase 3: Paid Sources (authenticated)
  fetchers/wsj.py      <- Cookie auth pattern; highest complexity
  fetchers/theinfo.py  <- Same pattern as WSJ
  Deliverable: Can print WSJ + TheInfo headlines with cookie auth

Phase 4: Summarization
  pipeline/summarize.py <- Claude Batch API; needs real API key
  Deliverable: Can submit batch, poll for completion, print summaries

Phase 5: Rendering
  templates/digest.html.j2 <- Jinja2 template with CSS
  pipeline/render.py       <- Jinja2 rendering + premailer inlining
  Deliverable: Can generate a full HTML email and open it in a browser

Phase 6: Orchestration and CI
  orchestrator.py              <- Wires all stages, handles graceful degradation
  .github/workflows/daily.yml  <- Cron job, secrets injection
  Deliverable: Full automated end-to-end run in GitHub Actions
```

**Build order rationale:**
- `models.py` first because all other modules import from it
- `filter.py` before fetchers because it has no external dependencies and lets you validate logic with mock data
- `send.py` early because it validates the critical delivery mechanism — if Gmail rejects the App Password, you want to know before building 5 fetchers
- RSS fetchers before WSJ/TheInfo because they need no authentication and will deliver the most content
- Summarization before rendering because you need real summaries to validate the template looks right
- Orchestrator last because it integrates all prior stages

---

## Scalability Considerations

This is intentionally a personal tool. Scalability is not a concern. The constraints that matter at this scale:

| Concern | At 1 user (current) | Implication |
|---------|---------------------|-------------|
| Claude API cost | ~$0.05/day | Use Haiku, batch API — negligible |
| GitHub Actions minutes | ~3-5 min/day | Well within free tier (2,000 min/month) |
| Email deliverability | Gmail sending to Gmail | No SPF/DKIM issues; no spam risk |
| Cookie freshness | Manual rotation every 30-90 days | Build clear "cookie expired" log message |
| Batch API timeout | Most batches finish in <1 hour | 30 min job timeout is safe |

---

## Sources

- Claude Batch Processing API (official): https://platform.claude.com/docs/en/build-with-claude/batch-processing [HIGH confidence]
- Claude API Rate Limits (official): https://platform.claude.com/docs/en/api/rate-limits [HIGH confidence]
- GitHub Actions Cron Scheduling (verified, multiple sources): https://cicube.io/blog/github-actions-cron/ [MEDIUM confidence]
- Python Gmail SMTP via GitHub Actions: https://www.paulie.dev/posts/2025/02/how-to-send-email-using-github-actions/ [MEDIUM confidence]
- HTML Email Dark Mode Best Practices (2026): https://www.enchantagency.com/blog/dark-mode-email-design-best-practices-css-guide-2026 [MEDIUM confidence]
- Email Rendering Differences Guide (2026): https://dev.to/aoifecarrigan/the-complete-guide-to-email-client-rendering-differences-in-2026-243f [MEDIUM confidence]
- Python feedparser library: https://pypi.org/project/feedparser/ [HIGH confidence]
- Python requests.Session cookie handling: https://proxiesapi.com/articles/mastering-sessions-cookies-with-python-requests [MEDIUM confidence]
- Graceful Degradation Patterns: https://docs.aws.amazon.com/wellarchitected/latest/reliability-pillar/rel_mitigate_interaction_failure_graceful_degradation.html [HIGH confidence]
