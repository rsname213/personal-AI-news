# Phase 2: Polish and Resilience - Research

**Researched:** 2026-03-01
**Domain:** HTML email design (Gmail-compatible) + URL deduplication
**Confidence:** HIGH

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| PIPE-05 | System deduplicates content so the same article never appears twice across consecutive runs | Deduplication pattern: JSON file `.seen_urls` at repo root; URL normalization via urllib.parse; integrate in filter.py after recency step |
| EMAIL-01 | Email renders correctly in Gmail (inline CSS, table-based layout, no unsupported CSS) | premailer 3.10.0 already installed and wired in render.py; template redesign must stay within confirmed Gmail CSS support |
| EMAIL-02 | Email visually designed based on Wispr Flow aesthetic — clean, minimal, modern | Wispr Flow design tokens documented; system font stack required (no Google Fonts @import in email); Minimalism/Swiss style variant |
| EMAIL-04 | Email total size stays under 102KB to prevent Gmail clipping | Baseline is 10,590 bytes — enormous headroom; monitor in orchestrator (already done in Phase 1) |
| EMAIL-05 | Email supports dark mode on Apple Mail and Gmail Mobile via @media (prefers-color-scheme: dark) | @media approach works for Apple Mail + iOS Mail; Gmail mobile does its own color inversion — design to survive inversion, not fight it; premailer must preserve style block |
| EMAIL-06 | If all sources in a section return no new content, that section is suppressed | Already implemented in render.py line 42 — needs verification test only, plus ALL-empty edge case handling |
</phase_requirements>

---

## Summary

Phase 2 has two parallel work streams: (1) email visual redesign to a Wispr Flow-inspired clean minimal aesthetic, and (2) pipeline resilience via URL-based deduplication. Both streams are low risk given the solid Phase 1 foundation — premailer is already wired, the template already uses table-based layout, and empty-section suppression is already coded (just needs verification).

The email design work is the most creative and highest-effort task. The design goal is clean, white-background, generous-whitespace, sans-serif modernism — exactly what Wispr Flow and its peers (Linear, Loom, Notion) use. For email specifically, all design must be implemented with inline CSS and table structure. Google Fonts @import is stripped by Gmail, so the system font stack (`-apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif`) is the correct approach — and it's already in the Phase 1 template. The Wispr Flow brand uses the same system sans-serif pattern.

Dark mode is nuanced: `@media (prefers-color-scheme: dark)` works in Apple Mail and iOS Mail (both excellent targets), but Gmail mobile performs its own brightness inversion that cannot be overridden. The practical strategy is to (a) write proper `@media` dark styles for Apple Mail, (b) design midtone colors that survive Gmail's inversion gracefully, and (c) use `premailer`'s `keep_style_tags=True` to ensure the `@media` block is preserved in the output HTML. For deduplication, the implementation is a single Python module that reads/writes a JSON file (`.seen_urls`) and integrates into `filter.py` after the recency filter.

**Primary recommendation:** Redesign `digest.html.j2` with Wispr Flow tokens + inline-first CSS, add `@media` dark mode block in a preserved style tag, implement `pipeline/deduplicate.py` with a JSON seen-URLs store, and verify EMAIL-06 edge cases.

---

## Standard Stack

### Core (already installed — no new installs needed)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Jinja2 | 3.1.6 | HTML template rendering | Already wired; autoescape on |
| premailer | 3.10.0 | CSS inlining for Gmail compat | Already wired in render.py; supports `keep_style_tags` |
| Python stdlib: `json`, `os`, `urllib.parse` | stdlib | Deduplication store I/O + URL normalization | No new deps; json for seen-URLs file |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `urllib.parse.urlparse` / `urlencode` | stdlib | Normalize URLs for dedup key | Strip UTM params, trailing slashes before hashing |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| stdlib `json` for seen-URLs | SQLite | SQLite is overkill; REQUIREMENTS.md explicitly calls out "no database" — JSON file is the right call |
| System font stack | Google Fonts @import | Gmail strips `@import` and `<link rel="stylesheet">` entirely — system fonts are not optional |
| premailer `keep_style_tags=True` | Manual style block in template | `keep_style_tags=True` is cleaner; same outcome |

