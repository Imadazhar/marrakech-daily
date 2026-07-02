"""
Marrakech Daily — Web Scraper
Fetches article links and raw content from configured sources.
"""

import time
import logging
import re
from typing import Optional
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

from config import SOURCES, HTTP_TIMEOUT, HTTP_RETRIES, HTTP_BACKOFF, MIN_CONTENT_WORDS, MAX_CONTENT_WORDS

logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "fr-FR,fr;q=0.9,en;q=0.8",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

# Patterns to skip (nav, ads, social)
SKIP_PATTERNS = re.compile(
    r"(facebook|twitter|instagram|linkedin|youtube|whatsapp|"
    r"login|register|contact|about|privacy|terms|sitemap|"
    r"tag/|category/|author/|page/|\?s=|#|javascript:)",
    re.IGNORECASE,
)

# Minimum meaningful title length
MIN_TITLE_LEN = 25


def _fetch(url: str, retries: int = HTTP_RETRIES) -> Optional[requests.Response]:
    """GET with retry + exponential backoff."""
    for attempt in range(1, retries + 1):
        try:
            resp = requests.get(url, headers=HEADERS, timeout=HTTP_TIMEOUT)
            resp.raise_for_status()
            return resp
        except requests.RequestException as exc:
            logger.warning(f"Attempt {attempt}/{retries} failed for {url}: {exc}")
            if attempt < retries:
                time.sleep(HTTP_BACKOFF * attempt)
    logger.error(f"All retries exhausted for {url}")
    return None


def _is_article_url(url: str, base_domain: str) -> bool:
    """Heuristic: is this URL likely an article (not a nav/category page)?"""
    parsed = urlparse(url)
    if parsed.netloc and base_domain not in parsed.netloc:
        return False                   # external link
    if SKIP_PATTERNS.search(url):
        return False
    path = parsed.path.rstrip("/")
    segments = [s for s in path.split("/") if s]
    return len(segments) >= 1 and len(path) > 10


def _extract_links(soup: BeautifulSoup, base_url: str) -> list[str]:
    """Return candidate article URLs from a listing page."""
    base_domain = urlparse(base_url).netloc
    seen = set()
    links = []
    for tag in soup.find_all("a", href=True):
        href = tag["href"].strip()
        abs_url = urljoin(base_url, href)
        if abs_url in seen:
            continue
        seen.add(abs_url)
        if _is_article_url(abs_url, base_domain):
            links.append(abs_url)
    return links


def _extract_content(soup: BeautifulSoup, selectors: dict) -> tuple[str, str]:
    """
    Returns (title, body_text) from an article page.
    Falls back gracefully when selectors don't match.
    """
    # Title
    title = ""
    for sel in [selectors.get("title", "h1"), "h1", "h2"]:
        tag = soup.select_one(sel)
        if tag:
            title = tag.get_text(" ", strip=True)
            break

    # Body — try several selectors before falling back to all <p> tags
    body_text = ""
    for sel in [
        selectors.get("body", ""),
        "article",
        ".entry-content",
        ".post-content",
        ".article-content",
        ".story-content",
        ".article-body",
        "main",
    ]:
        if not sel:
            continue
        container = soup.select_one(sel)
        if container:
            paragraphs = container.find_all("p")
            body_text = "\n".join(p.get_text(" ", strip=True) for p in paragraphs if p.get_text(strip=True))
            if len(body_text.split()) >= MIN_CONTENT_WORDS:
                break

    # Last resort: grab all <p> from the page
    if len(body_text.split()) < MIN_CONTENT_WORDS:
        paragraphs = soup.find_all("p")
        body_text = "\n".join(p.get_text(" ", strip=True) for p in paragraphs if p.get_text(strip=True))

    # Truncate to keep AI prompt reasonable
    words = body_text.split()
    if len(words) > MAX_CONTENT_WORDS:
        body_text = " ".join(words[:MAX_CONTENT_WORDS]) + " [...]"

    return title.strip(), body_text.strip()


def scrape_source(source: dict, limit: int = 15) -> list[dict]:
    """
    Crawl a single source, return list of raw article dicts:
      { url, source_name, source_lang, raw_title, raw_body }
    """
    logger.info(f"Scraping source: {source['name']} → {source['url']}")
    index_resp = _fetch(source["url"])
    if not index_resp:
        return []

    soup = BeautifulSoup(index_resp.text, "html.parser")
    links = _extract_links(soup, source["url"])
    logger.info(f"  Found {len(links)} candidate links")

    results = []
    for url in links[:limit * 2]:          # over-fetch to hit target after filtering
        if len(results) >= limit:
            break

        resp = _fetch(url)
        if not resp:
            continue

        art_soup = BeautifulSoup(resp.text, "html.parser")
        raw_title, raw_body = _extract_content(art_soup, source["selectors"])

        if len(raw_title) < MIN_TITLE_LEN:
            logger.debug(f"  Skip (short title): {url}")
            continue
        if len(raw_body.split()) < MIN_CONTENT_WORDS:
            logger.debug(f"  Skip (thin content: {len(raw_body.split())} words): {url}")
            continue

        results.append({
            "url": url,
            "source_name": source["name"],
            "source_lang": source["lang"],
            "raw_title": raw_title,
            "raw_body": raw_body,
        })
        logger.info(f"  ✓ Collected: {raw_title[:70]}")
        time.sleep(0.8)   # polite crawl delay

    logger.info(f"  → {len(results)} articles collected from {source['name']}")
    return results


def scrape_all(articles_per_source: dict[str, int]) -> list[dict]:
    """Scrape all configured sources. articles_per_source = {source_name: limit}"""
    all_raw = []
    for source in SOURCES:
        limit = articles_per_source.get(source["name"], source["weight"])
        raw = scrape_source(source, limit=limit)
        all_raw.extend(raw)
    return all_raw
