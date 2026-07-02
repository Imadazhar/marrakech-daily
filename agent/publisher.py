"""
Article publisher: persists articles to _data/articles.json.

The JSON file is the single source of truth for all published articles.
It stores articles in reverse-chronological order (newest first).
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Optional

from config import ARTICLES_FILE

log = logging.getLogger(__name__)

# Max articles to keep in the JSON file (keeps it manageable for a static site)
MAX_ARTICLES_STORED = 500


# ── Load / Save ────────────────────────────────────────────────────────────────

def load_articles() -> list[dict]:
    """Load the current articles list from disk."""
    if ARTICLES_FILE.exists():
        try:
            data = json.loads(ARTICLES_FILE.read_text(encoding="utf-8"))
            if isinstance(data, list):
                return data
            if isinstance(data, dict):
                return data.get("articles", [])
        except Exception as exc:
            log.error("Could not load articles file: %s", exc)
    return []


def save_articles(articles: list[dict]) -> None:
    """Persist the articles list to disk (newest first, capped at MAX_ARTICLES_STORED)."""
    # Sort newest first
    articles = sorted(
        articles,
        key=lambda a: a.get("published_at", ""),
        reverse=True,
    )
    # Trim
    articles = articles[:MAX_ARTICLES_STORED]

    ARTICLES_FILE.parent.mkdir(parents=True, exist_ok=True)
    ARTICLES_FILE.write_text(
        json.dumps(articles, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    log.info("Saved %d articles to %s", len(articles), ARTICLES_FILE)


def append_article(article: dict) -> None:
    """Append a single article to the store (in-place save)."""
    articles = load_articles()

    # Guard against accidental duplicates (shouldn't happen, but be safe)
    existing_slugs = {a.get("slug") for a in articles}
    if article.get("slug") in existing_slugs:
        log.warning("Slug '%s' already exists — skipping append", article.get("slug"))
        return

    articles.insert(0, article)   # prepend (newest first)
    save_articles(articles)
    log.info("Published: [%s] %s", article.get("category"), article.get("title"))


def get_published_slugs() -> set[str]:
    """Return the set of all slugs currently in the article store."""
    return {a.get("slug", "") for a in load_articles()}
