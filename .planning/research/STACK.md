# Technology Stack

**Project:** Personal AI News Newsletter
**Researched:** 2026-03-01
**Research mode:** Ecosystem (Stack dimension)

---

## Recommended Stack

### Python Runtime

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| Python | 3.12 | Runtime | LTS release available on GitHub Actions `ubuntu-latest`; best performance and stdlib improvements; actions/setup-python supports it natively |

Use `python-version: '3.12'` in GitHub Actions setup. Pin to `3.12` not `3.x` to prevent surprises across runs.

---

### RSS Feed Parsing

| Library | Version | Purpose | Why |
|---------|---------|---------|-----|
| feedparser | 6.0.12 | Parse RSS/Atom feeds from 20 personal blogs + Anthropic | The definitive Python RSS library. Auto-detects feed format (RSS 0.9x/1.0/2.0, Atom 0.3/1.0, RDF). Normalizes divergent feed structures into a consistent dict interface. Handles malformed XML and missing fields — critical because personal blogs like gwern.net and paulgraham.com have nonstandard feeds. Released September 10, 2025. |

**Do not use:** `xml.etree.ElementTree` directly — you'd re-implement feedparser's normalization logic across 20+ different feed formats. Not worth it.

**Do not use:** `atoma` or `listparser` — smaller ecosystems, less battle-tested against real-world malformed feeds.

**Pattern for 24-hour filtering:**
```python
import feedparser
from datetime import datetime, timezone, timedelta

def fetch_recent_entries(feed_url: str, hours: int = 24) -> list[dict]:
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    feed = feedparser.parse(feed_url)
    return [
        entry for entry in feed.entries
        if hasattr(entry, 'published_parsed')
        and entry.published_parsed is not None
        and datetime(*entry.published_parsed[:6], tzinfo=timezone.utc) >= cutoff
    ]
```

**Important:** `entry.published_parsed` is a `time.struct_time` — convert to `datetime` for comparison. Some feeds omit dates; handle gracefully.

---

### Authenticated HTTP Scraping (WSJ + The Information)

| Library | Version | Purpose | Why |
|---------|---------|---------|-----|
| httpx | 0.28.1 | Authenticated HTTP requests with stored cookies | Modern successor to `requests`. Sync API identical to `requests` (minimal learning curve). Built-in cookie jar, session management, and HTTP/2 support. Cleaner than `requests` for cookie dict injection. |
| playwright | 1.58.0 | Fallback for JS-rendered paywall content | WSJ and The Information use JavaScript-heavy article pages. If cookie-based `httpx` requests return gated content (soft-paywall JS check), Playwright with stored cookies renders the full DOM. Released January 30, 2026. |

**Primary approach — httpx with serialized cookies:**

Store cookies as a JSON string in GitHub Secret `WSJ_COOKIES` and `THE_INFORMATION_COOKIES`. At runtime, deserialize and inject:

```python
import httpx
import json
import os

def scrape_with_cookies(url: str, cookies_json: str) -> str:
    cookies = json.loads(cookies_json)
    # cookies is a list of {name, value, domain, path, ...} dicts
    cookie_dict = {c["name"]: c["value"] for c in cookies}
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                      "AppleWebKit/537.36 (KHTML, like Gecko) "
                      "Chrome/121.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }
    with httpx.Client(cookies=cookie_dict, headers=headers, follow_redirects=True) as client:
        response = client.get(url, timeout=30)
        return response.text
```

**How to obtain cookies for GitHub Secret:**
1. Log in to WSJ/The Information in Chrome
2. Open DevTools > Application > Cookies
3. Export via EditThisCookie extension or copy as JSON
4. Paste JSON into GitHub Secret

**Fallback — Playwright for JS-gated content:**

Use only if `httpx` returns a paywall wall or redirect. Playwright adds ~2 minutes to install browsers on GitHub Actions (mitigate with caching).

