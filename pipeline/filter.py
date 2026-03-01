"""
Article filtering: 25-hour recency window + 5-item per-source cap.

Uses 25 hours (not 24) to absorb GitHub Actions cron scheduling delays
of up to ~1 hour without silently dropping recent articles.
"""
from collections import defaultdict
from datetime import datetime, timezone, timedelta
from models import RawArticle, FilteredArticle


def filter_articles(
    articles: list[RawArticle],
    hours: int = 25,
    cap: int = 5,
) -> list[FilteredArticle]:
    """
    Returns only recent articles, capped per source.

    Args:
        articles: All raw articles from all fetchers.
        hours: Recency window in hours. Default 25 (absorbs Actions delay).
        cap: Max articles per source_name. Default 5.

    Returns:
        FilteredArticle list, sorted by recency (newest first), capped per source.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)

    # Step 1: Filter to recent articles only
    recent = [a for a in articles if a.published_at >= cutoff]

    # Step 2: Sort by recency (newest first) so cap keeps the most recent
    recent.sort(key=lambda a: a.published_at, reverse=True)

    # Step 3: Apply per-source cap
    counts: dict[str, int] = defaultdict(int)
    filtered: list[FilteredArticle] = []
    for article in recent:
        if counts[article.source_name] < cap:
            filtered.append(FilteredArticle(**article.__dict__))
            counts[article.source_name] += 1

    total_raw = len(articles)
    total_filtered = len(filtered)
    print(f"[OK] Filter: {total_raw} raw articles -> {total_filtered} after 25h filter + 5-cap")
    return filtered
