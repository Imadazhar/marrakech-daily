"""
Marrakech Daily — Publisher
Registry management + HTML injection + sitemap + RSS generation.
"""
import hashlib
import json
import logging
import os
import re
from datetime import datetime
from email.utils import formatdate
from typing import Optional

from config import (
    PUBLISHED_DB, INDEX_HTML, ARTICLES_DIR,
    SITEMAP_XML, RSS_XML, SITE_URL, SITE_NAME, SITE_TAGLINE,
    UNSPLASH_BASE,
)

logger = logging.getLogger("publisher")

# ── REGISTRY ──────────────────────────────────────────────────────────────────

def load_registry() -> dict:
    if not os.path.exists(PUBLISHED_DB):
        return {"articles": [], "slugs": set(), "url_hashes": set()}
    try:
        with open(PUBLISHED_DB, "r", encoding="utf-8") as f:
            d = json.load(f)
        # Convert lists → sets for O(1) lookup
        d["slugs"]      = set(d.get("slugs", []))
        d["url_hashes"] = set(d.get("url_hashes", []))
        return d
    except Exception as e:
        logger.error(f"Registry load error: {e}")
        return {"articles": [], "slugs": set(), "url_hashes": set()}


def save_registry(registry: dict) -> None:
    os.makedirs(ARTICLES_DIR, exist_ok=True)
    # Convert sets back to sorted lists for JSON
    out = {
        "articles":   registry.get("articles", [])[-500:],
        "slugs":      sorted(registry.get("slugs", set())),
        "url_hashes": sorted(registry.get("url_hashes", set())),
    }
    with open(PUBLISHED_DB, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2, ensure_ascii=False)


def is_duplicate(slug: str, url_hash: str, registry: dict) -> bool:
    if slug in registry.get("slugs", set()):
        return True
    if url_hash in registry.get("url_hashes", set()):
        return True
    return False


def register(article: dict, registry: dict) -> None:
    slug     = article.get("slug", "")
    url_hash = hashlib.md5(article.get("source_url", "").encode()).hexdigest()
    registry.setdefault("slugs", set()).add(slug)
    registry.setdefault("url_hashes", set()).add(url_hash)
    registry.setdefault("articles", []).append({
        "slug":         slug,
        "title":        article.get("title", ""),
        "category":     article.get("category", ""),
        "published_at": article.get("published_at", ""),
        "source_url":   article.get("source_url", ""),
        "source_name":  article.get("source_name", ""),
    })


