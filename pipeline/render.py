"""
Email rendering: Jinja2 template + premailer CSS inlining.

premailer.transform() converts all <style> block CSS to inline style=""
attributes. This is required because Gmail strips <head> style blocks.
"""
import os
from datetime import datetime

from jinja2 import Environment, FileSystemLoader
from premailer import transform

from models import SummarizedArticle

# Load templates relative to repo root (where orchestrator.py will run from)
_TEMPLATE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "templates")
env = Environment(loader=FileSystemLoader(_TEMPLATE_DIR), autoescape=True)

# Section display order — controls the order of sections in the email
SECTION_ORDER = ["Personal Blogs", "WSJ", "The Information", "Anthropic"]


def render_email(articles: list[SummarizedArticle]) -> tuple[str, str]:
    """
    Render summarized articles into (html_body, text_body).

    Args:
        articles: Summarized articles from all sources.

    Returns:
        Tuple of (html_body, text_body). html_body has all CSS inlined.
    """
    # Group articles by source_category, preserving section order
    sections: dict[str, list[SummarizedArticle]] = {cat: [] for cat in SECTION_ORDER}
    for article in articles:
        cat = article.source_category
        if cat not in sections:
            sections[cat] = []  # Handle any unexpected categories
        sections[cat].append(article)

    # Remove empty sections (EMAIL-06 requirement — clean suppression in Phase 2)
    sections = {cat: arts for cat, arts in sections.items() if arts}

    today = datetime.now().strftime("%B %-d, %Y")

    template = env.get_template("digest.html.j2")
    raw_html = template.render(sections=sections, date=today)
    inlined_html = transform(raw_html)  # Inline all CSS for Gmail compatibility

    # Plain-text fallback
    text_lines = [f"AI Briefing — {today}", "=" * 40]
    for category, arts in sections.items():
        text_lines.append(f"\n{category.upper()}")
        text_lines.append("-" * len(category))
        for a in arts:
            text_lines.append(f"\n{a.title}")
            text_lines.append(f"  {a.source_name} | {a.published_at.strftime('%b %-d, %Y')}")
            text_lines.append(f"  {a.url}")
            if not a.summarization_failed and a.summary:
                text_lines.append(f"  {a.summary}")
            if not a.summarization_failed and a.why_it_matters:
                text_lines.append(f"  Why it matters: {a.why_it_matters}")
    text_lines.append(f"\n---\nGenerated {today}")
    text_body = "\n".join(text_lines)

    return inlined_html, text_body
