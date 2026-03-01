---
phase: 01-core-pipeline
plan: "02"
subsystem: fetchers
tags: [feedparser, httpx, beautifulsoup4, rss, atom, scraping, lxml]

# Dependency graph
requires:
  - phase: 01-core-pipeline
    plan: "01"
    provides: "RawArticle, FilteredArticle, SummarizedArticle dataclasses in models.py"
provides:
  - "fetchers/rss.py: fetch_feed(), fetch_all(), FEED_URLS config (20 sources)"
  - "fetchers/paul_graham.py: fetch() via community RSS (olshansk/pgessays-rss)"
  - "fetchers/gwern.py: fetch() scraping gwern.net/blog/index with YYYY-MM-DD date precision"
  - "fetchers/anthropic_blog.py: fetch() with community RSS primary + anthropic.com/news scraper fallback"
affects:
  - filter
  - pipeline
  - 01-03
  - 01-04
  - 01-05

# Tech tracking
tech-stack:
  added:
    - feedparser==6.0.12 (RSS/Atom parsing, normalizes all feed formats)
    - httpx==0.28.1 (HTTP client for scrapers)
    - beautifulsoup4==4.14.3 + lxml (HTML parsing for gwern and anthropic scrapers)
  patterns:
    - "25-hour cutoff window (not 24h) to absorb GitHub Actions scheduling delays"
    - "try/except Exception on all fetcher bodies — log [WARN], return [] on any failure"
    - "Source config in FEED_URLS dict — URL changes require no code edits"
    - "Community RSS feeds as primary for problematic sources (PG, Anthropic)"
    - "Scraper fallback when community feeds return 0 articles (Anthropic)"
    - "id=hashlib.md5(url.encode()).hexdigest() as stable dedup key"

key-files:
  created:
    - fetchers/rss.py
    - fetchers/paul_graham.py
    - fetchers/gwern.py
    - fetchers/anthropic_blog.py
  modified: []

key-decisions:
  - "Gwern scraper uses <a id='YYYY-MM-DD'> attributes for precise date parsing (not year-only approximation) — verified against live gwern.net/blog/index HTML structure"
  - "Anthropic scraper parses date strings ('Feb 27, 2026' format) from card text — provides proper 25h recency filtering in fallback path"
  - "The Information: feedparser bozo/empty check logs specific auth warning instead of generic 0-articles warn"

patterns-established:
  - "Fetcher pattern: wrap entire body in try/except, log [WARN source: msg], return []"
  - "Fetcher pattern: 25-hour cutoff = datetime.now(timezone.utc) - timedelta(hours=25)"
  - "Fetcher pattern: skip entries where published_parsed is None"
  - "Config pattern: FEED_URLS dict maps display_name -> (url, category) — one place to fix URLs"

requirements-completed:
  - RSS-01
  - RSS-02
  - RSS-03
  - RSS-04
  - RSS-05
  - RSS-06
  - RSS-07
  - PIPE-02
  - PIPE-03

# Metrics
duration: 3min
completed: 2026-03-01
---

# Phase 1 Plan 02: Content Fetchers Summary

**Four fetchers (generic RSS with 20-source FEED_URLS config, Paul Graham community feed, Gwern HTML scraper with YYYY-MM-DD precision dates, Anthropic RSS+scraper fallback) returning RawArticle lists with 25-hour recency filtering**

## Performance

- **Duration:** 3 min
- **Started:** 2026-03-01T18:48:44Z
- **Completed:** 2026-03-01T18:51:24Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments

- `fetchers/rss.py` with `fetch_feed()`, `fetch_all()`, and `FEED_URLS` covering 18 personal blogs + WSJ + The Information (20 sources total)
- `fetchers/paul_graham.py` delegating to shared `fetch_feed()` via community RSS (olshansk/pgessays-rss)
- `fetchers/gwern.py` scraping `gwern.net/blog/index` with precise date extraction from `<a id="YYYY-MM-DD">` attributes — verified against live HTML
- `fetchers/anthropic_blog.py` with community RSS primary and `anthropic.com/news` scraper fallback with date parsing

## Task Commits

1. **Task 1: fetchers/rss.py — generic RSS fetcher and 20-source config** - `ee2b81e` (feat)
2. **Task 2: paul_graham.py, gwern.py, anthropic_blog.py** - `bdb84b1` (feat)

**Plan metadata:** _(pending docs commit)_

## Files Created/Modified

- `fetchers/rss.py` - Generic RSS/Atom fetcher + FEED_URLS config for all 20 standard sources
- `fetchers/paul_graham.py` - Thin wrapper delegating to fetch_feed() with community RSS URL
- `fetchers/gwern.py` - HTML scraper of gwern.net/blog/index; uses <a id> attributes for YYYY-MM-DD dates
- `fetchers/anthropic_blog.py` - Community RSS primary; falls back to scraping anthropic.com/news with date regex parsing

## Decisions Made

- **Gwern date precision:** The plan skeleton suggested year-only date approximation. Live HTML inspection revealed `<a id="2026-01-22">` attributes providing exact dates — used these for full YYYY-MM-DD precision with standard 25h filter (not a current-year-only filter).
- **Anthropic scraper date parsing:** Added regex date parsing (`Feb 27, 2026` format) to the fallback scraper. The plan template used `datetime.now()` as a universal fallback; parsing actual dates enables proper recency filtering in the fallback path.
- **The Information special handling:** Added bozo-check early return with a specific auth warning message to distinguish "feed broken/empty" from "no recent articles".

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Gwern year-only date approximation replaced with YYYY-MM-DD precision**
- **Found during:** Task 2 (gwern.py implementation)
- **Issue:** The plan's skeleton selector logic used year-only dates from parent text, which would only capture `<current_year>` posts but with Jan 1 timestamps — making the 25h filter always exclude them. Live HTML inspection showed `<a id="YYYY-MM-DD">` attributes available.
- **Fix:** Used `soup.find_all("a", id=re.compile(r"^\d{4}-\d{2}-\d{2}$"))` to select all post links, then parsed the id attribute directly for full date precision.
- **Files modified:** fetchers/gwern.py
- **Verification:** `python3 -c "from fetchers.gwern import fetch; r = fetch(); print(type(r))"` — returns list without raising
- **Committed in:** bdb84b1 (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (Rule 1 — bug in plan's skeleton selector logic)
**Impact on plan:** Fix improves date precision from year-level to day-level. No scope changes. Gwern fetcher now correctly filters using 25h window with exact dates.

## Issues Encountered

- Dependencies from requirements.txt were not yet installed in the codespace — ran `pip install -r requirements.txt` before implementing (Rule 3 auto-fix: blocking issue).

## User Setup Required

None — no external service configuration required for fetchers.

## Next Phase Readiness

- All 4 fetcher modules are importable with correct exports (`fetch_feed`, `fetch_all`, `FEED_URLS`, `fetch`)
- Each returns `list[RawArticle]` without raising exceptions on failure
- Ready for 01-03 (filter stage) which will consume these fetchers' output
- Known concern: Paul Graham community feed (olshansk/pgessays-rss) is a third-party scraper — may go stale. Fallback to direct paulgraham.com scraping documented in STATE.md.

---
*Phase: 01-core-pipeline*
*Completed: 2026-03-01*