```python
from playwright.sync_api import sync_playwright
import json

def scrape_playwright_with_cookies(url: str, cookies_json: str) -> str:
    cookies = json.loads(cookies_json)
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        context.add_cookies(cookies)
        page = context.new_page()
        page.goto(url, timeout=30000)
        page.wait_for_load_state("networkidle")
        content = page.content()
        browser.close()
    return content
```

**GitHub Actions — cache Playwright browsers to avoid 2-min install penalty:**
```yaml
- name: Cache Playwright browsers
  uses: actions/cache@v4
  with:
    path: ~/.cache/ms-playwright
    key: playwright-${{ hashFiles('requirements.txt') }}
- run: playwright install chromium --with-deps
```

**MEDIUM confidence** on cookie-based WSJ scraping working reliably. WSJ uses sophisticated anti-bot detection (TLS fingerprinting, behavioral analysis). If `httpx` is consistently blocked, switch entirely to Playwright with `playwright-extra` stealth plugin (LOW confidence on long-term viability — sites actively update defenses).

**Legal note:** The project owner has valid subscriptions. This approach uses authenticated sessions, not paywall bypass. Still, WSJ ToS prohibits automated access — owner accepts this risk for personal use.

---

### HTML Parsing (Article Content Extraction)

| Library | Version | Purpose | Why |
|---------|---------|---------|-----|
| beautifulsoup4 | 4.14.3 | Parse scraped HTML, extract article body text | Standard for HTML parsing in Python. Released November 30, 2025. |
| lxml | latest stable | Parser backend for BeautifulSoup | Fastest BS4 parser; handles malformed HTML well. Required by premailer for CSS parsing too — a single dependency serving two purposes. |

```python
from bs4 import BeautifulSoup

def extract_article_text(html: str) -> str:
    soup = BeautifulSoup(html, "lxml")
    # Remove nav, ads, scripts
    for tag in soup(["script", "style", "nav", "header", "footer", "aside"]):
        tag.decompose()
    # Extract main content
    article = soup.find("article") or soup.find(class_=["article-body", "entry-content"])
    if article:
        return article.get_text(separator="\n", strip=True)
    return soup.get_text(separator="\n", strip=True)
```

---

### AI Summarization

| Library | Version | Purpose | Why |
|---------|---------|---------|-----|
| anthropic | 0.84.0 | Claude API for article summarization | Official SDK. Released February 25, 2026. Requires Python 3.9+. Type-safe, handles retries, streaming, and prompt caching. |

**Recommended model: `claude-haiku-4-5`** (API ID: `claude-haiku-4-5-20251001`)

Rationale:
- At $1/$5 per million input/output tokens, summarizing ~30 articles/day costs approximately **$0.01–0.05/day** — negligible
- Haiku 4.5 is the fastest model — suitable for sequential summarization of 30 items without hitting execution time limits
- Quality sufficient for 2–3 paragraph article summaries; no need for Sonnet/Opus reasoning depth

**Do not use:** `claude-sonnet-4-6` for this task — 3x more expensive with no quality gain for straightforward summarization. Reserve Sonnet/Opus for tasks requiring deep reasoning.

**Do not use:** Batch API (`client.beta.messages.batches`) for this pipeline. Batch API is asynchronous (results available after processing, up to 24 hours). This pipeline needs results synchronously within a single GitHub Actions run. Use sequential `client.messages.create()` calls instead.

**Prompt caching opportunity:** The system prompt (summarization instructions) repeats for every article. Mark it with `cache_control` to get 90% discount on repeated tokens after the first call:

```python
import anthropic
import os

client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

SYSTEM_PROMPT = """You are a concise AI/tech newsletter editor. For each article, write:
1. SUMMARY: 2-3 sentences explaining what the article covers
2. WHY IT MATTERS: 1-2 sentences on relevance to AI practitioners

Be direct and specific. No filler phrases. No "the author argues" constructions."""

def summarize_article(title: str, content: str) -> dict:
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
        messages=[
            {
                "role": "user",
                "content": f"Title: {title}\n\nContent:\n{content[:3000]}"
            }
        ],
    )
    return {"summary": response.content[0].text}
```

