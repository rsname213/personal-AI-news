"""
Article filtering: 25-hour recency window with smart per-category caps.

Rules:
  Personal Blogs — max 1 article per blogger, max 5 bloggers total
  All other sources (WSJ, The Information, Anthropic) — max 5 per source

Uses 25 hours (not 24) to absorb GitHub Actions cron scheduling delays
of up to ~1 hour without silently dropping recent articles.
"""
from collections import defaultdict
from datetime import datetime, timezone, timedelta
from models import RawArticle, FilteredArticle

PERSONAL_BLOGS_CATEGORY = "Personal Blogs"
BLOG_SECTION_CAP = 5   # max distinct bloggers in the digest
BLOG_AUTHOR_CAP = 1    # max articles per individual blogger
DEFAULT_SOURCE_CAP = 5  # max articles for non-blog sources (WSJ, The Info, Anthropic)


def filter_articles(
    articles: list[RawArticle],
    hours: int = 25,
) -> list[FilteredArticle]:
    """
    Returns only recent articles, applying category-aware caps.

    Personal Blogs: 1 article per blogger, 5 bloggers max.
    Other sources:  5 articles per source.

    Args:
        articles: All raw articles from all fetchers.
        hours: Recency window in hours. Default 25 (absorbs Actions delay).

    Returns:
        FilteredArticle list, sorted by recency (newest first).
    """
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)

    # Step 1: Filter to recent articles only
    recent = [a for a in articles if a.published_at >= cutoff]

    # Step 2: Sort by recency (newest first) so caps keep the most recent
    recent.sort(key=lambda a: a.published_at, reverse=True)

    # Step 3: Apply caps
    author_counts: dict[str, int] = defaultdict(int)   # per source_name
    source_counts: dict[str, int] = defaultdict(int)   # per source_category (non-blog)
    blog_section_count = 0
    filtered: list[FilteredArticle] = []

    for article in recent:
        if article.source_category == PERSONAL_BLOGS_CATEGORY:
            # Rule: max 1 per blogger AND max 5 bloggers total
            if (author_counts[article.source_name] < BLOG_AUTHOR_CAP
                    and blog_section_count < BLOG_SECTION_CAP):
                filtered.append(FilteredArticle(**article.__dict__))
                author_counts[article.source_name] += 1
                blog_section_count += 1
        else:
            # Rule: max 5 per source (WSJ, The Information, Anthropic)
            if source_counts[article.source_category] < DEFAULT_SOURCE_CAP:
                filtered.append(FilteredArticle(**article.__dict__))
                source_counts[article.source_category] += 1

    total_raw = len(articles)
    total_filtered = len(filtered)
    print(
        f"[OK] Filter: {total_raw} raw -> {total_filtered} kept "
        f"(blogs: {blog_section_count} bloggers, 1 each; "
        f"other sources: up to {DEFAULT_SOURCE_CAP} each)"
    )
    return filtered
