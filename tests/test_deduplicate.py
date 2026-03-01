"""
Tests for pipeline/deduplicate.py

TDD: These tests are written before the implementation.
"""
import json
import os
import tempfile
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, MagicMock

import pytest

# We'll test via public API only (no _normalize_url direct import for private fn,
# but we test its behavior through filter_duplicates and mark_as_seen)
from pipeline.deduplicate import (
    load_seen_urls,
    save_seen_urls,
    purge_old_entries,
    filter_duplicates,
    mark_as_seen,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_article(url: str):
    """Minimal article-like object for testing."""
    obj = MagicMock()
    obj.url = url
    return obj


# ---------------------------------------------------------------------------
# _normalize_url (tested via filter_duplicates / mark_as_seen behaviour)
# ---------------------------------------------------------------------------

class TestNormalizeUrl:
    """Test URL normalization via filter_duplicates (strips UTM, lowercases, removes trailing slash)."""

    def test_utm_params_stripped(self):
        """Articles with UTM params should match the seen URL without UTM params."""
        # If the clean URL is "seen", the UTM-laden version should be treated as a dupe
        clean_url = "https://example.com/article"
        utm_url = "https://example.com/article?utm_source=twitter&utm_medium=social"
        seen = {"https://example.com/article": "2026-02-28"}
        article_with_utm = make_article(utm_url)
        new_articles, dupes = filter_duplicates([article_with_utm], seen)
        assert len(dupes) == 1, "UTM-laden URL should match the clean seen URL"
        assert len(new_articles) == 0

    def test_utm_all_params_stripped(self):
        """All 5 UTM params are stripped."""
        utm_url = (
            "https://example.com/post"
            "?utm_source=email&utm_medium=newsletter&utm_campaign=weekly"
            "&utm_term=ai&utm_content=header"
        )
        seen = {"https://example.com/post": "2026-02-28"}
        article = make_article(utm_url)
        new_articles, dupes = filter_duplicates([article], seen)
        assert len(dupes) == 1

    def test_scheme_host_lowercased(self):
        """Uppercase scheme+host is normalized to lowercase."""
        url = "HTTPS://Example.COM/path"
        seen = {"https://example.com/path": "2026-02-28"}
        article = make_article(url)
        new_articles, dupes = filter_duplicates([article], seen)
        assert len(dupes) == 1, "URL with uppercase scheme+host should match lowercase seen entry"

    def test_trailing_slash_stripped(self):
        """Trailing slash on path is stripped."""
        url = "https://example.com/article/"
        seen = {"https://example.com/article": "2026-02-28"}
        article = make_article(url)
        new_articles, dupes = filter_duplicates([article], seen)
        assert len(dupes) == 1, "Trailing slash should be stripped before lookup"

    def test_fragment_dropped(self):
        """Fragment (#section) is dropped during normalization."""
        url = "https://example.com/article#intro"
        seen = {"https://example.com/article": "2026-02-28"}
        article = make_article(url)
        new_articles, dupes = filter_duplicates([article], seen)
        assert len(dupes) == 1, "Fragment should be dropped"

    def test_non_utm_query_params_kept(self):
        """Non-UTM query params are retained (sorted for stability)."""
        url_a = "https://example.com/search?q=ai&page=2"
        url_b = "https://example.com/search?page=2&q=ai"  # same params, different order
        seen = {url_a: "2026-02-28"}  # Won't match url_b because load_seen_urls stores normalized
        # Both should normalize to the same URL, so url_b should be a dupe if url_a is in seen
        # We need to use mark_as_seen to populate the seen dict with normalized URLs
        article_a = make_article(url_a)
        seen_after = mark_as_seen([article_a], {})
        article_b = make_article(url_b)
        new_articles, dupes = filter_duplicates([article_b], seen_after)
        assert len(dupes) == 1, "Same query params in different order should match after normalization"


# ---------------------------------------------------------------------------
# load_seen_urls
# ---------------------------------------------------------------------------

class TestLoadSeenUrls:
    def test_returns_empty_dict_when_file_missing(self, tmp_path):
        missing_path = str(tmp_path / ".seen_urls")
        with patch("pipeline.deduplicate.SEEN_URLS_PATH", missing_path):
            result = load_seen_urls()
        assert result == {}

    def test_returns_empty_dict_on_corrupt_json(self, tmp_path):
        path = tmp_path / ".seen_urls"
        path.write_text("NOT VALID JSON }{")
        with patch("pipeline.deduplicate.SEEN_URLS_PATH", str(path)):
            result = load_seen_urls()
        assert result == {}

    def test_returns_dict_when_valid_json(self, tmp_path):
        data = {"https://example.com/article": "2026-02-28"}
        path = tmp_path / ".seen_urls"
        path.write_text(json.dumps(data))
        with patch("pipeline.deduplicate.SEEN_URLS_PATH", str(path)):
            result = load_seen_urls()
        assert result == data

    def test_returns_empty_dict_on_os_error(self, tmp_path):
        """Simulates a read permission error."""
        with patch("pipeline.deduplicate.SEEN_URLS_PATH", "/nonexistent/path/.seen_urls"):
            result = load_seen_urls()
        assert result == {}


# ---------------------------------------------------------------------------
# save_seen_urls
# ---------------------------------------------------------------------------

class TestSaveSeenUrls:
    def test_writes_indented_json(self, tmp_path):
        path = tmp_path / ".seen_urls"
        data = {"https://example.com": "2026-02-28"}
        with patch("pipeline.deduplicate.SEEN_URLS_PATH", str(path)):
            save_seen_urls(data)
        content = path.read_text()
        loaded = json.loads(content)
        assert loaded == data
        # Check indented (contains newline + spaces)
        assert "\n" in content

    def test_round_trip(self, tmp_path):
        path = tmp_path / ".seen_urls"
        data = {
            "https://example.com/a": "2026-02-25",
            "https://example.com/b": "2026-02-28",
        }
        with patch("pipeline.deduplicate.SEEN_URLS_PATH", str(path)):
            save_seen_urls(data)
            loaded = load_seen_urls()
        assert loaded == data


# ---------------------------------------------------------------------------
# purge_old_entries
# ---------------------------------------------------------------------------

class TestPurgeOldEntries:
    def _today(self):
        return datetime.now(timezone.utc).date()

    def test_keeps_entries_within_window(self):
        today = self._today()
        seen = {
            "https://example.com/recent": (today - timedelta(days=3)).isoformat(),
            "https://example.com/today": today.isoformat(),
        }
        result = purge_old_entries(seen, window_days=7)
        assert "https://example.com/recent" in result
        assert "https://example.com/today" in result

    def test_removes_entries_older_than_window(self):
        today = self._today()
        seen = {
            "https://example.com/old": (today - timedelta(days=8)).isoformat(),
            "https://example.com/borderline": (today - timedelta(days=7)).isoformat(),
        }
        result = purge_old_entries(seen, window_days=7)
        assert "https://example.com/old" not in result, "8-day-old entry should be purged"
        assert "https://example.com/borderline" in result, "7-day-old entry should be kept"

    def test_empty_dict_returns_empty(self):
        result = purge_old_entries({})
        assert result == {}

    def test_custom_window_days(self):
        today = self._today()
        seen = {
            "https://example.com/three_days_ago": (today - timedelta(days=3)).isoformat(),
        }
        result = purge_old_entries(seen, window_days=2)
        assert "https://example.com/three_days_ago" not in result


# ---------------------------------------------------------------------------
# filter_duplicates
# ---------------------------------------------------------------------------

class TestFilterDuplicates:
    def test_new_article_passes_through(self):
        article = make_article("https://example.com/new")
        new_articles, dupes = filter_duplicates([article], {})
        assert len(new_articles) == 1
        assert len(dupes) == 0

    def test_seen_article_is_filtered(self):
        article = make_article("https://example.com/old")
        seen = {"https://example.com/old": "2026-02-28"}
        new_articles, dupes = filter_duplicates([article], seen)
        assert len(new_articles) == 0
        assert len(dupes) == 1

    def test_split_new_and_dupes(self):
        a1 = make_article("https://example.com/new")
        a2 = make_article("https://example.com/old")
        seen = {"https://example.com/old": "2026-02-28"}
        new_articles, dupes = filter_duplicates([a1, a2], seen)
        assert len(new_articles) == 1
        assert len(dupes) == 1
        assert new_articles[0].url == "https://example.com/new"
        assert dupes[0].url == "https://example.com/old"

    def test_empty_articles_returns_empty_lists(self):
        new_articles, dupes = filter_duplicates([], {"https://example.com/x": "2026-02-28"})
        assert new_articles == []
        assert dupes == []

    def test_empty_seen_passes_all(self):
        articles = [make_article(f"https://example.com/{i}") for i in range(5)]
        new_articles, dupes = filter_duplicates(articles, {})
        assert len(new_articles) == 5
        assert len(dupes) == 0


# ---------------------------------------------------------------------------
# mark_as_seen
# ---------------------------------------------------------------------------

class TestMarkAsSeen:
    def test_adds_todays_date_for_each_article(self):
        today = datetime.now(timezone.utc).date().isoformat()
        articles = [
            make_article("https://example.com/a"),
            make_article("https://example.com/b"),
        ]
        seen = mark_as_seen(articles, {})
        assert "https://example.com/a" in seen
        assert "https://example.com/b" in seen
        assert seen["https://example.com/a"] == today
        assert seen["https://example.com/b"] == today

    def test_does_not_overwrite_existing_entries(self):
        """Existing seen entries for other URLs are preserved."""
        existing = {"https://example.com/existing": "2026-02-25"}
        articles = [make_article("https://example.com/new")]
        seen = mark_as_seen(articles, existing)
        assert "https://example.com/existing" in seen
        assert seen["https://example.com/existing"] == "2026-02-25"

    def test_normalizes_url_when_marking(self):
        """mark_as_seen normalizes URL so subsequent filter_duplicates works."""
        utm_url = "https://example.com/article?utm_source=twitter"
        article = make_article(utm_url)
        seen = mark_as_seen([article], {})
        # The stored key should be the normalized URL
        assert "https://example.com/article" in seen, (
            "mark_as_seen should store normalized URL so future filter_duplicates can match"
        )

    def test_returns_updated_dict(self):
        articles = [make_article("https://example.com/x")]
        result = mark_as_seen(articles, {})
        assert isinstance(result, dict)
        assert len(result) == 1

    def test_empty_articles_returns_seen_unchanged(self):
        existing = {"https://example.com/a": "2026-02-28"}
        result = mark_as_seen([], existing)
        assert result == existing