The `cache_control: ephemeral` on the system prompt caches it for 5 minutes — more than sufficient for sequential calls in a single run. First call: slight premium (1.25x); subsequent ~29 calls: 0.1x cost.

---

### HTML Email Rendering

| Library | Version | Purpose | Why |
|---------|---------|---------|-----|
| Jinja2 | 3.1.6 | HTML email template rendering | Industry standard for Python templating. Released March 5, 2025. Template inheritance, loops, conditionals — all needed for iterating article sections. Already in most Python environments. |
| premailer | 3.10.0 | CSS inlining for email client compatibility | Email clients (Gmail web, Outlook) strip `<style>` blocks and ignore class-based CSS. Premailer converts CSS rules to inline `style=""` attributes on each element. Essential for Wispr Flow-styled design to survive Gmail rendering. |

**Do not use:** `mjml` — requires Node.js, adds a non-Python dependency to the pipeline for no benefit over Jinja2+premailer.

**Do not use:** `html2text` — wrong direction (HTML to text); we're building HTML.

**Template structure:**
```
templates/
  base_email.html          # Master layout: header, footer, unsubscribe
  sections/
    rss_section.html       # Personal bloggers section
    paywalled_section.html # WSJ / The Information section
    anthropic_section.html # Anthropic updates section
  components/
    article_card.html      # Individual article summary card
```

**Rendering pipeline:**
```python
from jinja2 import Environment, FileSystemLoader
from premailer import transform

env = Environment(
    loader=FileSystemLoader("templates"),
    autoescape=True,
)

def render_email(articles_by_section: dict) -> str:
    template = env.get_template("base_email.html")
    raw_html = template.render(sections=articles_by_section, date=today)
    return transform(raw_html)  # Inline CSS
```

**Outlook compatibility:** Use table-based layouts in the HTML template (not flexbox/grid). Premailer handles CSS inlining but cannot fix unsupported CSS properties. Wispr Flow's minimal aesthetic (clean sans-serif, generous whitespace) translates well to table-based email HTML.

---

### Email Delivery

| Mechanism | Version | Purpose | Why |
|-----------|---------|---------|-----|
| smtplib | stdlib | Send HTML email via Gmail SMTP | Built into Python — zero additional dependency. Sufficient for single-recipient personal newsletter. |
| email.mime | stdlib | Construct MIME messages | Built into Python. `MIMEMultipart('alternative')` with plain-text fallback and HTML body is the correct RFC-compliant structure. |

**Gmail SMTP configuration:**
- Server: `smtp.gmail.com`
- Port: 465 (SSL) — preferred over 587 (STARTTLS) for simplicity
- Auth: Gmail App Password (16-digit, stored as `GMAIL_APP_PASSWORD` GitHub Secret)
- Prerequisite: Gmail account must have 2-Step Verification enabled

**Do not use:** SendGrid, Mailgun, or other transactional email services. This is a personal pipeline with 1 recipient/day — overkill and adds cost + API key management overhead.

**Do not use:** Google OAuth2/Gmail API — far more complex setup (OAuth flow, token refresh) with no benefit over App Password for this use case.

```python
import smtplib
import ssl
import os
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

def send_email(subject: str, html_body: str, text_body: str) -> None:
    gmail_user = os.environ["GMAIL_USER"]
    gmail_password = os.environ["GMAIL_APP_PASSWORD"]
    recipient = os.environ.get("RECIPIENT_EMAIL", gmail_user)

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = gmail_user
    msg["To"] = recipient
    msg.attach(MIMEText(text_body, "plain"))
    msg.attach(MIMEText(html_body, "html"))

    context = ssl.create_default_context()
    with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context) as server:
        server.login(gmail_user, gmail_password)
        server.sendmail(gmail_user, recipient, msg.as_string())
```