def save_article_json(article: dict) -> None:
    os.makedirs(ARTICLES_DIR, exist_ok=True)
    path = os.path.join(ARTICLES_DIR, f"{article['slug']}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(article, f, indent=2, ensure_ascii=False)


def load_recent_articles(n: int = 80) -> list[dict]:
    """Load N most-recently-modified article JSON files."""
    if not os.path.exists(ARTICLES_DIR):
        return []
    files = [
        f for f in os.listdir(ARTICLES_DIR)
        if f.endswith(".json") and f != "published.json"
    ]
    files.sort(key=lambda f: os.path.getmtime(os.path.join(ARTICLES_DIR, f)), reverse=True)
    out = []
    for fname in files[:n]:
        try:
            with open(os.path.join(ARTICLES_DIR, fname), encoding="utf-8") as f:
                out.append(json.load(f))
        except Exception:
            pass
    return out


# ── IMAGES ───────────────────────────────────────────────────────────────────

def img_url(article: dict) -> str:
    q    = (article.get("image_query") or "marrakech morocco").replace(" ", ",")
    seed = int(hashlib.md5(article.get("slug", "x").encode()).hexdigest(), 16) % 9999
    return f"{UNSPLASH_BASE}/?{q}&sig={seed}"


# ── HTML INJECTION ────────────────────────────────────────────────────────────

JS_START   = "/* AGENT_ARTICLES_START */"
JS_END     = "/* AGENT_ARTICLES_END */"
CARD_START = "<!-- AGENT_CARDS_START -->"
CARD_END   = "<!-- AGENT_CARDS_END -->"


def _js_entry(a: dict) -> str:
    slug     = json.dumps(a.get("slug", ""))
    cat_raw  = a.get("category", "national").replace("-", " ").title()
    cat      = json.dumps(("⚡ " if a.get("is_breaking") else "") + cat_raw)
    title    = json.dumps(a.get("title", ""))
    img      = json.dumps(img_url(a))
    by       = json.dumps(a.get("author", "Marrakech Daily Staff"))
    date     = json.dumps(a.get("published_at", ""))
    read     = json.dumps(f"{a.get('reading_time', 3)} min")
    tags     = json.dumps(a.get("tags", []))
    src_url  = json.dumps(a.get("source_url", "#"))
    src_name = json.dumps(a.get("source_name", ""))
    body     = json.dumps(a.get("body_html", "<p>Content unavailable.</p>"))
    is_brk   = "true" if a.get("is_breaking") else "false"

    return (
        f"  {slug}:{{cat:{cat},title:{title},img:{img},by:{by},"
        f"date:{date},read:{read},tags:{tags},"
        f"src:`Source: <a href='${{encodeURI({src_url})}}' target='_blank' rel='noopener'>{{}}</a>`.replace('{{}}',{src_name}),"
        f"body:{body},is_breaking:{is_brk}}}"
    )


def _card_html(a: dict) -> str:
    slug    = a.get("slug", "")
    title   = a.get("title", "")
    excerpt = a.get("excerpt", "")
    cat     = a.get("category", "").replace("-", " ").title()
    date    = a.get("published_at", "")
    read    = a.get("reading_time", 3)
    img     = img_url(a)
    brk     = a.get("is_breaking", False)
    cat_label = f'{"⚡ " if brk else ""}{cat}'
    safe_title = title.replace('"', "&quot;")
    safe_excerpt = excerpt.replace("<", "&lt;").replace(">", "&gt;")
    return (
        f'\n      <article class="lcard" onclick="openA(\'{slug}\')">'
        f'<div class="limg"><img src="{img}" alt="{safe_title}" loading="lazy"></div>'
        f'<div class="lbody"><div class="lcat">{cat_label}</div>'
        f'<h3 class="ltitle">{title}</h3>'
        f'<p class="lexc">{safe_excerpt}</p>'
        f'<div class="tsm">{date} · {read} min read</div>'
        f'</div></article>'
    )


def inject_html(articles: list[dict]) -> bool:
    """Inject articles into index.html. Returns True on success."""
    if not articles:
        logger.warning("No articles to inject")
        return False
    if not os.path.exists(INDEX_HTML):
        logger.error(f"index.html not found: {INDEX_HTML}")
        return False

    with open(INDEX_HTML, "r", encoding="utf-8") as f:
        html = f.read()

    today = datetime.now().strftime("%A, %B %d, %Y")

    # 1. JS registry block
    if JS_START in html and JS_END in html:
        entries = ",\n".join(_js_entry(a) for a in articles)
        new_block = f"{JS_START}\n{entries}\n{JS_END}"
        html = re.sub(
            re.escape(JS_START) + r".*?" + re.escape(JS_END),
            new_block, html, flags=re.DOTALL,
        )
        logger.info(f"Injected {len(articles)} JS entries")
    else:
        logger.warning("JS markers not found — appending to const A")
        entries = ",\n".join(_js_entry(a) for a in articles)
        html = html.replace("const A = {", f"const A = {{\n{entries},\n", 1)

    # 2. Homepage cards (show latest 8)
    if CARD_START in html and CARD_END in html:
        cards = "".join(_card_html(a) for a in articles[:8])
        html = re.sub(
            re.escape(CARD_START) + r".*?" + re.escape(CARD_END),
            f"{CARD_START}{cards}\n      {CARD_END}",
            html, flags=re.DOTALL,
        )
        logger.info("Updated homepage cards")

    # 3. Date in header
    html = re.sub(
        r"(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday),\s+\w+\s+\d{1,2},\s+\d{4}",
        today, html,
    )

    # 4. Footer "Updated" line
    html = re.sub(r"Updated \w+ \w+ \d{1,2}, \d{4}", f"Updated {today}", html)

    # 5. Hero — update with latest article
    if articles:
        hero = articles[0]
        html = re.sub(
            r'class="htitle"[^>]*onclick="openA\(\'[^\']*\'\)">[^<]+</h1>',
            f'class="htitle" onclick="openA(\'{hero["slug"]}\')">{hero["title"]}</h1>',
            html,
        )

    with open(INDEX_HTML, "w", encoding="utf-8") as f:
        f.write(html)

    logger.info(f"✅ index.html updated — {today}")
    return True


# ── SITEMAP ───────────────────────────────────────────────────────────────────

def generate_sitemap(articles: list[dict]) -> None:
    today = datetime.now().strftime("%Y-%m-%d")
    urls = [
        f"""  <url>
    <loc>{SITE_URL}/</loc>
    <lastmod>{today}</lastmod>
    <changefreq>daily</changefreq>
    <priority>1.0</priority>
  </url>"""
    ]
    for a in articles:
        slug = a.get("slug", "")
        date = a.get("published_at", today)
        # Convert "June 26, 2026" → "2026-06-26"
        try:
            dt = datetime.strptime(date, "%B %d, %Y")
            iso = dt.strftime("%Y-%m-%d")
        except ValueError:
            iso = today
        urls.append(f"""  <url>
    <loc>{SITE_URL}/#article-{slug}</loc>
    <lastmod>{iso}</lastmod>
    <changefreq>monthly</changefreq>
    <priority>0.8</priority>
  </url>""")

    xml = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        + "\n".join(urls)
        + "\n</urlset>\n"
    )
    with open(SITEMAP_XML, "w", encoding="utf-8") as f:
        f.write(xml)
    logger.info(f"Sitemap: {len(urls)} URLs → sitemap.xml")


