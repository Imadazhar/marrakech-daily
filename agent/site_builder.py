"""
Site builder: regenerates index.html from the Jinja2 template and article data.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone, timedelta
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from config import (
    ROOT_DIR,
    TEMPLATES_DIR,
    SITE_TITLE,
    SITE_TAGLINE,
    SITE_DESCRIPTION,
    SITE_URL,
    SITE_TWITTER,
)
from publisher import load_articles

log = logging.getLogger(__name__)

MOROCCO_TZ = timezone(timedelta(hours=1))
OUTPUT_FILE = ROOT_DIR / "index.html"


def build_site() -> None:
    """Load articles and render the full index.html."""
    articles = load_articles()
    if not articles:
        log.warning("No articles found — site will render with empty state")

    env = Environment(
        loader=FileSystemLoader(str(TEMPLATES_DIR)),
        autoescape=select_autoescape(["html", "j2"]),
        trim_blocks=True,
        lstrip_blocks=True,
    )
    template = env.get_template("site.html.j2")

    # Derive breaking ticker items from breaking articles + recent headlines
    breaking = [a for a in articles if a.get("is_breaking")][:8]
    if len(breaking) < 4:
        breaking = articles[:8]

    ticker_texts = [a["title"] for a in breaking]

    # Hero = first article (or first breaking)
    hero = next((a for a in articles if a.get("is_breaking")), None) or (articles[0] if articles else None)

    # Latest news grid (exclude hero, max 8)
    latest = [a for a in articles if a.get("slug") != (hero.get("slug") if hero else None)][:8]

    # Category sections
    def by_category(cat: str, limit: int = 4) -> list[dict]:
        return [a for a in articles if a.get("category") == cat][:limit]

    now = datetime.now(tz=MOROCCO_TZ)

    html = template.render(
        site_title=SITE_TITLE,
        site_tagline=SITE_TAGLINE,
        site_description=SITE_DESCRIPTION,
        site_url=SITE_URL,
        site_twitter=SITE_TWITTER,
        build_time=now.strftime("%B %-d, %Y at %H:%M Morocco time"),
        build_iso=now.isoformat(),
        ticker_texts=ticker_texts,
        hero=hero,
        latest=latest,
        articles=articles,
        business=by_category("Business"),
        sport=by_category("Sport"),
        culture=by_category("Culture"),
        tourism=by_category("Tourism"),
        national=by_category("National"),
        total_articles=len(articles),
    )

    OUTPUT_FILE.write_text(html, encoding="utf-8")
    log.info("Site built → %s (%d articles)", OUTPUT_FILE, len(articles))


if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO)
    build_site()
    print(f"Built index.html with {len(load_articles())} articles.")
