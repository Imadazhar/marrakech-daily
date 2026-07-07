"""
Site builder: regenerates index.html from the Jinja2 template and article data.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone, timedelta
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from config import (
    ROOT_DIR, TEMPLATES_DIR,
    SITE_TITLE, SITE_TAGLINE, SITE_DESCRIPTION, SITE_URL, SITE_TWITTER,
    CATEGORIES,
)
from publisher import load_articles

log = logging.getLogger(__name__)

MOROCCO_TZ  = timezone(timedelta(hours=1))
OUTPUT_FILE = ROOT_DIR / "index.html"


def _by_cat(articles: list[dict], cat: str, limit: int = 6) -> list[dict]:
    return [a for a in articles if a.get("category", "") == cat][:limit]


def _most_read(articles: list[dict], limit: int = 5) -> list[dict]:
    """Return top articles by simulated view count (breaking + recent first)."""
    scored = []
    for i, a in enumerate(articles[:40]):
        score = 0
        if a.get("is_breaking"):
            score += 5000
        score += max(0, 10000 - i * 200)
        scored.append((score, a))
    scored.sort(reverse=True, key=lambda x: x[0])
    return [a for _, a in scored[:limit]]


def build_site() -> None:
    articles = load_articles()
    if not articles:
        log.warning("No articles found — rendering empty state")

    now = datetime.now(tz=MOROCCO_TZ)

    # ── Ticker: breaking first, then latest ──────────────────────────────────
    breaking_arts = [a for a in articles if a.get("is_breaking")][:6]
    ticker_arts   = breaking_arts if breaking_arts else articles[:6]
    ticker_items  = [a["title"] for a in ticker_arts]

    # ── Hero ─────────────────────────────────────────────────────────────────
    hero = next((a for a in articles if a.get("is_breaking")), None) or (articles[0] if articles else None)
    hero_slug = hero.get("slug") if hero else None

    # ── Latest (exclude hero, show 8) ────────────────────────────────────────
    latest_articles = [a for a in articles if a.get("slug") != hero_slug][:8]

    # ── Sidebar top 4 (excluding hero) ───────────────────────────────────────
    sidebar_articles = [a for a in articles if a.get("slug") != hero_slug][:4]

    # ── Category sections ─────────────────────────────────────────────────────
    business_articles  = _by_cat(articles, "Business", 5)
    sport_articles     = _by_cat(articles, "Sport", 4)
    culture_articles   = _by_cat(articles, "Culture", 4)
    tourism_articles   = _by_cat(articles, "Tourism", 3)
    national_articles  = _by_cat(articles, "National", 4)
    society_articles   = _by_cat(articles, "Society", 4)
    tech_articles      = _by_cat(articles, "Tech", 4)
    health_articles    = _by_cat(articles, "Health", 4)
    world_articles     = _by_cat(articles, "World", 4)
    breaking_articles  = _by_cat(articles, "Breaking", 4)

    # ── Events (Tourism + Culture articles flagged as events) ─────────────────
    events_articles = [
        a for a in articles
        if any(kw in (a.get("title","") + a.get("excerpt","")).lower()
               for kw in ["festival","event","concert","exhibition","match","tournoi",
                          "conference","summit","launch","opening","inauguration"])
    ][:6]
    if not events_articles:
        events_articles = (tourism_articles + culture_articles)[:6]

    # Add event day/month for calendar display
    for i, a in enumerate(events_articles):
        if not a.get("event_day"):
            a["event_day"]   = str(now.day + i % 14).zfill(2)
            a["event_month"] = now.strftime("%b").upper()

    # ── Most read ─────────────────────────────────────────────────────────────
    most_read = _most_read(articles)
    for i, a in enumerate(most_read):
        if not a.get("view_count"):
            a["view_count"] = f"{max(800, 12000 - i * 1800 + hash(a.get('slug','')) % 500):,}"

    # ── articles_json for JS modal ────────────────────────────────────────────
    articles_dict = {a["slug"]: a for a in articles if a.get("slug")}
    articles_json = json.dumps(articles_dict, ensure_ascii=False)

    # ── Render ────────────────────────────────────────────────────────────────
    env = Environment(
        loader=FileSystemLoader(str(TEMPLATES_DIR)),
        autoescape=select_autoescape(["html", "j2"]),
        trim_blocks=True,
        lstrip_blocks=True,
    )
    template = env.get_template("site.html.j2")

    html = template.render(
        # Site meta
        site_title=SITE_TITLE,
        site_tagline=SITE_TAGLINE,
        site_description=SITE_DESCRIPTION,
        site_url=SITE_URL,
        site_twitter=SITE_TWITTER,
        categories=CATEGORIES,
        current_year=now.year,
        # Date/weather
        today_display=now.strftime("%A, %B %-d, %Y"),
        today_iso=now.strftime("%Y-%m-%d"),
        build_time=now.strftime("%B %-d, %Y at %H:%M Morocco time"),
        weather_temp="38°C / 100°F",
        weather_icon="☀",
        weather_desc="Sunny, very hot",
        # Ticker
        ticker_items=ticker_items,
        # Articles
        hero=hero,
        sidebar_articles=sidebar_articles,
        latest_articles=latest_articles,
        business_articles=business_articles,
        sport_articles=sport_articles,
        culture_articles=culture_articles,
        tourism_articles=tourism_articles,
        national_articles=national_articles,
        society_articles=society_articles,
        tech_articles=tech_articles,
        health_articles=health_articles,
        world_articles=world_articles,
        breaking_articles=breaking_articles,
        events_articles=events_articles,
        most_read=most_read,
        total_articles=len(articles),
        # JS data
        articles_json=articles_json,
    )

    OUTPUT_FILE.write_text(html, encoding="utf-8")
    log.info("✅ Site built → %s (%d articles, %d bytes)",
             OUTPUT_FILE, len(articles), len(html))


if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    build_site()
