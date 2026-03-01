"""
Tests for pipeline/filter.py — category-aware article filtering.
"""
import pytest
from datetime import datetime, timezone, timedelta
from models import RawArticle
from pipeline.filter import filter_articles, PERSONAL_BLOGS_CATEGORY

NOW = datetime.now(timezone.utc)
RECENT = NOW - timedelta(hours=1)
OLD = NOW - timedelta(hours=30)


def make_article(source_name: str, source_category: str = PERSONAL_BLOGS_CATEGORY,
                 hours_ago: float = 1.0, url_suffix: str = "") -> RawArticle:
    slug = source_name.lower().replace(' ', '-')
    return RawArticle(
        id=f"{slug}{url_suffix}",
        title=f"Article from {source_name}{url_suffix}",
        url=f"https://example.com/{slug}{url_suffix}",
        published_at=NOW - timedelta(hours=hours_ago),
        source_name=source_name,
        source_category=source_category,
        content_text="Some content",
    )


class TestRecencyFilter:
    def test_old_articles_excluded(self):
        articles = [make_article("Paul Graham", hours_ago=30)]
        result = filter_articles(articles)
        assert result == []

    def test_recent_articles_included(self):
        articles = [make_article("Paul Graham", hours_ago=1)]
        result = filter_articles(articles)
        assert len(result) == 1

    def test_boundary_at_25h_excluded(self):
        articles = [make_article("Paul Graham", hours_ago=25.1)]
        result = filter_articles(articles)
        assert result == []

    def test_boundary_just_inside_25h_included(self):
        articles = [make_article("Paul Graham", hours_ago=24.9)]
        result = filter_articles(articles)
        assert len(result) == 1


class TestBlogAuthorCap:
    def test_max_one_article_per_blogger(self):
        """Tyler Cowen posts frequently — only 1 should make it through."""
        articles = [
            make_article("Tyler Cowen", hours_ago=1, url_suffix="/a"),
            make_article("Tyler Cowen", hours_ago=2, url_suffix="/b"),
            make_article("Tyler Cowen", hours_ago=3, url_suffix="/c"),
        ]
        result = filter_articles(articles)
        assert len(result) == 1
        # Most recent wins
        assert result[0].url.endswith("/a")

    def test_different_bloggers_each_get_one(self):
        articles = [
            make_article("Paul Graham", hours_ago=1),
            make_article("Sam Altman", hours_ago=2),
            make_article("Tyler Cowen", hours_ago=3),
        ]
        result = filter_articles(articles)
        assert len(result) == 3
        names = {a.source_name for a in result}
        assert names == {"Paul Graham", "Sam Altman", "Tyler Cowen"}


class TestBlogSectionCap:
    def test_max_5_bloggers_total(self):
        """Even if 10 bloggers each have a new post, only 5 make it."""
        bloggers = [
            "Paul Graham", "Sam Altman", "Tyler Cowen",
            "Scott Alexander", "Ben Kuhn", "Gwern Branwen",
            "Nabeel Qureshi", "Tom Tunguz", "Henrik Karlsson", "Kevin Kwok",
        ]
        articles = [make_article(name, hours_ago=i + 1) for i, name in enumerate(bloggers)]
        result = filter_articles(articles)
        assert len(result) == 5

    def test_fewer_than_5_bloggers_all_included(self):
        bloggers = ["Paul Graham", "Sam Altman", "Tyler Cowen"]
        articles = [make_article(name, hours_ago=i + 1) for i, name in enumerate(bloggers)]
        result = filter_articles(articles)
        assert len(result) == 3

    def test_5_bloggers_picks_most_recent(self):
        """When capped at 5, the 5 most recently published bloggers win."""
        bloggers = [f"Blogger{i}" for i in range(10)]
        # Bloggers 0-4 posted 1-5h ago, bloggers 5-9 posted 6-10h ago
        articles = [make_article(name, hours_ago=i + 1) for i, name in enumerate(bloggers)]
        result = filter_articles(articles)
        included = {a.source_name for a in result}
        assert included == {"Blogger0", "Blogger1", "Blogger2", "Blogger3", "Blogger4"}


class TestNonBlogSources:
    def test_wsj_allows_up_to_5(self):
        articles = [
            make_article(f"WSJ", source_category="WSJ", hours_ago=i + 1, url_suffix=f"/{i}")
            for i in range(7)
        ]
        result = filter_articles(articles)
        assert len(result) == 5

    def test_the_information_allows_up_to_5(self):
        articles = [
            make_article("The Information", source_category="The Information",
                         hours_ago=i + 1, url_suffix=f"/{i}")
            for i in range(3)
        ]
        result = filter_articles(articles)
        assert len(result) == 3

    def test_anthropic_allows_up_to_5(self):
        articles = [
            make_article("Anthropic", source_category="Anthropic",
                         hours_ago=i + 1, url_suffix=f"/{i}")
            for i in range(6)
        ]
        result = filter_articles(articles)
        assert len(result) == 5

    def test_non_blog_sources_independent_of_blog_cap(self):
        """WSJ articles don't count toward the 5-blogger cap."""
        blog_articles = [make_article(f"Blogger{i}", hours_ago=i + 1) for i in range(5)]
        wsj_articles = [
            make_article("WSJ", source_category="WSJ", hours_ago=i + 1, url_suffix=f"/{i}")
            for i in range(3)
        ]
        result = filter_articles(blog_articles + wsj_articles)
        blog_results = [a for a in result if a.source_category == PERSONAL_BLOGS_CATEGORY]
        wsj_results = [a for a in result if a.source_category == "WSJ"]
        assert len(blog_results) == 5
        assert len(wsj_results) == 3


class TestMixedContent:
    def test_empty_input_returns_empty(self):
        assert filter_articles([]) == []

    def test_all_old_returns_empty(self):
        articles = [make_article("Paul Graham", hours_ago=30)]
        assert filter_articles(articles) == []

    def test_sorted_newest_first(self):
        articles = [
            make_article("Paul Graham", hours_ago=3),
            make_article("Sam Altman", hours_ago=1),
            make_article("Tyler Cowen", hours_ago=2),
        ]
        result = filter_articles(articles)
        pub_times = [a.published_at for a in result]
        assert pub_times == sorted(pub_times, reverse=True)
