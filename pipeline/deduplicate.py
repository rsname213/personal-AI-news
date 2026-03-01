"""
URL deduplication for the AI Newsletter pipeline.

Prevents articles seen in a previous run from appearing in today's digest.

Public API:
    load_seen_urls()        — Load .seen_urls file → dict[url, date_str]
    save_seen_urls(seen)    — Write dict back to .seen_urls
    purge_old_entries(seen) — Remove entries older than DEDUP_WINDOW_DAYS
    filter_duplicates(articles, seen) → (new_articles, dupe_articles)
    mark_as_seen(articles, seen)      → updated seen dict

Storage format (.seen_urls):
    JSON dict mapping normalized URL strings to ISO date strings (YYYY-MM-DD).
    Example: {"https://example.com/article": "2026-02-28"}
"""
import json
import os
from datetime import datetime, timezone, timedelta
from urllib.parse import urlparse, urlencode, parse_qsl

# ---------------------------------------------------------------------------
# Module-level constants
# ---------------------------------------------------------------------------

SEEN_URLS_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".seen_urls")
DEDUP_WINDOW_DAYS = 7
_UTM_PARAMS = {"utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content"}


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _normalize_url(url: str) -> str:
    """
    Normalize a URL for stable deduplication comparison.

    Transformations applied:
    - Lowercase scheme and host
    - Strip UTM query parameters
    - Sort remaining query params for stability
    - Strip trailing slash from path (keep '/' for root paths)
    - Drop fragment (#section)
    """
    parsed = urlparse(url.lower().strip())

    # Filter out UTM params; sort remaining for stability
    query_pairs = [
        (k, v) for k, v in parse_qsl(parsed.query)
        if k not in _UTM_PARAMS
    ]
    query_pairs.sort()
    normalized_query = urlencode(query_pairs)

    # Strip trailing slash from path (but preserve lone '/' root)
    path = parsed.path.rstrip("/") or "/"
    # If path is now empty (was just '/'), restore '/'
    if not path:
        path = "/"

    # Reconstruct — drop fragment by passing empty string
    normalized = parsed._replace(
        path=path,
        query=normalized_query,
        fragment="",
    )
    return normalized.geturl()


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def load_seen_urls() -> dict[str, str]:
    """
    Load the seen-URLs store from disk.

    Returns:
        dict mapping normalized URL → ISO date string (YYYY-MM-DD)
        Returns {} if file does not exist, is unreadable, or contains invalid JSON.
    """
    try:
        with open(SEEN_URLS_PATH, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except (FileNotFoundError, OSError, json.JSONDecodeError):
        return {}


def save_seen_urls(seen: dict[str, str]) -> None:
    """
    Persist the seen-URLs dict to disk as indented JSON.

    Args:
        seen: dict mapping normalized URL → ISO date string
    """
    with open(SEEN_URLS_PATH, "w", encoding="utf-8") as fh:
        json.dump(seen, fh, indent=2)


def purge_old_entries(
    seen: dict[str, str],
    window_days: int = DEDUP_WINDOW_DAYS,
) -> dict[str, str]:
    """
    Remove entries older than window_days from the seen dict.

    Args:
        seen:        Current seen-URLs dict
        window_days: Entries with date < (today - window_days) are removed

    Returns:
        New dict containing only entries within the retention window.
        An entry dated exactly window_days ago is retained (inclusive cutoff).
    """
    cutoff = datetime.now(timezone.utc).date() - timedelta(days=window_days)
    return {
        url: date_str
        for url, date_str in seen.items()
        if datetime.fromisoformat(date_str).date() >= cutoff
    }


def filter_duplicates(articles: list, seen: dict[str, str]) -> tuple[list, list]:
    """
    Split articles into new (unseen) and duplicate (already seen) lists.

    Args:
        articles: List of article objects (must have a .url attribute)
        seen:     Dict mapping normalized URL → date string

    Returns:
        (new_articles, dupe_articles) — order within each list is preserved.
    """
    new_articles = []
    dupe_articles = []
    for article in articles:
        if _normalize_url(article.url) in seen:
            dupe_articles.append(article)
        else:
            new_articles.append(article)
    return new_articles, dupe_articles


def mark_as_seen(articles: list, seen: dict[str, str]) -> dict[str, str]:
    """
    Add each article's normalized URL to the seen dict with today's date.

    Args:
        articles: List of article objects (must have a .url attribute)
        seen:     Existing seen-URLs dict (modified in place and returned)

    Returns:
        Updated seen dict (same object, mutated).
    """
    today = datetime.now(timezone.utc).date().isoformat()
    for article in articles:
        seen[_normalize_url(article.url)] = today
    return seen