---

### GitHub Actions (Orchestration)

| Component | Value | Why |
|-----------|-------|-----|
| Trigger | `schedule: cron: '0 12 * * *'` | 12:00 UTC = 7:00 AM EST (UTC-5, winter). For EDT (UTC-4, summer), use `'0 11 * * *'`. GitHub Actions has no timezone support — use UTC arithmetic. |
| Also include | `workflow_dispatch` | Enables manual testing without waiting for schedule |
| Runner | `ubuntu-latest` | Standard, free, includes Python toolchain |
| Python setup | `actions/setup-python@v5` with `cache: 'pip'` | Built-in pip caching keyed to `requirements.txt` hash; avoids re-downloading deps on every run |
| Secrets access | `env:` block in workflow step | Map secrets to env vars, read via `os.environ` in Python |

**DST handling:** GitHub has no timezone-aware scheduling. Two options:
1. Pick a time that works acceptably in both EST and EDT (e.g., 12:00 UTC = 7am EST / 8am EDT — both acceptable for a morning briefing)
2. Use two cron entries and let the Python script check whether to run (adds complexity — not recommended)

**Recommended:** Use `'0 12 * * *'` year-round. The email arrives at 7am EST in winter, 8am EDT in summer. Both within the desired 7–8am window.

**Workflow skeleton:**
```yaml
name: Daily AI Newsletter

on:
  schedule:
    - cron: '0 12 * * *'
  workflow_dispatch:

jobs:
  send-newsletter:
    runs-on: ubuntu-latest
    timeout-minutes: 30

    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'
          cache: 'pip'

      - name: Install dependencies
        run: pip install -r requirements.txt

      - name: Install Playwright browsers
        run: playwright install chromium --with-deps

      - name: Run newsletter pipeline
        env:
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
          GMAIL_USER: ${{ secrets.GMAIL_USER }}
          GMAIL_APP_PASSWORD: ${{ secrets.GMAIL_APP_PASSWORD }}
          WSJ_COOKIES: ${{ secrets.WSJ_COOKIES }}
          THE_INFORMATION_COOKIES: ${{ secrets.THE_INFORMATION_COOKIES }}
          RECIPIENT_EMAIL: ${{ secrets.RECIPIENT_EMAIL }}
        run: python main.py
```

**Job timeout:** Set `timeout-minutes: 30`. A full run (20 RSS feeds + 2 scrapes + 30 Claude calls + email send) should complete in 5–10 minutes. 30-minute timeout prevents runaway jobs consuming Actions minutes.

---

## Complete requirements.txt

```
# RSS parsing
feedparser==6.0.12

# HTTP client for authenticated scraping
httpx==0.28.1

# Browser automation (paywall fallback)
playwright==1.58.0

# HTML parsing / content extraction
beautifulsoup4==4.14.3
lxml>=5.0.0

# AI summarization
anthropic==0.84.0

# Email HTML templating
Jinja2==3.1.6
premailer==3.10.0

# CSS parsing (premailer dependency)
cssutils>=2.9.0
cssselect>=1.2.0
```

**No separate async library needed.** All operations are I/O-bound but low-concurrency (20 feeds, 2 scrapes, ~30 API calls). Synchronous sequential execution is simple and sufficient. If feed fetching becomes a bottleneck, use `concurrent.futures.ThreadPoolExecutor` with `feedparser.parse` — feedparser is thread-safe.

---

## Alternatives Considered

