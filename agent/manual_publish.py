"""
Manual publish mode for Marrakech Daily.

Usage (locally):
    python agent/manual_publish.py "New luxury hotel opens in Marrakech"
    python agent/manual_publish.py "Marrakech airport expansion"

Usage (via GitHub Actions workflow_dispatch):
    Trigger the "manual-publish" workflow from the Actions tab and enter the headline.

This script:
  1. Calls the AI pipeline to generate a full article from the headline
  2. Saves the article to _data/articles.json
  3. Rebuilds index.html
  4. Exits 0 on success
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from config import LOGS_DIR
from ai_pipeline import rewrite_from_headline
from deduplicator import Deduplicator
from publisher import append_article
from site_builder import build_site


def setup_logging() -> None:
    from datetime import datetime
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    log_file = LOGS_DIR / f"manual_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    fmt = "%(asctime)s %(levelname)-8s %(name)s — %(message)s"
    logging.basicConfig(
        level=logging.INFO,
        format=fmt,
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(log_file, encoding="utf-8"),
        ],
    )


log = logging.getLogger(__name__)


def publish_from_headline(headline: str) -> bool:
    """Generate and publish an article from a raw headline/topic. Returns True on success."""
    if not headline or not headline.strip():
        log.error("Headline cannot be empty")
        return False

    headline = headline.strip().strip('"').strip("'")
    log.info("Manual publish requested: '%s'", headline)

    dedup = Deduplicator()

    # Check for duplicate title
    if dedup.is_duplicate("", headline):
        log.warning("A very similar article already exists — publishing anyway (manual mode)")

    article = rewrite_from_headline(headline)
    if not article:
        log.error("AI pipeline failed to generate an article")
        return False

    log.info("Generated: [%s] %s", article["category"], article["title"])

    append_article(article)
    dedup.mark_published("", headline)
    dedup.save()

    build_site()

    log.info("✅ Successfully published: %s", article["title"])
    log.info("   Slug: %s", article["slug"])
    return True


def main() -> None:
    setup_logging()

    if len(sys.argv) < 2:
        print("Usage: python agent/manual_publish.py \"Your article headline\"")
        print('Example: python agent/manual_publish.py "New luxury hotel opens in Marrakech"')
        sys.exit(1)

    # Support: python manual_publish.py "headline here"
    #      or: python manual_publish.py Headline words without quotes
    headline = " ".join(sys.argv[1:])

    success = publish_from_headline(headline)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
