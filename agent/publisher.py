"""
Marrakech Daily — Publisher
Manages the published articles registry and injects content into index.html.
"""

import json
import logging
import os
import re
import hashlib
from datetime import datetime
from typing import Optional

from config import PUBLISHED_LOG, INDEX_HTML, ARTICLES_DIR

logger = logging.getLogger(__name__)


# ── REGISTRY ─────────────────────────────────────────────────────────────────

def load_registry() -> dict:
    """Load the published articles registry from disk."""
    if not os.path.exists(PUBLISHED_LOG):
        return {"articles": [], "slugs": [], "url_hashes": []}
    try:
        with open(PUBLISHED_LOG, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        logger.error(f"Registry load error: {e}")
        return {"articles": [], "slugs": [], "url_hashes": []}


def save_registry(registry: dict) -> None:
    """Save the registry back to disk."""
    os.makedirs(ARTICLES_DIR, exist_ok=True)
    with open(PUBLISHED_LOG, "w", encoding="utf-8") as f:
        json.dump(registry, f, indent=2, ensure_ascii=False)


def is_duplicate(article: dict, registry: dict) -> bool:
    """Check if an article has already been published (by slug or source URL)."""
    slug = article.get("slug", "")
    url_hash = hashlib.md5(article.get("source_url", "").encode()).hexdigest()

    if slug in registry.get("slugs", []):
        logger.info(f"  Duplicate slug: {slug}")
        return True
    if url_hash in registry.get("url_hashes", []):
        logger.info(f"  Duplicate source URL: {article.get('source_url','')}")
        return True
    return False


def register_article(article: dict, registry: dict) -> dict:
    """Add an article to the registry."""
    slug     = article.get("slug", "")
    url_hash = hashlib.md5(article.get("source_url", "").encode()).hexdigest()

    registry.setdefault("articles", []).append({
        "slug":        slug,
        "title":       article.get("title", ""),
        "category":    article.get("category", ""),
        "published_at": article.get("published_at", ""),
        "source_url":  article.get("source_url", ""),
    })
    registry.setdefault("slugs", []).append(slug)
    registry.setdefault("url_hashes", []).append(url_hash)

    # Keep registry manageable (last 500 articles)
    for key in ("articles", "slugs", "url_hashes"):
        if len(registry[key]) > 500:
            registry[key] = registry[key][-500:]

    return registry


# ── UNSPLASH IMAGE ────────────────────────────────────────────────────────────

def _build_image_url(query: str, slug: str) -> str:
    """
    Build a deterministic Unsplash URL.
    Uses a seed derived from the slug so the same article always gets the same image.
    """
    seed = int(hashlib.md5(slug.encode()).hexdigest(), 16) % 1000
    q = query.replace(" ", "%20") if query else "marrakech%20morocco"
    return f"https://source.unsplash.com/1200x600/?{q}&sig={seed}"


# ── HTML GENERATION ───────────────────────────────────────────────────────────

def _format_date_display(date_str: str) -> str:
    """Turn 'June 26, 2026' → 'June 26, 2026'  (keep as-is, already formatted)."""
    return date_str


def _tags_html(tags: list) -> str:
    return "".join(f'<span class="mtag">{t}</span>' for t in tags)


def _article_to_js_entry(article: dict) -> str:
    """Render one article dict as a JavaScript object entry for the A={} registry."""
    slug        = json.dumps(article.get("slug", ""))
    cat         = json.dumps(article.get("category", "").replace("-", " ").title())
    title       = json.dumps(article.get("title", ""))
    img         = json.dumps(_build_image_url(article.get("image_query", "marrakech"), article.get("slug", "")))
    by_line     = json.dumps(f"Marrakech Daily Editorial Team")
    date        = json.dumps(article.get("published_at", ""))
    read        = json.dumps(f"{article.get('reading_time', 3)} min")
    tags_list   = json.dumps(article.get("tags", []))
    src_url     = json.dumps(article.get("source_url", ""))
    src_name    = json.dumps(article.get("source_name", ""))
    body        = json.dumps(article.get("body_html", "<p>Content unavailable.</p>"))
    is_brk      = "true" if article.get("is_breaking") else "false"

    return (
        f"  {slug}: {{"
        f"cat:{cat},"
        f"title:{title},"
        f"img:{img},"
        f"by:{by_line},"
        f"date:{date},"
        f"read:{read},"
        f"tags:{tags_list},"
        f"src:`Source: <a href=${{encodeURI({src_url})}} target='_blank'>{{}}</a>`.replace('{{}}',{src_name}),"
        f"body:{body},"
        f"is_breaking:{is_brk}"
        f"}}"
    )


def _article_to_card_html(article: dict, position: int = 0) -> str:
    """Generate a homepage card HTML snippet for an article."""
    slug     = article.get("slug", "")
    title    = article.get("title", "")
    excerpt  = article.get("excerpt", "")
    cat      = article.get("category", "").replace("-", " ").title()
    date     = article.get("published_at", "")
    read     = article.get("reading_time", 3)
    img_url  = _build_image_url(article.get("image_query", "marrakech"), slug)
    is_brk   = article.get("is_breaking", False)

    cat_label = f'{"⚡ " if is_brk else ""}{cat}'

    return f"""
      <article class="lcard" onclick="openA('{slug}')">
        <div class="limg"><img src="{img_url}" alt="{title[:60]}" loading="lazy"></div>
        <div class="lbody">
          <div class="lcat">{cat_label}</div>
          <h3 class="ltitle">{title}</h3>
          <p class="lexc">{excerpt}</p>
          <div class="tsm">{date} · {read} min read</div>
        </div>
      </article>"""


# ── MAIN INJECT ──────────────────────────────────────────────────────────────

# Markers that bracket the dynamic sections in index.html
MARKER_JS_START   = "/* AGENT_ARTICLES_START */"
MARKER_JS_END     = "/* AGENT_ARTICLES_END */"
MARKER_CARD_START = "<!-- AGENT_CARDS_START -->"
MARKER_CARD_END   = "<!-- AGENT_CARDS_END -->"
MARKER_TICKER_START = "<!-- AGENT_TICKER_START -->"
MARKER_TICKER_END   = "<!-- AGENT_TICKER_END -->"
MARKER_DATE       = "<!-- AGENT_DATE -->"
MARKER_HERO_TITLE = "<!-- AGENT_HERO_TITLE -->"


def inject_into_html(articles: list[dict]) -> bool:
    """
    Inject published articles into index.html.
    Returns True on success.
    """
    if not articles:
        logger.warning("No articles to inject")
        return False

    if not os.path.exists(INDEX_HTML):
        logger.error(f"index.html not found at {INDEX_HTML}")
        return False

    with open(INDEX_HTML, "r", encoding="utf-8") as f:
        html = f.read()

    # ── 1. Update JS article registry ────────────────────────────────────────
    if MARKER_JS_START in html and MARKER_JS_END in html:
        js_entries = ",\n".join(_article_to_js_entry(a) for a in articles)
        new_js_block = f"{MARKER_JS_START}\n{js_entries}\n{MARKER_JS_END}"
        html = re.sub(
            re.escape(MARKER_JS_START) + r".*?" + re.escape(MARKER_JS_END),
            new_js_block,
            html,
            flags=re.DOTALL,
        )
        logger.info(f"Injected {len(articles)} articles into JS registry")
    else:
        logger.warning("JS markers not found — will append JS to existing A object")
        # Fallback: inject before closing </script>
        js_entries = ",\n".join(_article_to_js_entry(a) for a in articles)
        html = html.replace(
            "const A = {",
            f"const A = {{\n// AUTO-GENERATED — {datetime.now().strftime('%Y-%m-%d')}\n{js_entries},\n",
            1,
        )

    # ── 2. Update homepage article cards ─────────────────────────────────────
    if MARKER_CARD_START in html and MARKER_CARD_END in html:
        cards_html = "".join(_article_to_card_html(a, i) for i, a in enumerate(articles[:8]))
        new_card_block = f"{MARKER_CARD_START}{cards_html}\n      {MARKER_CARD_END}"
        html = re.sub(
            re.escape(MARKER_CARD_START) + r".*?" + re.escape(MARKER_CARD_END),
            new_card_block,
            html,
            flags=re.DOTALL,
        )
        logger.info("Updated homepage article cards")

    # ── 3. Update breaking news ticker ───────────────────────────────────────
    if MARKER_TICKER_START in html and MARKER_TICKER_END in html:
        breaking = [a for a in articles if a.get("is_breaking")][:5]
        top      = articles[:8]
        combined = {a["slug"]: a for a in breaking + top}  # dedup

        ticker_items = " ◆ ".join(a["title"] for a in list(combined.values())[:8])
        ticker_html  = f'<span>{ticker_items}</span><span>{ticker_items}</span>'

        html = re.sub(
            re.escape(MARKER_TICKER_START) + r".*?" + re.escape(MARKER_TICKER_END),
            f"{MARKER_TICKER_START}{ticker_html}{MARKER_TICKER_END}",
            html,
            flags=re.DOTALL,
        )

    # ── 4. Update date display ────────────────────────────────────────────────
    today_display = datetime.now().strftime("%A, %B %d, %Y")
    if MARKER_DATE in html:
        html = html.replace(MARKER_DATE, today_display)
    else:
        # Fallback: replace hardcoded date patterns
        html = re.sub(
            r"(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday),\s+\w+\s+\d+,\s+\d{4}",
            today_display,
            html,
        )

    # ── 5. Update hero title with latest article ──────────────────────────────
    if articles and MARKER_HERO_TITLE in html:
        hero = articles[0]
        hero_html = (
            f'<h1 class="htitle" onclick="openA(\'{hero["slug"]}\')">'
            f'{hero["title"]}'
            f'</h1>'
        )
        html = html.replace(MARKER_HERO_TITLE, hero_html)

    # ── 6. Update "Updated" line in footer ───────────────────────────────────
    html = re.sub(
        r"Updated \w+ \w+ \d+, \d{4}",
        f"Updated {today_display}",
        html,
    )

    with open(INDEX_HTML, "w", encoding="utf-8") as f:
        f.write(html)

    logger.info(f"✅ index.html updated with {len(articles)} articles")
    return True


def save_article_json(article: dict) -> None:
    """Save individual article JSON for archival."""
    os.makedirs(ARTICLES_DIR, exist_ok=True)
    path = os.path.join(ARTICLES_DIR, f"{article['slug']}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(article, f, indent=2, ensure_ascii=False)
