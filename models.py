"""
Data models for the AI Newsletter pipeline.

Flow: RawArticle -> FilteredArticle -> SummarizedArticle
Each stage reads the previous type and produces the next type.
"""
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class RawArticle:
    """Article as fetched from an RSS feed or HTML scraper."""
    id: str                  # Stable hash: hashlib.md5(url.encode()).hexdigest()
    url: str                 # Direct link to article
    title: str               # Article title
    content_text: str        # RSS feed content or scraped body text (may be empty)
    published_at: datetime   # UTC-aware datetime (never naive)
    source_name: str         # Display name, e.g. "Ben Kuhn", "WSJ", "Anthropic"
    source_category: str     # Section header: "Personal Blogs" | "WSJ" | "The Information" | "Anthropic"


@dataclass
class FilteredArticle(RawArticle):
    """Article that has passed recency and per-source cap filters."""
    pass  # Inherits all fields from RawArticle; filter.py selects from RawArticle list


@dataclass
class SummarizedArticle(FilteredArticle):
    """Article with Claude Haiku summary and why-it-matters annotation."""
    summary: str = ""
    why_it_matters: str = ""
    summarization_failed: bool = False  # True = API call failed; render without summary