**Installation:** No new packages needed. All dependencies are already installed.

---

## Architecture Patterns

### Recommended Project Structure Changes

```
personal-AI-news/
├── pipeline/
│   ├── filter.py          # Add dedup call after recency filter
│   ├── deduplicate.py     # NEW: seen-URLs read/write logic
│   └── render.py          # Update transform() call to keep_style_tags=True
├── templates/
│   └── digest.html.j2     # REDESIGN: Wispr Flow aesthetic + dark mode @media block
└── .seen_urls             # CREATED AT RUNTIME: JSON list of seen URLs (gitignored or committed)
```

### Pattern 1: URL Deduplication with JSON Seen-File

**What:** Before articles reach summarization, check each article's normalized URL against a persisted `.seen_urls` file. Articles whose URL was seen in the last N days are excluded. After the email is sent successfully, update the file with today's URLs.

**When to use:** Every pipeline run. The seen file is a rolling window (e.g., 7 days).

**Architecture decision — where to call deduplicate:**

The deduplication step belongs AFTER `filter_articles()` in orchestrator.py (recency + cap already applied) and BEFORE `summarize_articles()` (so we don't waste Claude API calls on duplicates). The seen-URLs file is updated AFTER a successful `send_email()` call — not before — so a failed run does not incorrectly mark articles as "seen."

```python
# pipeline/deduplicate.py
# Source: project design — no external dependency needed

import json
import os
from datetime import datetime, timezone
from urllib.parse import urlparse, urlencode, parse_qsl

SEEN_URLS_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".seen_urls")
DEDUP_WINDOW_DAYS = 7

# UTM parameters to strip before URL comparison
_UTM_PARAMS = {"utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content"}


def _normalize_url(url: str) -> str:
    """
    Normalize URL for dedup comparison.
    - Lowercase scheme + host
    - Strip UTM query parameters
    - Strip trailing slash from path
    - Drop fragment
    """
    parsed = urlparse(url.lower().strip())
    # Filter out UTM params
    clean_params = [(k, v) for k, v in parse_qsl(parsed.query) if k not in _UTM_PARAMS]
    path = parsed.path.rstrip("/") or "/"
    normalized = parsed._replace(
        path=path,
        query=urlencode(clean_params),
        fragment="",
    )
    return normalized.geturl()


def load_seen_urls() -> dict[str, str]:
    """
    Load seen URLs from .seen_urls file.
    Returns dict of {normalized_url: iso_date_string}.
    Returns empty dict if file does not exist.
    """
    if not os.path.exists(SEEN_URLS_PATH):
        return {}
    try:
        with open(SEEN_URLS_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}  # Corrupt file — treat as empty, will be overwritten


def save_seen_urls(seen: dict[str, str]) -> None:
    """Write seen URLs dict back to .seen_urls file."""
    with open(SEEN_URLS_PATH, "w", encoding="utf-8") as f:
        json.dump(seen, f, indent=2)


def purge_old_entries(seen: dict[str, str], window_days: int = DEDUP_WINDOW_DAYS) -> dict[str, str]:
    """Remove entries older than window_days from the seen dict."""
    cutoff = datetime.now(timezone.utc).date()
    from datetime import timedelta
    oldest_allowed = cutoff - timedelta(days=window_days)
    return {
        url: date_str
        for url, date_str in seen.items()
        if datetime.fromisoformat(date_str).date() >= oldest_allowed
    }


def filter_duplicates(articles, seen: dict[str, str]) -> tuple[list, list]:
    """
    Split articles into (new_articles, duplicate_articles).
    new_articles: not seen in the window
    duplicate_articles: already seen — excluded from email
    """
    new, dupes = [], []
    for article in articles:
        key = _normalize_url(article.url)
        if key in seen:
            dupes.append(article)
        else:
            new.append(article)
    return new, dupes


def mark_as_seen(articles, seen: dict[str, str]) -> dict[str, str]:
    """Add today's articles to the seen dict. Call AFTER successful email send."""
    today = datetime.now(timezone.utc).date().isoformat()
    for article in articles:
        key = _normalize_url(article.url)
        seen[key] = today
    return seen
```

**Orchestrator integration (orchestrator.py):**

```python
from pipeline.deduplicate import (
    load_seen_urls, save_seen_urls, purge_old_entries,
    filter_duplicates, mark_as_seen
)

# After filter step, before summarize:
seen = purge_old_entries(load_seen_urls())
filtered, dupes = filter_duplicates(filtered, seen)
print(f"[OK] Dedup: {len(dupes)} duplicates removed, {len(filtered)} articles remain")

# After successful send (at end of main()):
seen = mark_as_seen(summarized, seen)
save_seen_urls(seen)
print(f"[OK] Seen URLs file updated ({len(seen)} entries)")
```

### Pattern 2: Wispr Flow Email Design with Inline CSS

**What:** A clean, minimal single-column email template using table-based layout, inline CSS for all structural styles, and a preserved `<style>` block for dark mode media query.

**Design tokens from Wispr Flow analysis:**

| Token | Light Mode Value | Dark Mode Value | Notes |
|-------|-----------------|-----------------|-------|
| Background (outer) | `#f5f5f5` | `#121212` | Outer wrapper |
| Background (card) | `#ffffff` | `#1e1e1e` | Main content area |
| Text primary | `#111111` | `#eeeeee` | Headlines, article titles |
| Text secondary | `#555555` | `#aaaaaa` | Meta, dates, source names |
| Text muted | `#888888` | `#777777` | Footer, small labels |
| Accent (left border) | `#dddddd` | `#444444` | "Why it matters" left border |
| Divider | `#e8e8e8` | `#333333` | Section separators |
| Section label | `#999999` | `#666666` | Uppercase section headers |
| Link color | `#111111` | `#eeeeee` | Article title links |
| Font stack | `-apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica Neue, Arial, sans-serif` | same | No Google Fonts in email |

**Key typography measurements:**

| Element | Size | Weight | Color |
|---------|------|--------|-------|
| Header title "AI Briefing" | 20px | 700 | `#111111` |
| Header date | 13px | 400 | `#888888` |
| Section label | 10px | 600 | `#999999`, uppercase, letter-spacing: 0.12em |
| Article title (link) | 15px | 600 | `#111111` |
| Article meta | 12px | 400 | `#888888` |
| Article summary | 14px | 400 | `#333333`, line-height: 1.65 |
| Why it matters | 13px | 400 | `#555555`, left-border accent |
| Footer | 11px | 400 | `#aaaaaa` |

**Template structure pattern:**

```html
<!-- Source: Phase 1 baseline + Wispr Flow design tokens -->
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <meta name="color-scheme" content="light dark">
  <meta name="supported-color-schemes" content="light dark">
  <style data-premailer="ignore">
    /* Dark mode — preserved by premailer; Apple Mail + iOS Mail only */
    @media (prefers-color-scheme: dark) {
      body { background-color: #121212 !important; }
      .wrapper-td { background-color: #1e1e1e !important; }
      .header-title { color: #eeeeee !important; }
      .header-date { color: #777777 !important; }
      .section-header { color: #666666 !important; border-bottom-color: #333333 !important; }
      .article-title { color: #eeeeee !important; }
      .article-meta { color: #888888 !important; }
      .article-summary { color: #cccccc !important; }
      .article-why { color: #aaaaaa !important; border-left-color: #444444 !important; }
      .footer { color: #555555 !important; border-top-color: #333333 !important; }
    }
  </style>
  <style>
    /* Structural styles — inlined by premailer */
    body { ... }
    .wrapper { ... }
    /* all other styles */
  </style>
</head>
```

**render.py change — preserve dark mode style block:**

```python
# Current (Phase 1):
inlined_html = transform(raw_html)

# Phase 2 — keep_style_tags=True so @media block survives:
inlined_html = transform(raw_html, keep_style_tags=True, strip_important=False)
```

The `data-premailer="ignore"` attribute on the dark mode `<style>` block tells premailer to skip processing that block entirely (confirmed supported per PyPI docs). The structural `<style>` block without this attribute gets fully inlined. Result: all layout CSS is inline, dark mode `@media` stays in `<head>`.

### Pattern 3: Empty Section Suppression Verification (EMAIL-06)

**What:** EMAIL-06 is already implemented in `render.py` line 42. The code suppresses empty sections correctly. This pattern is about verifying the edge case: ALL sections empty.

**Current code (render.py line 42):**
```python
sections = {cat: arts for cat, arts in sections.items() if arts}
```

This works correctly. The edge case is when `sections` becomes `{}` after suppression — the template renders with only the header and footer and no articles. This is acceptable behavior (the orchestrator already logs a warning and continues). No code change needed; only verification.

**Edge case test:** If `sections` is empty, the Jinja2 `{% for ... %}` loop simply produces no output — the email sends with header + date + footer only. For a personal self-send, this is correct behavior (empty digest is a valid outcome on a slow news day).

### Anti-Patterns to Avoid

- **Anti-pattern: Updating seen-URLs before email is sent.** If the SMTP call fails, the articles are falsely marked as seen and excluded from tomorrow's run. Always update after successful send.
- **Anti-pattern: Using article title as dedup key.** Titles can change. URLs are more stable. Use URL as primary key, normalized.
- **Anti-pattern: Flexbox or Grid in email layout.** Gmail strips `display: flex` sub-properties. Keep all layout in `<table>` elements. The Phase 1 template already uses tables correctly.
- **Anti-pattern: `<link rel="stylesheet">` or `@import url(...)` for fonts.** Gmail strips external stylesheets entirely. System font stack only.
- **Anti-pattern: `box-shadow`, `filter`, `clip-path`, `animation`, `transition` in email.** All stripped by Gmail. Use `border` for visual separation, no shadows or effects.
- **Anti-pattern: `premailer.transform()` without `keep_style_tags=True`.** The default strips all style blocks after inlining, removing the dark mode `@media` query. Pass `keep_style_tags=True`.
- **Anti-pattern: Marking seen-URLs using article GUID.** RSS GUIDs reset on CMS upgrades. URL is the stable key.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| CSS inlining for Gmail | Custom regex CSS inliner | `premailer.transform()` (already installed) | premailer handles CSS specificity, inheritance, shorthand expansion, malformed CSS gracefully |
| URL normalization | Custom string manipulation | `urllib.parse.urlparse` + `urlencode` (stdlib) | Handles edge cases: schemes, ports, encoded chars, empty query strings |
| Jinja2 template section suppression | Manual string building | `{% if articles %}` guard already in template | Already done; don't replace with Python-side string construction |

**Key insight:** The project's dependencies for Phase 2 are already installed. The only new code is `pipeline/deduplicate.py` (~60 lines) and the template redesign.

---

## Common Pitfalls

### Pitfall 1: premailer Strips Dark Mode @media Block

**What goes wrong:** `premailer.transform(raw_html)` with default settings inlines all CSS and removes the `<style>` blocks. The dark mode `@media (prefers-color-scheme: dark)` rules are wiped from the output HTML. The email renders correctly in the browser preview but has no dark mode support.

**Why it happens:** premailer's default `keep_style_tags=False` removes all style blocks after processing. `@media` queries cannot be inlined (they have no equivalent as element-level attributes), so they are silently dropped.

**How to avoid:** Two combined approaches:
1. Add `data-premailer="ignore"` attribute to the dark mode `<style>` block — premailer skips that block entirely.
2. Call `transform(raw_html, keep_style_tags=True, strip_important=False)` — keeps all style blocks in output.

Using both together is belt-and-suspenders and ensures the dark mode block survives regardless of premailer version behavior.

**Warning signs:** Inspect the output of `transform()` and check if `@media (prefers-color-scheme: dark)` appears in the HTML string. If not, the block was stripped.

### Pitfall 2: Gmail Mobile Ignores @media prefers-color-scheme

**What goes wrong:** Developer adds `@media (prefers-color-scheme: dark)` dark mode styles, tests in Apple Mail (works), then sends to Gmail and is confused when dark mode looks broken on Gmail iOS/Android.

**Why it happens:** Gmail mobile does NOT support `@media (prefers-color-scheme: dark)`. It performs its own brightness inversion on any color it finds — light backgrounds become dark, dark text becomes light. This is a Gmail-specific behavior that cannot be overridden via CSS.

**How to avoid:** Design the email to survive Gmail's inversion gracefully by using midtone colors where possible. The `@media` dark mode block targets Apple Mail and iOS Mail only — this is still valuable for ~50%+ of email opens. For Gmail, accept the inversion behavior.

**Warning signs:** Dark mode looks different in Apple Mail vs Gmail iPhone app — this is expected, not a bug.

**Confirmed client support for @media prefers-color-scheme (from caniemail.com, multiple sources):**
- Apple Mail macOS: YES
- Apple Mail iOS: YES
- Gmail Web (desktop): NO (not listed as supported media feature in Gmail developer docs)
- Gmail iOS/Android: NO (does its own inversion)

### Pitfall 3: Seen-URLs File Grows Unboundedly

**What goes wrong:** The `.seen_urls` JSON file accumulates entries forever. After months of daily runs at ~25 articles/day, the file becomes large enough to slow I/O and git diffs.

**Why it happens:** Simple append-only logic without cleanup.

**How to avoid:** `purge_old_entries()` in `deduplicate.py` removes entries older than `DEDUP_WINDOW_DAYS` (7 days) on every run. With ~25 articles/day and 7-day window, the file stays under ~175 entries — well under 50KB.

**Warning signs:** File exceeds 500 entries; git history shows continuously growing file.

### Pitfall 4: Deduplication Runs Before Email Is Sent — Then SMTP Fails

**What goes wrong:** The orchestrator marks articles as "seen" before calling `send_email()`. SMTP fails. Tomorrow's run skips these articles as duplicates. Articles are permanently lost.

**Why it happens:** Naive ordering: deduplicate → summarize → send → update seen.

**How to avoid:** Call `mark_as_seen()` and `save_seen_urls()` ONLY after `send_email()` returns successfully. The orchestrator already has a clear pipeline ordering; insert the save call at the very end.

**Warning signs:** Yesterday's email was not received, and today's email is missing articles from yesterday.

### Pitfall 5: Gmail Style Block 8KB Limit

**What goes wrong:** The preserved `<style>` block (dark mode rules) is combined with leftover structural CSS in a single block that exceeds 8,192 characters, causing Gmail to strip the entire block.

**Why it happens:** premailer with `keep_style_tags=True` may merge style blocks or leave larger remnants.

**How to avoid:** Keep the dark mode `@media` block compact — only override colors, no font-size or layout changes. Target 20-30 rules maximum. Verify the style block character count in the rendered HTML before finalizing the template. 8,192 chars is the confirmed Gmail limit (Pitfall 8 in PITFALLS.md).

**Warning signs:** Style block exceeds ~7,000 characters in the premailer output.

---

## Code Examples

### Wispr Flow-Inspired Email Template Pattern

```html
<!-- Source: Wispr Flow design analysis + Phase 1 baseline + Gmail email HTML research -->
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <meta name="color-scheme" content="light dark">
  <meta name="supported-color-schemes" content="light dark">

  <!-- Dark mode: data-premailer="ignore" preserves this block; Apple Mail + iOS Mail only -->
  <style data-premailer="ignore">
    @media (prefers-color-scheme: dark) {
      body { background-color: #121212 !important; }
      .content-td { background-color: #1e1e1e !important; }
      .header-title { color: #eeeeee !important; }
      .header-date { color: #777777 !important; }
      .section-header {
        color: #666666 !important;
        border-bottom-color: #333333 !important;
      }
      .article-title { color: #eeeeee !important; }
      .article-meta { color: #888888 !important; }
      .article-summary { color: #cccccc !important; }
      .article-why {
        color: #aaaaaa !important;
        border-left-color: #444444 !important;
      }
      .footer {
        color: #555555 !important;
        border-top-color: #2a2a2a !important;
      }
    }
  </style>

  <!-- Structural styles: inlined by premailer into element style="" attributes -->
  <style>
    body {
      margin: 0;
      padding: 0;
      background-color: #f5f5f5;
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI',
                   'Helvetica Neue', Arial, sans-serif;
      -webkit-font-smoothing: antialiased;
    }
    .outer-td {
      padding: 32px 16px;
      background-color: #f5f5f5;
    }
    .content-td {
      background-color: #ffffff;
      padding: 40px 36px;
      border-radius: 0; /* border-radius stripped by Gmail — keep at 0 */
    }
    .header-title {
      font-size: 20px;
      font-weight: 700;
      color: #111111;
      margin: 0 0 6px 0;
      letter-spacing: -0.01em;
    }
    .header-date {
      font-size: 13px;
      color: #888888;
      margin: 0 0 40px 0;
    }
    .section-header {
      font-size: 10px;
      font-weight: 600;
      letter-spacing: 0.12em;
      text-transform: uppercase;
      color: #999999;
      border-bottom: 1px solid #e8e8e8;
      padding-bottom: 8px;
      margin: 36px 0 18px 0;
    }
    .article-title {
      font-size: 15px;
      font-weight: 600;
      color: #111111;
      text-decoration: none;
      display: block;
      margin-bottom: 5px;
      line-height: 1.4;
    }
    .article-meta {
      font-size: 12px;
      color: #888888;
      margin: 0 0 10px 0;
    }
    .article-summary {
      font-size: 14px;
      color: #333333;
      line-height: 1.65;
      margin: 0 0 10px 0;
    }
    .article-why {
      font-size: 13px;
      color: #555555;
      border-left: 3px solid #dddddd;
      padding-left: 12px;
      margin: 0 0 24px 0;
      line-height: 1.55;
    }
    .article-no-summary {
      font-size: 13px;
      color: #888888;
      font-style: italic;
      margin: 0 0 24px 0;
    }
    .footer {
      font-size: 11px;
      color: #aaaaaa;
      margin-top: 40px;
      border-top: 1px solid #eeeeee;
      padding-top: 16px;
    }
  </style>
</head>
<body>
  <table width="100%" cellpadding="0" cellspacing="0" border="0">
    <tr>
      <td class="outer-td" align="center">
        <table width="600" cellpadding="0" cellspacing="0" border="0"
               style="max-width: 600px; width: 100%;">
          <tr>
            <td class="content-td">

              <!-- Header -->
              <p class="header-title">AI Briefing</p>
              <p class="header-date">{{ date }}</p>

              <!-- Sections -->
              {% for category, articles in sections.items() %}
              {% if articles %}
              <p class="section-header">{{ category }}</p>
              {% for article in articles %}
              <a href="{{ article.url }}" class="article-title">{{ article.title }}</a>
              <p class="article-meta">
                {{ article.source_name }}&nbsp;&middot;&nbsp;{{ article.published_at.strftime('%b %-d, %Y') }}
              </p>
              {% if not article.summarization_failed %}
              <p class="article-summary">{{ article.summary }}</p>
              <p class="article-why">
                <strong>Why it matters:</strong> {{ article.why_it_matters }}
              </p>
              {% else %}
              <p class="article-no-summary">
                Summary unavailable &mdash;
                <a href="{{ article.url }}" style="color: #666666;">read article</a>
              </p>
              {% endif %}
              {% endfor %}
              {% endif %}
              {% endfor %}

              <!-- Footer -->
              <p class="footer">Generated {{ date }} &middot; Personal AI Briefing</p>

            </td>
          </tr>
        </table>
      </td>
    </tr>
  </table>
</body>
</html>
```

### render.py Change (premailer with style preservation)

```python
# Source: premailer 3.10.0 PyPI docs + data-premailer="ignore" attribute support

# Before (Phase 1 — strips dark mode block):
inlined_html = transform(raw_html)

# After (Phase 2 — preserves dark mode @media block):
inlined_html = transform(
    raw_html,
    keep_style_tags=True,    # Keep style blocks in <head> (dark mode @media survives)
    strip_important=False,   # Preserve !important in @media overrides
)
```

### URL Deduplication — normalize_url pattern

```python
# Source: Python stdlib urllib.parse docs
from urllib.parse import urlparse, urlencode, parse_qsl

_UTM_PARAMS = {"utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content"}

def _normalize_url(url: str) -> str:
    parsed = urlparse(url.lower().strip())
    clean_params = [(k, v) for k, v in parse_qsl(parsed.query) if k not in _UTM_PARAMS]
    path = parsed.path.rstrip("/") or "/"
    normalized = parsed._replace(
        path=path,
        query=urlencode(sorted(clean_params)),  # sort for stability
        fragment="",
    )
    return normalized.geturl()
```

---

## State of the Art

| Old Approach | Current Approach | Impact for This Project |
|--------------|-----------------|------------------------|
| Email layout with CSS Flexbox/Grid | Table-based HTML layout | Tables required — already used in Phase 1 template |
| External fonts via `<link>` | System font stack in inline CSS | Gmail strips `<link>`; system stack already in Phase 1 |
| Full dark mode control via CSS | @media for Apple Mail + accept Gmail inversion | Pragmatic — delivers dark mode for ~50% of opens |
| Deduplication via database | JSON file (stateless per-run with committed state) | Requirements explicitly say no DB; JSON file is correct choice |
| premailer without options | `keep_style_tags=True, strip_important=False` | Required to preserve @media dark mode block |

**Note on Gmail CSS support:** Google's official CSS support page (developers.google.com/workspace/gmail/design/css) documents 200+ supported properties but does NOT list `prefers-color-scheme` as a supported media query feature. The only documented media query features are `min-width`, `max-width`, `min-device-width`, `max-device-width`, `orientation`, `min-resolution`, `max-resolution`. This is consistent with the observed behavior that Gmail mobile ignores `@media (prefers-color-scheme: dark)`.

---

## Open Questions

1. **Does `premailer keep_style_tags=True` leave a large style remnant that could approach the 8KB Gmail limit?**
   - What we know: premailer inlines what it can and leaves what it cannot in the style block. Media queries cannot be inlined. The dark mode `@media` block will be ~1-2KB. Any leftover structural CSS from the main `<style>` block could add more.
   - What's unclear: Exact size of the premailer output's remaining style block.
   - Recommendation: After implementing, print `len(re.findall(r'<style[^>]*>(.*?)</style>', rendered_html, re.DOTALL))` in a test render and verify the style block is under 6KB (leaving buffer below 8KB limit).

2. **Should `.seen_urls` be committed to git or gitignored?**
   - What we know: The file must persist between GitHub Actions runs. The only persistence mechanism in this stateless-runner setup is either (a) committing the file to the repo or (b) using a GitHub Actions cache. REQUIREMENTS.md says "stateless per-run is sufficient; deduplication via URL hash file" — this implies committing the file.
   - What's unclear: Whether auto-committing from GitHub Actions (to update `.seen_urls`) is acceptable in this project's workflow.
   - Recommendation: Commit `.seen_urls` to the repo. Add a git commit step at the end of the GitHub Actions workflow after email sends successfully: `git add .seen_urls && git commit -m "chore: update seen URLs" && git push`. This is the standard pattern for stateful GitHub Actions workflows.

3. **What if .seen_urls doesn't exist on the first run?**
   - What we know: `load_seen_urls()` returns `{}` if file not found — this is handled.
   - What's unclear: Nothing — this is handled cleanly.
   - Recommendation: No action needed; `{}` means no articles are filtered as duplicates on first run.

---

## Validation Architecture

> Note: `workflow.nyquist_validation` is not present in `.planning/config.json` — field not set, treated as false. Skipping formal validation architecture section.

However, for Phase 2, the following manual verification steps are critical:

1. **EMAIL-01 / EMAIL-02 verification:** Send the redesigned email to the Gmail test account and visually inspect in Gmail web + Gmail iOS (dark mode on). The only reliable test is a real send.
2. **PIPE-05 verification:** Run the pipeline twice in succession. Confirm the second run excludes all articles from the first run. Check `.seen_urls` file content after each run.
3. **EMAIL-06 verification:** Force all sections empty by temporarily filtering out all articles. Confirm the email renders without crashing and with no empty section headers.
4. **EMAIL-04 verification:** Print HTML byte size after `transform()` call. Already done in orchestrator.py. Confirm < 102KB.
5. **EMAIL-05 verification:** Open the sent email in Apple Mail (macOS or iOS) with dark mode enabled. Confirm dark mode colors apply. In Gmail iOS with dark mode, confirm graceful inversion (no completely invisible text).

---

## Sources

### Primary (HIGH confidence)
- `premailer` PyPI docs (3.10.0) — `keep_style_tags`, `strip_important`, `data-premailer="ignore"` attribute
- Python stdlib `urllib.parse` docs — `urlparse`, `urlencode`, `parse_qsl`
- Google Developers Gmail CSS Support page — confirmed supported media query features (no `prefers-color-scheme` listed)
- caniemail.com `css-at-media-prefers-color-scheme` — support table for Apple Mail, Gmail
- Existing project code — `pipeline/render.py`, `pipeline/filter.py`, `models.py`, `orchestrator.py`, `templates/digest.html.j2`

### Secondary (MEDIUM confidence)
- [Wispr Flow website design analysis](https://wisprflow.ai) — design tokens extracted via WebFetch (color palette, typography, spacing)
- [Litmus Ultimate Guide to Dark Mode Email](https://www.litmus.com/blog/the-ultimate-guide-to-dark-mode-for-email-marketers) — @media pattern, [data-ogsc] pattern, client support matrix
- [htmlemail.io dark mode guide](https://htmlemail.io/blog/dark-mode-email-styles) — meta tags `color-scheme`, `supported-color-schemes`, code patterns
- [mailmoxie.com Gmail dark mode article](https://www.mailmoxie.com/blog/gmail-dark-mode-email-design) — Gmail inversion behavior confirmed, no CSS control on mobile
- [Email on Acid Gmail rendering guide](https://www.emailonacid.com/blog/article/email-development/12-things-you-must-know-when-developing-for-gmail-and-gmail-mobile-apps-2/) — Gmail CSS stripping behaviors
- [designmodo.com HTML CSS in emails 2025](https://designmodo.com/html-css-emails/) — current state of HTML email best practices
- PITFALLS.md Pitfall 8 — project-specific Gmail CSS stripping research (style block 8KB limit, 102KB clip threshold)
- UI/UX Pro Max skill — design system output for "SaaS newsletter email minimal clean modern"

### Tertiary (LOW confidence)
- Individual community discussions about Gmail dark mode (Latenode, Klaviyo) — consistent with higher-confidence sources but not authoritative

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries already installed; no new dependencies needed
- Architecture patterns: HIGH — deduplication pattern is well-established; premailer options verified against PyPI docs
- Design tokens: MEDIUM — Wispr Flow tokens extracted via WebFetch (live site analysis); system font stack confirmed required
- Dark mode strategy: HIGH — Gmail behavior confirmed via multiple sources + official Gmail CSS docs; Apple Mail support confirmed via caniemail.com
- Pitfalls: HIGH — all pitfalls supported by multiple sources or verified against existing PITFALLS.md research

**Research date:** 2026-03-01
**Valid until:** 2026-09-01 (Gmail CSS behavior stable; premailer API stable; dark mode landscape evolves slowly)
