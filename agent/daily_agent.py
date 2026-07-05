#!/usr/bin/env python3
"""
Marrakech Daily — Autonomous AI Editorial Agent
================================================
Modes:
  python daily_agent.py                        # daily run: scrape → write → publish
  python daily_agent.py --manual "topic"       # publish one article on topic
  python daily_agent.py --limit 10             # override article count
  python daily_agent.py --dry-run              # run pipeline, skip HTML write
  python daily_agent.py --sources kech24       # run only specific source(s)

Environment variables required:
  GROQ_API_KEY   — your Groq API key
"""
import argparse
import hashlib
import logging
import os
import sys
import time
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import (
    ARTICLES_PER_RUN, LOGS_DIR, GROQ_API_KEY, ROOT_DIR,
)
from scraper   import scrape_all
from writer    import write_from_source, write_manual
from publisher import (
    load_registry, save_registry, is_duplicate, register,
    inject_html, save_article_json, load_recent_articles,
    generate_sitemap, generate_rss,
)

# ── LOGGING ───────────────────────────────────────────────────────────────────
os.makedirs(LOGS_DIR, exist_ok=True)
log_path = os.path.join(LOGS_DIR, f"agent_{datetime.now().strftime('%Y%m%d_%H%M')}.log")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)-8s] %(name)s — %(message)s",
    datefmt="%H:%M:%S",
    handlers=[
        logging.FileHandler(log_path, encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger("main")


# ── HELPERS ───────────────────────────────────────────────────────────────────

def _url_hash(url: str) -> str:
    return hashlib.md5(url.encode()).hexdigest()


def _banner(msg: str) -> None:
    logger.info("─" * 60)
    logger.info(msg)
    logger.info("─" * 60)


# ── DAILY RUN ─────────────────────────────────────────────────────────────────

def run_daily(limit: int, dry_run: bool, source_filter: list[str] | None) -> int:
    _banner(f"MARRAKECH DAILY AGENT — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    logger.info(f"Target: {limit} articles | dry_run={dry_run}")

    # Load registry
    registry    = load_registry()
    seen_hashes = registry.get("url_hashes", set())
    seen_slugs  = registry.get("slugs", set())
    logger.info(f"Registry: {len(seen_slugs)} slugs, {len(seen_hashes)} URL hashes")

    # Optional source filter
    if source_filter:
        from config import SOURCES
        active_sources = [s for s in SOURCES if s["id"] in source_filter]
        logger.info(f"Source filter: {[s['id'] for s in active_sources]}")
        # Temporarily patch config
        import config
        _orig = config.SOURCES
        config.SOURCES = active_sources

    # ── SCRAPE ───────────────────────────────────────────────────────────────
    _banner("PHASE 1 — SCRAPING")
    all_raw = scrape_all(seen_hashes)

    if source_filter:
        import config
        config.SOURCES = _orig  # restore

    if not all_raw:
        logger.error("No articles scraped — check network / sources")
        return 0

    # ── WRITE & PUBLISH ──────────────────────────────────────────────────────
    _banner("PHASE 2 — AI WRITING")
    published = []
    skipped = errors = 0

    for i, raw in enumerate(all_raw):
        if len(published) >= limit:
            break

        url_hash = raw.get("url_hash", _url_hash(raw["url"]))
        logger.info(f"\n[{len(published)+1}/{limit}] {raw['raw_title'][:70]}")

        try:
            article = write_from_source(raw)
        except Exception as exc:
            logger.error(f"  ✗ Write failed: {exc}")
            errors += 1
            time.sleep(2)
            continue

        slug = article.get("slug", "")
        if is_duplicate(slug, url_hash, registry):
            logger.info(f"  → Duplicate, skipping")
            skipped += 1
            continue

        # Add url_hash to article for registry
        article["url_hash"] = url_hash

        logger.info(f"  ✓ [{article['category']}] {article['title'][:70]}")
        published.append(article)
        save_article_json(article)
        register(article, registry)

        time.sleep(1.2)  # rate-limit AI calls

    logger.info(f"\nPhase 2 done: {len(published)} published, {skipped} skipped, {errors} errors")

    if not published:
        logger.warning("Nothing new to publish")
        return 0

    if dry_run:
        logger.info("DRY RUN — skipping HTML/sitemap/RSS writes")
        return len(published)

    # ── INJECT INTO SITE ─────────────────────────────────────────────────────
    _banner("PHASE 3 — PUBLISHING TO SITE")
    recent = load_recent_articles(80)
    # Merge: new articles first, then historical (no duplicates)
    new_slugs = {a["slug"] for a in published}
    combined  = published + [a for a in recent if a.get("slug") not in new_slugs]

    success = inject_html(combined[:80])  # keep JS manageable
    if not success:
        logger.error("HTML injection failed")
        return 0

    generate_sitemap(combined[:200])
    generate_rss(combined[:30])
    save_registry(registry)

    logger.info(f"✅ {len(published)} articles published | Log: {log_path}")
    return len(published)


# ── MANUAL MODE ───────────────────────────────────────────────────────────────

def run_manual(topic: str, dry_run: bool) -> bool:
    _banner(f"MANUAL PUBLISH: {topic}")
    registry = load_registry()

    try:
        article = write_manual(topic)
    except Exception as exc:
        logger.error(f"Write failed: {exc}")
        return False

    logger.info(f"✓ Written: {article['title']}")

    # Avoid exact slug collision
    slug     = article.get("slug", "")
    url_hash = _url_hash(article.get("source_url", topic))
    if is_duplicate(slug, url_hash, registry):
        article["slug"] = slug + f"-{datetime.now().strftime('%H%M%S')}"
        logger.info(f"Slug adjusted to avoid collision: {article['slug']}")

    article["url_hash"] = url_hash
    save_article_json(article)
    register(article, registry)

    if dry_run:
        logger.info("DRY RUN — skipping HTML write")
        return True

    recent   = load_recent_articles(80)
    combined = [article] + [a for a in recent if a.get("slug") != article["slug"]]

    success = inject_html(combined[:80])
    if success:
        generate_sitemap(combined[:200])
        generate_rss(combined[:30])
        save_registry(registry)
        logger.info(f"✅ Manual article published: {article['title']}")
        return True

    logger.error("HTML injection failed")
    return False


# ── CLI ───────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="Marrakech Daily AI Agent")
    parser.add_argument("--manual", "-m", metavar="TOPIC",
                        help='Manually publish: --manual "New hotel in Marrakech"')
    parser.add_argument("--dry-run", action="store_true",
                        help="Run pipeline without writing files")
    parser.add_argument("--limit", "-n", type=int, default=ARTICLES_PER_RUN,
                        help=f"Articles to publish (default: {ARTICLES_PER_RUN})")
    parser.add_argument("--sources", nargs="+", metavar="ID",
                        help="Only use specific sources by ID, e.g. --sources kech24 alphabourse")
    args = parser.parse_args()

    if not GROQ_API_KEY:
        logger.error("GROQ_API_KEY environment variable is not set. Exiting.")
        sys.exit(1)

    t0 = time.time()

    if args.manual:
        ok = run_manual(args.manual, dry_run=args.dry_run)
        logger.info(f"Manual run: {'SUCCESS' if ok else 'FAILED'} in {time.time()-t0:.1f}s")
        sys.exit(0 if ok else 1)
    else:
        n = run_daily(limit=args.limit, dry_run=args.dry_run, source_filter=args.sources)
        logger.info(f"Daily run: {n} articles in {time.time()-t0:.1f}s")
        sys.exit(0 if n > 0 else 1)


if __name__ == "__main__":
    main()
