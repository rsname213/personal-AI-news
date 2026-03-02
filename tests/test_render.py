"""
Tests for pipeline/render.py — email rendering and CSS inlining.

Covers:
- Basic render with no articles
- Dark mode @media block survives premailer
- CSS inlining (style= attributes present on elements)
- Failed-summary fallback rendering
- HTML size under 102KB (EMAIL-04)
- Style block size under 8KB (Gmail limit)
- EMAIL-06: empty sections produce no section-label elements
"""
import re
from datetime import datetime, timezone

import pytest

from models import SummarizedArticle


def make_article(
    title="Test Article",
    url="https://example.com/test",
    source_name="Test Blog",
    source_category="Personal Blogs",
    summary="A test summary.",
    why_it_matters="It matters.",
    summarization_failed=False,
):
    return SummarizedArticle(
        id="test-id-001",
        url=url,
        title=title,
        content_text="",
        published_at=datetime(2026, 3, 1, 10, 0, tzinfo=timezone.utc),
        source_name=source_name,
        source_category=source_category,
        summary=summary,
        why_it_matters=why_it_matters,
        summarization_failed=summarization_failed,
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestRenderEmpty:
    """render_email([]) — no articles."""

    def test_returns_tuple(self):
        from pipeline.render import render_email
        result = render_email([])
        assert isinstance(result, tuple)
        assert len(result) == 2

    def test_html_contains_header(self):
        from pipeline.render import render_email
        html, _ = render_email([])
        assert "AI Briefing" in html

    def test_text_contains_header(self):
        from pipeline.render import render_email
        _, text = render_email([])
        assert "AI Briefing" in text

    def test_css_was_inlined(self):
        """At least one style= attribute must be present (premailer did its job)."""
        from pipeline.render import render_email
        html, _ = render_email([])
        assert 'style=' in html, "No inline style= attributes found — premailer may not have run"


class TestRenderWithArticles:
    """render_email with normal articles."""

    def test_article_title_appears(self):
        from pipeline.render import render_email
        article = make_article(title="My AI Discovery")
        html, _ = render_email([article])
        assert "My AI Discovery" in html

    def test_article_summary_appears(self):
        from pipeline.render import render_email
        article = make_article(summary="The world is changing fast.")
        html, _ = render_email([article])
        assert "The world is changing fast." in html

    def test_article_why_appears(self):
        from pipeline.render import render_email
        article = make_article(why_it_matters="Impacts everyone who uses AI.")
        html, _ = render_email([article])
        assert "Impacts everyone who uses AI." in html

    def test_article_url_in_link(self):
        from pipeline.render import render_email
        article = make_article(url="https://example.com/specific-page")
        html, _ = render_email([article])
        assert "https://example.com/specific-page" in html


class TestRenderFailedSummary:
    """render_email with summarization_failed=True."""

    def test_failed_summary_renders_fallback(self):
        from pipeline.render import render_email
        article = make_article(summarization_failed=True, summary="", why_it_matters="")
        html, _ = render_email([article])
        assert "Read article" in html, "Missing fallback link for failed summary"

    def test_failed_summary_does_not_crash(self):
        from pipeline.render import render_email
        article = make_article(summarization_failed=True, summary="", why_it_matters="")
        html, text = render_email([article])
        assert isinstance(html, str)
        assert isinstance(text, str)
        assert len(html) > 100


class TestHtmlSize:
    """HTML must be under 102KB (EMAIL-04)."""

    def test_empty_render_size(self):
        from pipeline.render import render_email
        html, _ = render_email([])
        size = len(html.encode("utf-8"))
        assert size < 102_000, f"HTML too large: {size} bytes (limit: 102,000)"

    def test_full_render_size(self):
        """10 articles across all sections — realistic worst case."""
        from pipeline.render import render_email
        articles = [
            make_article(
                title=f"Article {i}: " + "A" * 60,
                summary="S" * 300,
                why_it_matters="W" * 200,
                source_category=cat,
            )
            for i, cat in enumerate(
                ["Personal Blogs"] * 3 + ["WSJ"] * 3 + ["The Information"] * 2 + ["Anthropic"] * 2
            )
        ]
        html, _ = render_email(articles)
        size = len(html.encode("utf-8"))
        assert size < 102_000, f"HTML too large: {size} bytes (limit: 102,000)"


class TestStyleBlockSize:
    """Remaining <style> block after premailer must be under 8KB (Gmail limit)."""

    def test_style_block_size(self):
        from pipeline.render import render_email
        html, _ = render_email([])
        style_blocks = re.findall(r"<style[^>]*>(.*?)</style>", html, re.DOTALL)
        total_size = sum(len(b) for b in style_blocks)
        assert total_size < 8192, (
            f"Style block total {total_size} chars exceeds 8KB Gmail limit"
        )


class TestEmptySectionSuppression:
    """EMAIL-06: sections with no articles must not appear in output."""

    def test_empty_render_has_no_section_label_elements(self):
        """With no articles, no <p class='section-label'> should be in output."""
        from pipeline.render import render_email
        html, _ = render_email([])
        # After premailer, inline styles replace class attributes on structural elements.
        # The section-label class should not appear as an element attribute in final output.
        # We check that no <p ...section-label... is present as an element (not in <style> blocks).
        # Strip style blocks first, then search.
        html_no_styles = re.sub(r"<style[^>]*>.*?</style>", "", html, flags=re.DOTALL)
        assert "section-label" not in html_no_styles, (
            "Empty render contains section-label element — empty section suppression broken"
        )

    def test_articles_with_empty_category_no_header(self):
        """render_email filters empty categories; no section header for empty list."""
        from pipeline.render import render_email
        # render.py removes empty sections before passing to template,
        # so passing an article with a category different from any in SECTION_ORDER
        # won't produce a broken section. Test the main path: no articles = no sections.
        html, _ = render_email([])
        html_no_styles = re.sub(r"<style[^>]*>.*?</style>", "", html, flags=re.DOTALL)
        # Verify: none of the 4 section names appear as element text
        for section_name in ["Personal Blogs", "WSJ", "The Information", "Anthropic"]:
            assert section_name not in html_no_styles, (
                f"Section '{section_name}' appears even with no articles in that section"
            )
