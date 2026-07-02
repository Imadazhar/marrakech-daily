#!/usr/bin/env python3
"""
Marrakech Daily — Daily News Agent
====================================
Usage:
  python daily_agent.py                    # full daily run (scrape + write + publish)
  python daily_agent.py --manual "topic"  # publish one article on a given topic
  python daily_agent.py --dry-run         # scrape & write but don't commit to HTML
  python daily_agent.py --limit 5         # override ARTICLES_PER_RUN
"""

import argparse
import logging
import os
import sys
import time
from datetime import datetime

# ── Path setup so we can import sibling modules ──────────────────────────────
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import (
    ARTICLES_PER_RUN, MAX_ATTEMPTS, SOURCES, LOG_DIR,
    ANTHROPIC_KEY,
)
from scraper   import scrape_all
from writer    import write_from_source, write_manual
from publisher import (
    load_registry, save_registry, is_duplicate,
    register_article, inject_into_html, save_article_json,
)

# ── Logging ──────────────────────────────────────────────────────────────────
os.makedirs(LOG_DIR, exist_ok=True)
log_file = os.path.join(LOG_DIR, f"agent_{datetime.now().strftime('%Y%m%d')}.log")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    handlers=[
        logging.FileHandler(log_file, encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger("daily_agent")


# ── Helpers ──────────────────────────────────────────────────────────────────

def check_env() -> None:
    if not ANTHROPIC_KEY:
        logger.error("ANTHROPIC_API_KEY environment variable is not set.")
        sys.exit(1)


def run_daily(limit: int, dry_run: bool) -> int:
    """Full daily pipeline. Returns number of articles published."""
    logger.info("=" * 60)
    logger.info(f"Marrakech Daily Agent — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    logger.info(f"Target: {limit} articles | dry_run={dry_run}")
    logger.info("=" * 60)

    registry = load_registry()
    logger.info(f"Registry: {len(registry.get('slugs', []))} slugs already published")

    # Distribute quota across sources by weight
    total_weight = sum(s["weight"] for s in SOURCES)
    per_source = {
        s["name"]: max(4, round(limit * s["weight"] / total_weight) + 3)
        for s in SOURCES
    }
    logger.info(f"Per-source limits: {per_source}")

    # Step 1 — Scrape
    logger.info("── STEP 1: Scraping sources ──")
    all_raw = scrape_all(per_source)
    logger.info(f"Total raw articles collected: {len(all_raw)}")

    if not all_raw:
        logger.error("No articles scraped — check source connectivity.")
        return 0

    # Step 2 — Write & publish loop
    logger.info("── STEP 2: AI writing pipeline ──")
    published = []
    skipped   = 0
    errors    = 0

    for raw in all_raw:
        if len(published) >= limit:
            break
        if (skipped + errors) > MAX_ATTEMPTS:
            logger.warning("Max attempts reached — stopping early")
            break

        logger.info(f"\n[{len(published)+1}/{limit}] Writing: {raw['raw_title'][:70]}")

        # Duplicate check on source URL before spending AI tokens
        temp_check = {"slug": "", "source_url": raw["url"]}
        if is_duplicate(temp_check, registry):
            skipped += 1
            continue

        try:
            article = write_from_source(raw)
        except Exception as exc:
            logger.error(f"  Write failed: {exc}")
            errors += 1
            time.sleep(2)
            continue

        # Duplicate check on slug after writing
        if is_duplicate(article, registry):
            skipped += 1
            continue

        logger.info(f"  ✓ Written: {article['title'][:70]}")
        published.append(article)
        save_article_json(article)
        registry = register_article(article, registry)

        time.sleep(1.5)   # rate-limit AI calls

    logger.info(f"\n── STEP 2 complete: {len(published)} written, {skipped} skipped, {errors} errors ──")

    if not published:
        logger.warning("No new articles — nothing to publish")
        return 0

    # Step 3 — Inject into HTML
    logger.info("── STEP 3: Injecting into index.html ──")
    if dry_run:
        logger.info("DRY RUN — skipping HTML injection")
    else:
        # Merge: new articles first, then last 40 from registry (for JS lookup)
        archived = _load_recent_articles(40)
        all_for_html = published + [a for a in archived if a["slug"] not in {p["slug"] for p in published}]
        success = inject_into_html(all_for_html[:60])   # keep HTML manageable
        if success:
            save_registry(registry)
            logger.info(f"✅ Published {len(published)} articles to index.html")
        else:
            logger.error("HTML injection failed")
            return 0

    return len(published)


def run_manual(topic: str, dry_run: bool) -> bool:
    """Write and publish a single article on a given topic."""
    logger.info("=" * 60)
    logger.info(f"Manual publish: '{topic}'")
    logger.info("=" * 60)

    registry = load_registry()

    try:
        article = write_manual(topic)
    except Exception as exc:
        logger.error(f"Manual write failed: {exc}")
        return False

    logger.info(f"✓ Written: {article['title']}")

    if is_duplicate(article, registry):
        logger.warning("This article appears to already be published (duplicate slug)")
        # Still publish with timestamp suffix
        article["slug"] = article["slug"] + f"-{datetime.now().strftime('%H%M')}"

    save_article_json(article)
    registry = register_article(article, registry)

    if dry_run:
        logger.info("DRY RUN — skipping HTML injection")
        return True

    archived = _load_recent_articles(40)
    all_for_html = [article] + [a for a in archived if a["slug"] != article["slug"]]
    success = inject_into_html(all_for_html[:60])

    if success:
        save_registry(registry)
        logger.info(f"✅ Manual article published: {article['title']}")
        return True
    else:
        logger.error("HTML injection failed")
        return False


def _load_recent_articles(n: int) -> list[dict]:
    """Load the N most recent article JSON files from disk."""
    from config import ARTICLES_DIR
    import json

    if not os.path.exists(ARTICLES_DIR):
        return []

    files = [
        f for f in os.listdir(ARTICLES_DIR)
        if f.endswith(".json") and f != "published.json"
    ]
    # Sort by modification time — newest first
    files.sort(
        key=lambda f: os.path.getmtime(os.path.join(ARTICLES_DIR, f)),
        reverse=True,
    )

    articles = []
    for fname in files[:n]:
        try:
            with open(os.path.join(ARTICLES_DIR, fname), "r", encoding="utf-8") as f:
                articles.append(json.load(f))
        except Exception:
            pass
    return articles


# ── CLI ───────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Marrakech Daily — AI Editorial Agent"
    )
    parser.add_argument(
        "--manual", "-m",
        metavar="TOPIC",
        help='Manually publish one article. E.g. --manual "New hotel opens in Marrakech"',
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run the pipeline but do NOT write to index.html",
    )
    parser.add_argument(
        "--limit", "-n",
        type=int,
        default=ARTICLES_PER_RUN,
        help=f"Number of articles to publish (default: {ARTICLES_PER_RUN})",
    )
    args = parser.parse_args()

    check_env()

    start = time.time()

    if args.manual:
        success = run_manual(args.manual, dry_run=args.dry_run)
        elapsed = time.time() - start
        logger.info(f"Manual run complete in {elapsed:.1f}s — {'SUCCESS' if success else 'FAILED'}")
        sys.exit(0 if success else 1)
    else:
        count = run_daily(limit=args.limit, dry_run=args.dry_run)
        elapsed = time.time() - start
        logger.info(f"Daily run complete in {elapsed:.1f}s — {count} articles published")
        sys.exit(0 if count > 0 else 1)


if __name__ == "__main__":
    main()