# ── RSS FEED ─────────────────────────────────────────────────────────────────

def generate_rss(articles: list[dict]) -> None:
    now_rfc = formatdate(localtime=False)
    items = []
    for a in articles[:20]:
        title    = a.get("title", "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        desc     = a.get("excerpt", "").replace("&", "&amp;")
        slug     = a.get("slug", "")
        cats     = "".join(f"    <category>{c}</category>" for c in a.get("tags", []))
        body     = a.get("body_html", "")
        src_url  = a.get("source_url", "")
        src_name = a.get("source_name", "")
        # pub date
        try:
            dt = datetime.strptime(a.get("published_at", ""), "%B %d, %Y")
            pub_date = formatdate(dt.timestamp(), localtime=False)
        except Exception:
            pub_date = now_rfc

        items.append(f"""  <item>
    <title><![CDATA[{a.get('title','')}]]></title>
    <link>{SITE_URL}/#article-{slug}</link>
    <guid isPermaLink="false">{SITE_URL}/#article-{slug}</guid>
    <description><![CDATA[{a.get('excerpt','')}]]></description>
    <content:encoded><![CDATA[{body}]]></content:encoded>
    <pubDate>{pub_date}</pubDate>
    <author>contact@marrakechdaily.com ({a.get('author','Marrakech Daily Staff')})</author>
{cats}
    <source url="{src_url}">{src_name}</source>
  </item>""")

    rss = f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0"
  xmlns:content="http://purl.org/rss/1.0/modules/content/"
  xmlns:atom="http://www.w3.org/2005/Atom">
  <channel>
    <title>{SITE_NAME}</title>
    <link>{SITE_URL}/</link>
    <description>{SITE_TAGLINE}</description>
    <language>en-us</language>
    <lastBuildDate>{now_rfc}</lastBuildDate>
    <atom:link href="{SITE_URL}/feed.xml" rel="self" type="application/rss+xml"/>
    <image>
      <url>{SITE_URL}/og-image.jpg</url>
      <title>{SITE_NAME}</title>
      <link>{SITE_URL}/</link>
    </image>
{chr(10).join(items)}
  </channel>
</rss>
"""
    with open(RSS_XML, "w", encoding="utf-8") as f:
        f.write(rss)
    logger.info(f"RSS feed: {len(items)} items → feed.xml")
