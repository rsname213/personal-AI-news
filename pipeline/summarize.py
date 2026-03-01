"""
Article summarization via Claude Haiku.

Uses sequential client.messages.create() with prompt caching (NOT Batch API).
Batch API is async and can take up to 1 hour — incompatible with 30-min Actions timeout.
Prompt caching on the system prompt reduces cost ~90% after the first call in a run.
"""
import os
import re
import anthropic
from models import FilteredArticle, SummarizedArticle

SYSTEM_PROMPT = """You are a concise AI/tech newsletter editor. For each article, output exactly:

<summary>2-4 sentences explaining what the article covers. Be specific and factual. No "the author argues" constructions. No preamble.</summary>
<why_it_matters>1-2 sentences on the non-obvious significance for AI/tech practitioners. Focus on implications, not restatement.</why_it_matters>

Output only the two XML tags above. Nothing else."""

MODEL = "claude-haiku-4-5-20251001"
MAX_TOKENS = 400
CONTENT_TRUNCATE = 3000  # Truncate article content to reduce token cost


def summarize_articles(articles: list[FilteredArticle]) -> list[SummarizedArticle]:
    """
    Summarize all articles sequentially. Returns one SummarizedArticle per input.
    Never raises — failed summaries return with summarization_failed=True.
    """
    if not articles:
        return []

    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    results = []

    for i, article in enumerate(articles, 1):
        print(f"[...] Summarizing {i}/{len(articles)}: {article.title[:60]}")
        result = _summarize_one(client, article)
        results.append(result)

    succeeded = sum(1 for r in results if not r.summarization_failed)
    failed = len(results) - succeeded
    print(f"[OK] Summarization: {succeeded} succeeded, {failed} failed")
    return results


def _summarize_one(client: anthropic.Anthropic, article: FilteredArticle) -> SummarizedArticle:
    """Summarize a single article. Returns SummarizedArticle with summarization_failed=True on error."""
    try:
        response = client.messages.create(
            model=MODEL,
            max_tokens=MAX_TOKENS,
            system=[
                {
                    "type": "text",
                    "text": SYSTEM_PROMPT,
                    "cache_control": {"type": "ephemeral"},  # Cache for 5 min; ~90% cost savings after first call
                }
            ],
            messages=[
                {
                    "role": "user",
                    "content": (
                        f"<article>\n"
                        f"Title: {article.title}\n"
                        f"Source: {article.source_name}\n\n"
                        f"Content:\n{article.content_text[:CONTENT_TRUNCATE]}\n"
                        f"</article>"
                    ),
                }
            ],
        )
        text = response.content[0].text

        # Parse XML-tagged sections from response
        summary_match = re.search(r"<summary>(.*?)</summary>", text, re.DOTALL)
        why_match = re.search(r"<why_it_matters>(.*?)</why_it_matters>", text, re.DOTALL)

        summary = summary_match.group(1).strip() if summary_match else text[:300].strip()
        why_it_matters = why_match.group(1).strip() if why_match else ""

        return SummarizedArticle(
            **{k: v for k, v in article.__dict__.items()},
            summary=summary,
            why_it_matters=why_it_matters,
            summarization_failed=False,
        )

    except Exception as e:
        print(f"[WARN] Summarization failed for '{article.title[:50]}': {e}")
        return SummarizedArticle(
            **{k: v for k, v in article.__dict__.items()},
            summary="",
            why_it_matters="",
            summarization_failed=True,
        )
