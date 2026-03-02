"""
AI Newsletter Pipeline Orchestrator

Runs the complete pipeline:
  1. Fetch articles from all sources (fail-soft per source)
  2. Filter to recent articles (7-day window, 5 per source cap)
  3. Summarize each article with Claude Haiku
  4. Render HTML + plain text email
  5. Send via Gmail SMTP

Exit codes:
  0 — Email sent successfully
  1 — Gmail SMTP failure (Actions run marked red)
"""
import os
import sys

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # dotenv optional — env vars may already be set (e.g. GitHub Actions)

from fetchers.rss import fetch_all as fetch_rss_all
from fetchers.paul_graham import fetch as fetch_paul_graham
from fetchers.gwern import fetch as fetch_gwern
from fetchers.blog_scrapers import fetch_boz, fetch_calv, fetch_maxhodak

from pipeline.filter import filter_articles
from pipeline.deduplicate import (
    load_seen_urls, save_seen_urls, purge_old_entries,
    filter_duplicates, mark_as_seen,
)
from pipeline.summarize import summarize_articles
from pipeline.render import render_email
from pipeline.send import send_email, build_subject


def _check_env() -> None:
    """Validate required environment variables before starting. Fail fast with clear message."""
    required = ["ANTHROPIC_API_KEY", "GMAIL_USER", "GMAIL_APP_PASSWORD"]
    missing = [var for var in required if not os.environ.get(var)]
    if missing:
        print(f"[ERROR] Missing required environment variables: {', '.join(missing)}")
        print("  Copy .env.example to .env and fill in your values for local runs.")
        print("  For GitHub Actions, ensure all variables are set in repository secrets.")
        sys.exit(1)


def collect_all() -> list:
    """
    Fetch from all sources with fail-soft error handling.
    Any source that raises returns [] and logs a warning — never blocks email delivery.
    """
    FETCHERS = [
        (fetch_rss_all, "RSS feeds"),
        (fetch_paul_graham, "Paul Graham"),
        (fetch_gwern, "Gwern Branwen"),
        (fetch_boz, "Andrew Bosworth"),
        (fetch_calv, "Calvin French-Owen"),
        (fetch_maxhodak, "Max Hodak"),
    ]

    all_articles = []
    for fetch_fn, source_name in FETCHERS:
        try:
            articles = fetch_fn()
            count = len(articles)
            if count == 0:
                print(f"[WARN] {source_name}: returned 0 articles — check feed health")
            all_articles.extend(articles)
        except Exception as e:
            # Individual source failure must never block email delivery
            print(f"[WARN] {source_name} fetch failed: {e}")
            # Continue — partial email is better than no email

    return all_articles


def main() -> None:
    print("=" * 50)
    print("AI Newsletter Pipeline")
    print("=" * 50)

    # Pre-flight check
    _check_env()

    # Stage 1: Fetch
    print("\n[Stage 1] Fetching articles from all sources...")
    raw_articles = collect_all()
    print(f"[OK] Total raw articles collected: {len(raw_articles)}")

    # Stage 2: Filter
    print("\n[Stage 2] Filtering to recent articles...")
    filtered = filter_articles(raw_articles)
    print(f"[OK] Articles after filter: {len(filtered)}")

    # Stage 2b: Deduplicate — remove articles seen in last 7 days
    print("\n[Stage 2b] Deduplicating against seen URLs...")
    seen = purge_old_entries(load_seen_urls())
    filtered, dupes = filter_duplicates(filtered, seen)
    if dupes:
        print(f"[OK] Dedup: {len(dupes)} duplicate(s) removed, {len(filtered)} article(s) remain")
    else:
        print(f"[OK] Dedup: no duplicates found, {len(filtered)} article(s) proceed")

    if not filtered:
        print("[WARN] No articles passed the filter — sending empty digest")
        # Continue — send the email even if empty (subject + date still useful for monitoring)

    # Stage 3: Summarize
    print(f"\n[Stage 3] Summarizing {len(filtered)} articles with Claude Sonnet 4.6...")
    summarized = summarize_articles(filtered)

    # Stage 4: Render
    print("\n[Stage 4] Rendering email...")
    html_body, text_body = render_email(summarized)
    print(f"[OK] HTML size: {len(html_body):,} bytes (Gmail clips at 102KB)")
    if len(html_body) > 102_000:
        print(f"[WARN] HTML exceeds 102KB Gmail clip threshold ({len(html_body):,} bytes)")

    # Stage 5: Send
    print("\n[Stage 5] Sending via Gmail SMTP...")
    subject = build_subject()
    send_email(subject, html_body, text_body)

    # Update seen URLs — only after successful send to avoid false-marking on SMTP failure
    seen = mark_as_seen(summarized, seen)
    save_seen_urls(seen)
    print(f"[OK] Seen URLs updated ({len(seen)} total entries)")

    print("\n" + "=" * 50)
    print("Pipeline complete.")
    print("=" * 50)


if __name__ == "__main__":
    main()
