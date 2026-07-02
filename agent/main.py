"""
Main entry point for the Marrakech Daily editorial AI agent.

Run modes:
  python agent/main.py             → daily automated run (20 articles)
  python agent/main.py --dry-run   → scrape + generate but do NOT save/commit
  python agent/main.py --limit N   → override article limit
"""

from __future__ import annotations

import argparse
import logging
import random
import sys
import time
from pathlib import Path

# Add agent/ dir to path so relative imports work
sys.path.insert(0, str(Path(__file__).parent))

from config import MAX_ARTICLES_PER_RUN, MAX_PER_SOURCE, LOGS_DIR
from scraper import scrape_all_sources, enrich_with_content
from ai_pipeline import rewrite_article
from deduplicator import Deduplicator
from publisher import append_article, load_articles
from site_builder import build_site

# ── Logging setup ──────────────────────────────────────────────────────────────

def setup_logging(dry_run: bool = False) -> None:
    from datetime import datetime
    log_file = LOGS_DIR / f"agent_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    LOGS_DIR.mkdir(parents=True, exist_ok=True)

    fmt = "%(asctime)s %(levelname)-8s %(name)s — %(message)s"
    handlers: list[logging.Handler] = [logging.StreamHandler(sys.stdout)]
    if not dry_run:
        handlers.append(logging.FileHandler(log_file, encoding="utf-8"))

    logging.basicConfig(level=logging.INFO, format=fmt, handlers=handlers)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("openai").setLevel(logging.WARNING)


log = logging.getLogger(__name__)


# ── Main pipeline ──────────────────────────────────────────────────────────────

def run(limit: int = MAX_ARTICLES_PER_RUN, dry_run: bool = False) -> int:
    """
    Full editorial pipeline.
    Returns the number of articles successfully published.
    """
    log.info("═" * 60)
    log.info("Marrakech Daily Agent starting (limit=%d, dry_run=%s)", limit, dry_run)
    log.info("═" * 60)

    dedup = Deduplicator()
    published_count = 0

    # Step 1: Scrape all sources
    log.info("── Step 1: Scraping news sources ──")
    raw_articles = scrape_all_sources()
    if not raw_articles:
        log.error("No articles scraped — aborting run")
        return 0

    # Shuffle to avoid always favouring the same source
    random.shuffle(raw_articles)

    # Step 2: Filter duplicates before fetching full content (saves bandwidth)
    log.info("── Step 2: Pre-filtering duplicates ──")
    candidates = []
    seen_sources: dict[str, int] = {}
    for raw in raw_articles:
        src_id = raw.get("source_id", "unknown")
        if seen_sources.get(src_id, 0) >= MAX_PER_SOURCE:
            continue
        if dedup.is_duplicate(raw.get("url", ""), raw.get("title", "")):
            continue
        candidates.append(raw)
        seen_sources[src_id] = seen_sources.get(src_id, 0) + 1
        if len(candidates) >= limit * 2:   # fetch more than needed, some will fail AI
            break

    log.info("Candidates after dedup: %d", len(candidates))

    # Step 3: Enrich with full article text
    log.info("── Step 3: Fetching full article content ──")
    candidates = enrich_with_content(candidates)

    # Step 4: AI rewrite
    log.info("── Step 4: AI rewriting pipeline ──")
    for i, raw in enumerate(candidates):
        if published_count >= limit:
            break

        log.info("[%d/%d] Processing: %s", i + 1, len(candidates), raw.get("title", "?")[:70])

        article = rewrite_article(raw)
        if not article:
            log.warning("  → Skipped (AI failed or content too short)")
            continue

        # Second-pass dedup check (on AI-generated title)
        if dedup.is_duplicate(raw.get("url", ""), article["title"]):
            log.info("  → Duplicate detected post-rewrite — skipping")
            continue

        if dry_run:
            log.info("  → DRY RUN — would publish: [%s] %s",
                     article["category"], article["title"])
        else:
            append_article(article)
            dedup.mark_published(raw.get("url", ""), article["title"])

        published_count += 1

        # Polite pacing between AI calls
        if i < len(candidates) - 1:
            time.sleep(1)

    # Step 5: Persist deduplication state
    if not dry_run:
        dedup.save()

    # Step 6: Rebuild site
    if not dry_run and published_count > 0:
        log.info("── Step 5: Rebuilding site ──")
        build_site()

    log.info("═" * 60)
    log.info("Run complete — %d articles published", published_count)
    log.info("═" * 60)
    return published_count


# ── CLI ────────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Marrakech Daily Editorial AI Agent"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Scrape and generate but do NOT save articles or rebuild the site",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=MAX_ARTICLES_PER_RUN,
        help=f"Maximum articles to publish (default: {MAX_ARTICLES_PER_RUN})",
    )
    args = parser.parse_args()

    setup_logging(dry_run=args.dry_run)

    count = run(limit=args.limit, dry_run=args.dry_run)
    sys.exit(0 if count > 0 or args.dry_run else 1)


if __name__ == "__main__":
    main()
