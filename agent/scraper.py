"""
Marrakech Daily — Multi-source web scraper.
Handles HTML scrapers + RSS feeds for all configured news sources.
"""
from __future__ import annotations

import hashlib
import logging
import re
import time
from typing import Optional
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup
from tenacity import retry, stop_after_attempt, wait_exponential

from config import (
    NEWS_SOURCES, REQUEST_HEADERS, REQUEST_TIMEOUT,
    MAX_RETRY_ATTEMPTS, RETRY_WAIT_MIN, RETRY_WAIT_MAX,
    MIN_SOURCE_TEXT_WORDS, MAX_PER_SOURCE,
)

log = logging.getLogger(__name__)

# URLs to skip
SKIP_PATTERNS = re.compile(
    r"(facebook\.com|twitter\.com|instagram|youtube|whatsapp|linkedin"
    r"|mailto:|javascript:|tel:"
    r"|/login|/register|/contact|/about|/privacy|/terms|/cookies"
    r"|/tag/|/author/|/page/\d+|/feed|/rss|\?s=|#|\.pdf$|\.jpg$|\.png$|\.mp4$)",
    re.IGNORECASE,
)

MIN_TITLE_LEN = 20
CRAWL_DELAY   = 1.0   # polite delay between requests


# ── HTTP ───────────────────────────────────────────────────────────────────────

@retry(
    stop=stop_after_attempt(MAX_RETRY_ATTEMPTS),
    wait=wait_exponential(min=RETRY_WAIT_MIN, max=RETRY_WAIT_MAX),
    reraise=False,
)
def _get(url: str) -> Optional[requests.Response]:
    try:
        resp = requests.get(
            url,
            headers=REQUEST_HEADERS,
            timeout=REQUEST_TIMEOUT,
            allow_redirects=True,
        )
        if resp.status_code == 200:
            return resp
        if resp.status_code in (429, 503):
            log.warning("Rate limited (%s): %s — waiting", resp.status_code, url)
            time.sleep(15)
            raise requests.RequestException(f"Rate limited: {resp.status_code}")
        log.debug("HTTP %s: %s", resp.status_code, url)
        return None
    except requests.RequestException as exc:
        log.warning("Fetch error: %s — %s", exc, url)
        raise


def _url_hash(url: str) -> str:
    return hashlib.md5(url.strip().encode()).hexdigest()


def _is_article_url(url: str, base_domain: str) -> bool:
    p = urlparse(url)
    if p.netloc and base_domain not in p.netloc:
        return False
    if SKIP_PATTERNS.search(url):
        return False
    path = p.path.rstrip("/")
    if len(path) < 8:
        return False
    segs = [s for s in path.split("/") if len(s) >= 4]
    return len(segs) >= 1


def _find_links(soup: BeautifulSoup, base_url: str) -> list[str]:
    base_domain = urlparse(base_url).netloc
    seen, links = set(), []
    for tag in soup.find_all("a", href=True):
        href = tag["href"].strip()
        if not href:
            continue
        abs_url = urljoin(base_url, href).split("?")[0].rstrip("/")
        if abs_url in seen:
            continue
        seen.add(abs_url)
        if _is_article_url(abs_url, base_domain):
            links.append(abs_url)
    return links


# ── Content extraction ─────────────────────────────────────────────────────────

def _extract(soup: BeautifulSoup) -> tuple[str, str]:
    """Return (title, body_text)."""
    title = ""
    for sel in ["h1.entry-title", "h1.post-title", "h1.article-title",
                "h1.title", "h1", ".story-title", ".article__title"]:
        el = soup.select_one(sel)
        if el:
            title = el.get_text(" ", strip=True)
            break

    body = ""
    for sel in [
        "article .entry-content", ".entry-content", ".post-content",
        ".article-content", ".article-body", ".story-content",
        ".article__body", ".post-body", ".content-body",
        "article", "main .content", ".main-content", "main",
    ]:
        el = soup.select_one(sel)
        if not el:
            continue
        # Remove noise
        for noise in el.select(
            "script,style,nav,header,footer,aside,.ad,.advertisement,"
            ".share-buttons,.social-share,.comments,.related-posts,"
            ".newsletter-widget,.sidebar,.widget"
        ):
            noise.decompose()
        paras = [
            p.get_text(" ", strip=True)
            for p in el.find_all(["p", "h2", "h3", "li", "blockquote"])
            if len(p.get_text(strip=True)) > 20
        ]
        body = "\n".join(paras)
        if len(body.split()) >= MIN_SOURCE_TEXT_WORDS:
            break

    # Last resort
    if len(body.split()) < MIN_SOURCE_TEXT_WORDS:
        paras = [
            p.get_text(" ", strip=True)
            for p in soup.find_all("p")
            if len(p.get_text(strip=True)) > 30
        ]
        body = "\n".join(paras)

    return title.strip(), body.strip()[:8000]


# ── RSS parser ─────────────────────────────────────────────────────────────────

def _parse_rss(url: str, limit: int = 20) -> list[dict]:
    resp = _get(url)
    if not resp:
        return []
    try:
        soup = BeautifulSoup(resp.content, "xml")
        items = []
        for item in soup.find_all("item")[:limit]:
            link_el  = item.find("link")
            title_el = item.find("title")
            desc_el  = item.find("description") or item.find("summary")
            link  = link_el.get_text(strip=True) if link_el else ""
            title = title_el.get_text(strip=True) if title_el else ""
            desc  = BeautifulSoup(desc_el.get_text(strip=True), "html.parser").get_text() if desc_el else ""
            if link and len(title) >= MIN_TITLE_LEN:
                items.append({"url": link, "raw_title": title, "raw_body": desc[:2000]})
        return items
    except Exception as exc:
        log.warning("RSS parse error %s: %s", url, exc)
        return []


