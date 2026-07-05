"""
Marrakech Daily — Multi-source Scraper
Supports HTML scraping + RSS feeds with retry logic.
"""
import hashlib
import logging
import re
import time
from typing import Optional
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

from config import HTTP_TIMEOUT, HTTP_RETRIES, CRAWL_DELAY, MIN_WORDS, SOURCES

logger = logging.getLogger("scraper")

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,*/*;q=0.9",
    "Accept-Language": "fr-FR,fr;q=0.9,en;q=0.8",
    "Accept-Encoding": "gzip, deflate, br",
    "Cache-Control": "no-cache",
}

SKIP_URL_PATTERNS = re.compile(
    r"(facebook\.com|twitter\.com|instagram|youtube|whatsapp"
    r"|linkedin|telegram|mailto:|javascript:"
    r"|/login|/register|/contact|/about|/privacy|/terms"
    r"|/tag/|/author/|/page/\d+|\?s=|#comment|\.pdf$|\.jpg$|\.png$)",
    re.IGNORECASE,
)


def _fetch(url: str, retries: int = HTTP_RETRIES) -> Optional[requests.Response]:
    """GET with exponential back-off retry."""
    for attempt in range(1, retries + 1):
        try:
            resp = requests.get(url, headers=HEADERS, timeout=HTTP_TIMEOUT, allow_redirects=True)
            if resp.status_code == 200:
                return resp
            elif resp.status_code in (429, 503):
                wait = 10 * attempt
                logger.warning(f"Rate-limited ({resp.status_code}), waiting {wait}s — {url}")
                time.sleep(wait)
            else:
                logger.debug(f"HTTP {resp.status_code} — {url}")
                return None
        except requests.RequestException as exc:
            logger.warning(f"Attempt {attempt}/{retries} failed: {exc} — {url}")
            if attempt < retries:
                time.sleep(3 * attempt)
    return None


def _url_hash(url: str) -> str:
    return hashlib.md5(url.encode()).hexdigest()


def _is_article_url(url: str, pattern: str, base_domain: str) -> bool:
    parsed = urlparse(url)
    if parsed.netloc and base_domain not in parsed.netloc:
        return False
    if SKIP_URL_PATTERNS.search(url):
        return False
    path = parsed.path.rstrip("/")
    if len(path) < 5:
        return False
    if pattern and re.search(pattern, url):
        return True
    # Heuristic: path has at least 1 segment with 4+ chars
    segments = [s for s in path.split("/") if len(s) >= 4]
    return len(segments) >= 1


def _get_links_from_page(soup: BeautifulSoup, base_url: str, pattern: str) -> list[str]:
    base_domain = urlparse(base_url).netloc
    seen, links = set(), []
    for tag in soup.find_all("a", href=True):
        href = tag["href"].strip()
        if not href:
            continue
        abs_url = urljoin(base_url, href).split("?")[0].split("#")[0]
        if abs_url in seen:
            continue
        seen.add(abs_url)
        if _is_article_url(abs_url, pattern, base_domain):
            links.append(abs_url)
    return links


def _extract_text(soup: BeautifulSoup) -> tuple[str, str]:
    """Return (title, body_text) from article page."""
    # Title
    title = ""
    for sel in ["h1.entry-title", "h1.post-title", "h1.article-title", "h1", ".story-title h1"]:
        el = soup.select_one(sel)
        if el:
            title = el.get_text(" ", strip=True)
            break

    # Body — try known selectors in order
    body = ""
    for sel in [
        "article .entry-content",
        ".entry-content",
        ".post-content",
        ".article-content",
        ".article-body",
        ".story-content",
        ".post-body",
        "article",
        "main .content",
        "main",
    ]:
        el = soup.select_one(sel)
        if el:
            # Remove unwanted inner elements
            for rm in el.select("script,style,nav,header,footer,.ad,.advertisement,.share,.social,.comments"):
                rm.decompose()
            paras = [p.get_text(" ", strip=True) for p in el.find_all(["p", "h2", "h3", "li"]) if p.get_text(strip=True)]
            body = "\n".join(paras)
            if len(body.split()) >= MIN_WORDS:
                break

    # Last resort
    if len(body.split()) < MIN_WORDS:
        paras = [p.get_text(" ", strip=True) for p in soup.find_all("p") if len(p.get_text(strip=True)) > 30]
        body = "\n".join(paras)

    return title.strip(), body.strip()


def scrape_rss(rss_url: str, limit: int = 15) -> list[dict]:
    """Parse RSS feed and return list of {url, title} dicts."""
    resp = _fetch(rss_url)
    if not resp:
        return []
    try:
        soup = BeautifulSoup(resp.text, "xml")
        items = []
        for item in soup.find_all("item")[:limit]:
            url   = (item.find("link") or item.find("guid") or {}).get_text(strip=True) if hasattr(item.find("link") or {}, "get_text") else ""
            title = item.find("title").get_text(strip=True) if item.find("title") else ""
            if url and title:
                items.append({"url": url, "raw_title": title})
        return items
    except Exception as e:
        logger.warning(f"RSS parse error: {e}")
        return []


def scrape_source(source: dict, already_seen: set) -> list[dict]:
    """
    Scrape one source. Returns list of raw article dicts.
    already_seen: set of URL hashes already in registry.
    """
    sid   = source["id"]
    quota = source["quota"]
    pattern = source.get("link_pattern", "")
    logger.info(f"[{sid}] Scraping {source['url']} (quota={quota})")

    candidate_urls = []

    # Try RSS first
    if source.get("rss"):
        rss_items = scrape_rss(source["rss"], limit=quota * 3)
        candidate_urls = [i["url"] for i in rss_items]
        logger.info(f"[{sid}] RSS gave {len(candidate_urls)} candidates")

    # Fallback to HTML link extraction
    if not candidate_urls:
        resp = _fetch(source["url"])
        if not resp:
            logger.warning(f"[{sid}] Index page unreachable")
            return []
        soup = BeautifulSoup(resp.text, "html.parser")
        candidate_urls = _get_links_from_page(soup, source["url"], pattern)
        logger.info(f"[{sid}] HTML gave {len(candidate_urls)} candidates")

    results = []
    for url in candidate_urls:
        if len(results) >= quota:
            break

        h = _url_hash(url)
        if h in already_seen:
            logger.debug(f"[{sid}] Skip (already published): {url}")
            continue

        time.sleep(CRAWL_DELAY)
        resp = _fetch(url)
        if not resp:
            continue

        soup = BeautifulSoup(resp.text, "html.parser")
        title, body = _extract_text(soup)

        if len(title) < 15:
            logger.debug(f"[{sid}] Skip (no title): {url}")
            continue
        if len(body.split()) < MIN_WORDS:
            logger.debug(f"[{sid}] Skip (thin: {len(body.split())} words): {url}")
            continue

        art = {
            "url":           url,
            "url_hash":      h,
            "source_id":     sid,
            "source_name":   source["name"],
            "source_lang":   source["lang"],
            "category_hint": source["category_hint"],
            "raw_title":     title,
            "raw_body":      body[:6000],  # cap for AI
        }
        results.append(art)
        logger.info(f"[{sid}] ✓ {title[:70]}")

    logger.info(f"[{sid}] → {len(results)} articles collected")
    return results


def scrape_all(already_seen: set) -> list[dict]:
    """Scrape all configured sources. Returns combined list."""
    all_raw = []
    for source in SOURCES:
        try:
            raw = scrape_source(source, already_seen)
            all_raw.extend(raw)
        except Exception as exc:
            logger.error(f"Source {source['id']} crashed: {exc}", exc_info=True)
    logger.info(f"Total raw articles collected: {len(all_raw)}")
    return all_raw