| Category | Recommended | Alternative | Why Not |
|----------|-------------|-------------|---------|
| RSS parsing | feedparser 6.0.12 | atoma, listparser | Smaller ecosystems; feedparser normalizes 20 different feed formats automatically |
| RSS parsing | feedparser 6.0.12 | Raw xml.etree | Re-implements normalization; fragile against malformed feeds |
| HTTP client | httpx 0.28.1 | requests | httpx has cleaner cookie dict injection; async-capable if needed later |
| Paywall scraping | httpx + Playwright | Selenium | Playwright has faster startup, better Python API, better headless support; Selenium is legacy |
| AI model | claude-haiku-4-5 | claude-sonnet-4-6 | Haiku is 3x cheaper; quality sufficient for summarization; Sonnet/Opus reserved for reasoning tasks |
| AI calling pattern | Sequential messages.create() | Batch API | Batch API is async (up to 24hr delay); pipeline requires same-run results |
| HTML templates | Jinja2 + premailer | MJML | MJML requires Node.js runtime; unnecessary dependency in Python pipeline |
| Email delivery | smtplib + Gmail App Password | SendGrid / Mailgun | Personal use; 1 recipient; no need for deliverability infrastructure |
| Email delivery | smtplib + Gmail App Password | Gmail OAuth2 | App Password is simpler for non-interactive server scripts; OAuth requires token refresh flow |
| Scheduling | GitHub Actions cron | AWS Lambda + EventBridge | GH Actions is free for this use case; no additional infra to manage |

---

## Confidence Levels

| Component | Confidence | Basis |
|-----------|------------|-------|
| feedparser 6.0.12 | HIGH | Verified via PyPI (released Sep 10, 2025) |
| httpx 0.28.1 | HIGH | Verified via PyPI (released Dec 6, 2024) |
| playwright 1.58.0 | HIGH | Verified via PyPI (released Jan 30, 2026) |
| beautifulsoup4 4.14.3 | HIGH | Verified via PyPI (released Nov 30, 2025) |
| anthropic 0.84.0 | HIGH | Verified via PyPI (released Feb 25, 2026) |
| claude-haiku-4-5-20251001 model ID | HIGH | Verified via official Anthropic models page |
| Jinja2 3.1.6 | HIGH | Verified via PyPI (released Mar 5, 2025) |
| premailer 3.10.0 | MEDIUM | Verified version via PyPI; released Aug 2021 (no newer release found — project may be feature-complete or unmaintained) |
| Gmail App Password SMTP | HIGH | Multiple official sources + current Google account docs |
| GitHub Actions cron UTC | HIGH | Official GitHub Actions docs |
| Cookie-based WSJ scraping | MEDIUM | Technical approach is correct; WSJ anti-bot effectiveness is unknown without testing |
| Long-term cookie scraping viability | LOW | Cookies expire; WSJ/The Information may rotate session requirements; needs monitoring |

---

## Sources

- feedparser PyPI: https://pypi.org/project/feedparser/ (verified Sep 2025 release)
- feedparser GitHub: https://github.com/kurtmckee/feedparser
- Anthropic models overview: https://platform.claude.com/docs/en/about-claude/models/overview (verified Mar 2026)
- Anthropic Python SDK PyPI: https://pypi.org/project/anthropic/ (verified Feb 25, 2026 release)
- Anthropic prompt caching docs: https://platform.claude.com/docs/en/build-with-claude/prompt-caching
- httpx PyPI: https://pypi.org/project/httpx/ (verified Dec 2024 release)
- playwright PyPI: https://pypi.org/project/playwright/ (verified Jan 2026 release)
- beautifulsoup4 PyPI: https://pypi.org/project/beautifulsoup4/ (verified Nov 2025 release)
- Jinja2 PyPI: https://pypi.org/project/Jinja2/ (verified Mar 2025 release)
- premailer PyPI: https://pypi.org/project/premailer/ (Aug 2021)
- Gmail SMTP App Password: https://mailtrap.io/blog/python-send-email-gmail/ (2026 guidance)
- GitHub Actions cron: https://docs.github.com/actions/using-workflows/events-that-trigger-workflows#schedule
- GitHub Actions secrets: https://docs.github.com/actions/security-guides/using-secrets-in-github-actions
- actions/setup-python caching: https://github.com/marketplace/actions/setup-python