# ── Source-specific scrapers ───────────────────────────────────────────────────

def _scrape_kech24(listing_url: str, quota: int, seen: set) -> list[dict]:
    resp = _get(listing_url)
    if not resp:
        return []
    soup    = BeautifulSoup(resp.text, "html.parser")
    links   = _find_links(soup, listing_url)
    # Kech24 articles have slugs like /2024/06/25/article-name/
    links   = [l for l in links if re.search(r"/\d{4}/\d{2}/\d{2}/", l) or
               re.search(r"kech24\.com/[a-z]", l)]
    return _fetch_articles(links, "kech24", seen, quota, "fr")


def _scrape_madein_city(listing_url: str, quota: int, seen: set) -> list[dict]:
    resp = _get(listing_url)
    if not resp:
        return []
    soup  = BeautifulSoup(resp.text, "html.parser")
    links = _find_links(soup, listing_url)
    links = [l for l in links if "madein.city/marrakech" in l and "/stories/" in l]
    return _fetch_articles(links, "madein_city", seen, quota, "fr")


def _scrape_alphabourse(listing_url: str, quota: int, seen: set) -> list[dict]:
    resp = _get(listing_url)
    if not resp:
        return []
    soup  = BeautifulSoup(resp.text, "html.parser")
    links = _find_links(soup, listing_url)
    links = [l for l in links if "alphabourse.ma" in l]
    return _fetch_articles(links, "alphabourse", seen, quota, "fr")


def _scrape_generic(source: dict, seen: set) -> list[dict]:
    quota = min(source.get("daily_quota", 3), MAX_PER_SOURCE)
    listing_url = source["listing_url"]
    resp = _get(listing_url)
    if not resp:
        return []
    soup  = BeautifulSoup(resp.text, "html.parser")
    links = _find_links(soup, listing_url)
    return _fetch_articles(links, source["id"], seen, quota, source.get("language","fr"))


def _fetch_articles(links: list[str], source_id: str, seen: set,
                    quota: int, lang: str) -> list[dict]:
    results = []
    for url in links:
        if len(results) >= quota:
            break
        h = _url_hash(url)
        if h in seen:
            log.debug("Skip (seen): %s", url)
            continue

        time.sleep(CRAWL_DELAY)
        resp = _get(url)
        if not resp:
            continue

        soup = BeautifulSoup(resp.text, "html.parser")
        title, body = _extract(soup)

        if len(title) < MIN_TITLE_LEN:
            log.debug("Skip (no title): %s", url)
            continue
        if len(body.split()) < MIN_SOURCE_TEXT_WORDS:
            log.debug("Skip (thin content %d words): %s", len(body.split()), url)
            continue

        results.append({
            "url":        url,
            "url_hash":   h,
            "source_id":  source_id,
            "source_lang": lang,
            "raw_title":  title,
            "raw_body":   body,
        })
        log.info("✓ [%s] %s", source_id, title[:70])

    return results


# ── Main scrape entry point ────────────────────────────────────────────────────

def scrape_all(seen_hashes: set) -> list[dict]:
    """
    Scrape all configured sources.
    seen_hashes: set of URL md5 hashes already published — skip these.
    Returns list of raw article dicts.
    """
    all_raw: list[dict] = []

    for source in NEWS_SOURCES:
        sid   = source["id"]
        quota = min(source.get("daily_quota", 3), MAX_PER_SOURCE)
        stype = source.get("scraper", "generic")
        log.info("Scraping [%s] %s (quota=%d)", sid, source["listing_url"], quota)

        try:
            if stype == "rss":
                rss_items = _parse_rss(source["listing_url"], limit=quota * 2)
                # For RSS we have title+desc but no full body yet
                batch = []
                for item in rss_items:
                    h = _url_hash(item["url"])
                    if h in seen_hashes:
                        continue
                    if len(batch) >= quota:
                        break
                    # Try to fetch full body
                    time.sleep(CRAWL_DELAY)
                    resp = _get(item["url"])
                    if resp:
                        soup = BeautifulSoup(resp.text, "html.parser")
                        _, full_body = _extract(soup)
                        body = full_body if len(full_body.split()) >= MIN_SOURCE_TEXT_WORDS else item["raw_body"]
                    else:
                        body = item["raw_body"]
                    batch.append({
                        "url":         item["url"],
                        "url_hash":    h,
                        "source_id":   sid,
                        "source_lang": source.get("language", "en"),
                        "raw_title":   item["raw_title"],
                        "raw_body":    body,
                    })
                    log.info("✓ [%s] %s", sid, item["raw_title"][:70])
                all_raw.extend(batch)

            elif stype == "kech24":
                batch = _scrape_kech24(source["listing_url"], quota, seen_hashes)
                all_raw.extend(batch)

            elif stype == "madein_city":
                batch = _scrape_madein_city(source["listing_url"], quota, seen_hashes)
                all_raw.extend(batch)

            elif stype == "alphabourse":
                batch = _scrape_alphabourse(source["listing_url"], quota, seen_hashes)
                all_raw.extend(batch)

            else:
                batch = _scrape_generic(source, seen_hashes)
                all_raw.extend(batch)

            log.info("[%s] → %d articles collected", sid,
                     len([x for x in all_raw if x.get("source_id") == sid]))

        except Exception as exc:
            log.error("Source [%s] crashed: %s", sid, exc, exc_info=True)

    log.info("Total raw articles: %d", len(all_raw))
    return all_raw
