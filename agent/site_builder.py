"""
Site builder: regenerates index.html from the Jinja2 template and article data.
Normalises article field names between the AI pipeline output and the template.
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


def _normalise(article: dict) -> dict:
    """
    Normalise article fields so the template always gets consistent keys.
    The AI pipeline stores: hero_image, author={name,role}, body (HTML)
    The template expects:   image_url, author_name, author_role, body_html
    """
    a = dict(article)

    # image_url  ← hero_image OR thumb_image OR fallback
    if not a.get("image_url"):
        a["image_url"] = (
            a.get("hero_image") or
            a.get("thumb_image") or
            "https://images.unsplash.com/photo-1528360983277-13d401cdc186?w=1200&q=80"
        )
    # Ensure Unsplash URLs have size params
    if "unsplash.com" in a["image_url"] and "?" not in a["image_url"]:
        a["image_url"] += "?w=1200&q=80"

    # author_name / author_role  ← author dict or string
    auth = a.get("author", {})
    if isinstance(auth, dict):
        a["author_name"] = auth.get("name", "Marrakech Daily Staff")
        a["author_role"] = auth.get("role", "Editorial Team")
    else:
        a["author_name"] = str(auth) or "Marrakech Daily Staff"
        a["author_role"] = "Editorial Team"

    # body_html  ← body
    if not a.get("body_html"):
        a["body_html"] = a.get("body", "<p>Content unavailable.</p>")

    # source attribution  ← sources list or _source_url
    sources = a.get("sources", [])
    if sources and isinstance(sources, list):
        a["source_url"]  = sources[0].get("url", "")
        a["source_name"] = sources[0].get("name", "")
    else:
        a["source_url"]  = a.get("_source_url", "")
        a["source_name"] = ""

    # date_display fallback
    if not a.get("date_display"):
        try:
            dt = datetime.fromisoformat(a.get("published_at", ""))
            a["date_display"] = dt.strftime("%B %-d, %Y")
        except Exception:
            a["date_display"] = "Recently"

    # reading_time fallback
    if not a.get("reading_time"):
        words = len(a.get("body_html", "").split())
        a["reading_time"] = max(1, round(words / 220))

    # tags: always a list of strings
    tags = a.get("tags", [])
    if isinstance(tags, list):
        a["tags"] = [str(t) for t in tags[:8]]
    else:
        a["tags"] = []

    # is_breaking: always bool
    a["is_breaking"] = bool(a.get("is_breaking", False))

    return a


def _by_cat(articles: list[dict], cat: str, limit: int = 6) -> list[dict]:
    return [a for a in articles if a.get("category", "") == cat][:limit]


def _most_read(articles: list[dict], limit: int = 5) -> list[dict]:
    scored = []
    for i, a in enumerate(articles[:40]):
        score = (5000 if a.get("is_breaking") else 0) + max(0, 10000 - i * 200)
        scored.append((score, a))
    scored.sort(reverse=True, key=lambda x: x[0])
    return [a for _, a in scored[:limit]]


def build_site() -> None:
    raw_articles = load_articles()
    if not raw_articles:
        log.warning("No articles found — rendering empty state")

    # Normalise all articles
    articles = [_normalise(a) for a in raw_articles]

    now = datetime.now(tz=MOROCCO_TZ)

    # Ticker
    breaking_arts = [a for a in articles if a.get("is_breaking")][:6]
    ticker_arts   = breaking_arts if breaking_arts else articles[:6]
    ticker_items  = [a["title"] for a in ticker_arts]
    if not ticker_items:
        ticker_items = ["Welcome to Marrakech Daily — your English-language news source for Morocco"]

    # Hero
    hero      = next((a for a in articles if a.get("is_breaking")), None) or (articles[0] if articles else None)
    hero_slug = hero.get("slug") if hero else None

    # Page sections
    excl          = lambda arts, s: [a for a in arts if a.get("slug") != s]
    latest        = excl(articles, hero_slug)[:8]
    sidebar       = excl(articles, hero_slug)[:4]
    business      = _by_cat(articles, "Business", 5)
    sport         = _by_cat(articles, "Sport", 4)
    culture       = _by_cat(articles, "Culture", 4)
    tourism       = _by_cat(articles, "Tourism", 3)
    national      = _by_cat(articles, "National", 4)
    society       = _by_cat(articles, "Society", 4)
    tech          = _by_cat(articles, "Tech", 4) or _by_cat(articles, "Technology", 4)
    health        = _by_cat(articles, "Health", 4)
    world         = _by_cat(articles, "World", 4) or _by_cat(articles, "International", 4)
    breaking      = _by_cat(articles, "Breaking", 4)

    # Events calendar — pull from articles mentioning event keywords
    event_kws = ["festival","event","concert","exhibition","match","tournament",
                 "conference","summit","launch","opening","inauguration","screening"]
    events = [a for a in articles
              if any(kw in (a.get("title","") + a.get("excerpt","")).lower() for kw in event_kws)][:6]
    if not events:
        events = (tourism + culture)[:6]

    for i, a in enumerate(events):
        if not a.get("event_day"):
            a["event_day"]   = str(min(now.day + i * 2, 31)).zfill(2)
            a["event_month"] = now.strftime("%b").upper()

    # Most read
    most_read = _most_read(articles)
    for i, a in enumerate(most_read):
        if not a.get("view_count"):
            base = max(800, 12000 - i * 1800)
            vary = abs(hash(a.get("slug", ""))) % 500
            a["view_count"] = f"{base + vary:,}"

    # JS article dict
    articles_json = json.dumps(
        {a["slug"]: a for a in articles if a.get("slug")},
        ensure_ascii=False
    )

    # Render Jinja2 template
    env = Environment(
        loader=FileSystemLoader(str(TEMPLATES_DIR)),
        autoescape=select_autoescape(["html", "j2"]),
        trim_blocks=True,
        lstrip_blocks=True,
    )
    template = env.get_template("site.html.j2")

    html = template.render(
        site_title=SITE_TITLE,
        site_tagline=SITE_TAGLINE,
        site_description=SITE_DESCRIPTION,
        site_url=SITE_URL,
        site_twitter=SITE_TWITTER,
        categories=CATEGORIES,
        current_year=now.year,
        today_display=now.strftime("%A, %B %-d, %Y"),
        today_iso=now.strftime("%Y-%m-%d"),
        build_time=now.strftime("%B %-d, %Y at %H:%M Morocco time"),
        weather_temp="38°C / 100°F",
        weather_icon="☀",
        weather_desc="Sunny",
        ticker_items=ticker_items,
        hero=hero,
        sidebar_articles=sidebar,
        latest_articles=latest,
        business_articles=business,
        sport_articles=sport,
        culture_articles=culture,
        tourism_articles=tourism,
        national_articles=national,
        society_articles=society,
        tech_articles=tech,
        health_articles=health,
        world_articles=world,
        breaking_articles=breaking,
        events_articles=events,
        most_read=most_read,
        total_articles=len(articles),
        articles_json=articles_json,
    )

    OUTPUT_FILE.write_text(html, encoding="utf-8")
    log.info("✅ Site built → %s (%d articles, %d bytes)",
             OUTPUT_FILE, len(articles), len(html))


if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO, stream=sys.stdout,
                        format="%(asctime)s %(levelname)-8s — %(message)s")
    build_site()
