"""
Web scrapers for the three news sources.

Each scraper returns a list of raw article dicts:
  {
    "url":     str,            # canonical article URL
    "title":   str,            # original title (French)
    "excerpt": str | None,     # teaser / lead paragraph
    "content": str | None,     # main body text (may be empty; caller can fetch)
    "image":   str | None,     # absolute image URL
    "source":  str,            # source display name
    "source_id": str,          # source id key
    "published_raw": str | None,
    "category_hint": str | None,
  }
"""

from __future__ import annotations

import logging
import re
import time
from typing import Optional
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from config import (
    NEWS_SOURCES,
    REQUEST_HEADERS,
    REQUEST_TIMEOUT,
    MAX_RETRY_ATTEMPTS,
    RETRY_WAIT_MIN,
    RETRY_WAIT_MAX,
    MIN_SOURCE_TEXT_WORDS,
)

log = logging.getLogger(__name__)


# ── HTTP helpers ──────────────────────────────────────────────────────────────

def _session() -> requests.Session:
    s = requests.Session()
    s.headers.update(REQUEST_HEADERS)
    return s


@retry(
    stop=stop_after_attempt(MAX_RETRY_ATTEMPTS),
    wait=wait_exponential(min=RETRY_WAIT_MIN, max=RETRY_WAIT_MAX),
    retry=retry_if_exception_type((requests.exceptions.Timeout,
                                   requests.exceptions.ConnectionError)),
    reraise=True,
)
def _get(url: str, session: requests.Session, **kwargs) -> requests.Response:
    resp = session.get(url, timeout=REQUEST_TIMEOUT, **kwargs)
    resp.raise_for_status()
    return resp


def _soup(html: str) -> BeautifulSoup:
    return BeautifulSoup(html, "html.parser")


def _abs(url: str, base: str) -> str:
    return urljoin(base, url)


def _clean_text(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


# ── Article content fetcher ───────────────────────────────────────────────────

def fetch_article_text(url: str, session: requests.Session) -> str:
    """
    Fetch the full article body text from a URL.
    Tries trafilatura first, falls back to BeautifulSoup heuristics.
    """
    try:
        resp = _get(url, session)
        html = resp.text

        # Try trafilatura (best for content extraction)
        try:
            import trafilatura
            text = trafilatura.extract(html, include_comments=False,
                                        include_tables=False,
                                        no_fallback=False)
            if text and len(text.split()) >= MIN_SOURCE_TEXT_WORDS:
                return _clean_text(text)
        except ImportError:
            pass

        # Fallback: heuristic BS4 extraction
        soup = _soup(html)
        for tag in soup(["script", "style", "nav", "header", "footer",
                          "aside", "form", "figure", "figcaption", "noscript"]):
            tag.decompose()

        # Candidate selectors (most news CMSes)
        selectors = [
            "article",
            '[class*="article-body"]',
            '[class*="entry-content"]',
            '[class*="post-content"]',
            '[class*="content-body"]',
            "main",
            ".content",
        ]
        for sel in selectors:
            node = soup.select_one(sel)
            if node:
                text = _clean_text(node.get_text(" "))
                if len(text.split()) >= MIN_SOURCE_TEXT_WORDS:
                    return text

        # Last resort: all paragraph text
        paras = [p.get_text(" ") for p in soup.find_all("p")]
        return _clean_text(" ".join(paras))

    except Exception as exc:
        log.warning("Could not fetch article text from %s: %s", url, exc)
        return ""


# ── Kech24 scraper ────────────────────────────────────────────────────────────

def scrape_kech24(source: dict, session: requests.Session) -> list[dict]:
    articles: list[dict] = []
    base = source["base_url"]
    url  = source["listing_url"]
    log.info("Scraping %s → %s", source["name"], url)

    try:
        resp = _get(url, session)
        soup = _soup(resp.text)

        # kech24 uses <article> or <div class="jeg_post"> cards
        cards = soup.select("article") or soup.select('[class*="jeg_post"]') or []

        for card in cards[:25]:
            link_el = card.select_one("a[href]")
            title_el = card.select_one("h2, h3, .jeg_post_title, .entry-title")
            img_el   = card.select_one("img")
            excerpt_el = card.select_one(".jeg_post_excerpt, .entry-summary, p")

            if not link_el or not title_el:
                continue

            article_url = _abs(link_el["href"], base)
            if not article_url.startswith("http"):
                continue

            title = _clean_text(title_el.get_text())
            if len(title) < 15:
                continue

            excerpt = _clean_text(excerpt_el.get_text()) if excerpt_el else None
            img_url = None
            if img_el:
                img_url = img_el.get("src") or img_el.get("data-src") or img_el.get("data-lazy-src")
                if img_url and img_url.startswith("http"):
                    img_url = img_url
                else:
                    img_url = None

            # Guess category from URL
            category_hint = None
            for segment in ["sport", "economie", "culture", "societe", "international",
                             "politique", "sante", "education", "marrakech", "maroc"]:
                if segment in article_url.lower():
                    category_hint = segment
                    break

            articles.append({
                "url":            article_url,
                "title":          title,
                "excerpt":        excerpt,
                "content":        None,
                "image":          img_url,
                "source":         source["name"],
                "source_id":      source["id"],
                "published_raw":  None,
                "category_hint":  category_hint,
            })

    except Exception as exc:
        log.error("kech24 scrape failed: %s", exc, exc_info=True)

    log.info("kech24 found %d raw articles", len(articles))
    return articles


# ── Made In City scraper ──────────────────────────────────────────────────────

def scrape_madein_city(source: dict, session: requests.Session) -> list[dict]:
    articles: list[dict] = []
    base = source["base_url"]
    url  = source["listing_url"]
    log.info("Scraping %s → %s", source["name"], url)

    try:
        resp = _get(url, session)
        soup = _soup(resp.text)

        # madein.city uses <article> or generic grid cards
        cards = (soup.select("article") or
                 soup.select('[class*="story"]') or
                 soup.select('[class*="card"]') or [])

        # Also try <a> elements that link to story URLs
        if not cards:
            cards = [a for a in soup.find_all("a", href=True)
                     if "/stories/" in a.get("href", "")]

        seen_urls: set[str] = set()

        for card in cards[:25]:
            # Determine link element
            if card.name == "a":
                link_el = card
            else:
                link_el = card.select_one("a[href]")
            if not link_el:
                continue

            href = link_el.get("href", "")
            article_url = _abs(href, base)
            if article_url in seen_urls or not article_url.startswith("http"):
                continue
            seen_urls.add(article_url)

            title_el   = card.select_one("h1, h2, h3, h4")
            img_el     = card.select_one("img")
            excerpt_el = card.select_one("p, [class*='excerpt'], [class*='description']")

            title = _clean_text(title_el.get_text()) if title_el else _clean_text(link_el.get_text())
            if len(title) < 15:
                continue

            excerpt = _clean_text(excerpt_el.get_text()) if excerpt_el else None
            img_url = None
            if img_el:
                for attr in ("src", "data-src", "data-lazy-src"):
                    img_url = img_el.get(attr)
                    if img_url and img_url.startswith("http"):
                        break

            articles.append({
                "url":            article_url,
                "title":          title,
                "excerpt":        excerpt,
                "content":        None,
                "image":          img_url,
                "source":         source["name"],
                "source_id":      source["id"],
                "published_raw":  None,
                "category_hint":  "tourisme",   # madein.city is mostly lifestyle/tourism
            })

    except Exception as exc:
        log.error("madein_city scrape failed: %s", exc, exc_info=True)

    log.info("madein_city found %d raw articles", len(articles))
    return articles


# ── Alphabourse scraper ───────────────────────────────────────────────────────

def scrape_alphabourse(source: dict, session: requests.Session) -> list[dict]:
    articles: list[dict] = []
    base = source["base_url"]
    url  = source["listing_url"]
    log.info("Scraping %s → %s", source["name"], url)

    try:
        resp = _get(url, session)
        soup = _soup(resp.text)

        # alphabourse.ma uses <article> or div.article-item
        cards = (soup.select("article") or
                 soup.select('[class*="article"]') or
                 soup.select('[class*="news-item"]') or [])

        if not cards:
            # Fall back: h3 with links
            cards = soup.select("h3 a")

        seen_urls: set[str] = set()

        for card in cards[:25]:
            if card.name == "a":
                link_el = card
                title_el = card
            else:
                link_el  = card.select_one("a[href]")
                title_el = card.select_one("h2, h3, h4, .article-title, .title")
            if not link_el:
                continue

            href = link_el.get("href", "")
            article_url = _abs(href, base)
            if article_url in seen_urls or not article_url.startswith("http"):
                continue
            seen_urls.add(article_url)

            title = _clean_text(title_el.get_text()) if title_el else ""
            if len(title) < 15:
                continue

            img_el     = card.select_one("img") if hasattr(card, "select_one") else None
            excerpt_el = (card.select_one("p, [class*='excerpt']")
                          if hasattr(card, "select_one") else None)

            img_url = None
            if img_el:
                for attr in ("src", "data-src"):
                    img_url = img_el.get(attr)
                    if img_url and img_url.startswith("http"):
                        break

            category_hint = "bourse"
            for segment in ["marches", "economie", "bourse", "banques", "societe"]:
                if segment in article_url.lower():
                    category_hint = segment
                    break

            articles.append({
                "url":            article_url,
                "title":          title,
                "excerpt":        _clean_text(excerpt_el.get_text()) if excerpt_el else None,
                "content":        None,
                "image":          img_url,
                "source":         source["name"],
                "source_id":      source["id"],
                "published_raw":  None,
                "category_hint":  category_hint,
            })

    except Exception as exc:
        log.error("alphabourse scrape failed: %s", exc, exc_info=True)

    log.info("alphabourse found %d raw articles", len(articles))
    return articles


# ── Dispatcher ────────────────────────────────────────────────────────────────

SCRAPER_MAP = {
    "kech24":      scrape_kech24,
    "madein_city": scrape_madein_city,
    "alphabourse": scrape_alphabourse,
}


def scrape_all_sources() -> list[dict]:
    """Scrape all configured sources and return raw article candidates."""
    session  = _session()
    all_raw: list[dict] = []

    for source in NEWS_SOURCES:
        scraper_fn = SCRAPER_MAP.get(source["scraper"])
        if not scraper_fn:
            log.warning("No scraper registered for %s", source["scraper"])
            continue
        try:
            raw = scraper_fn(source, session)
            all_raw.extend(raw)
        except Exception as exc:
            log.error("Source %s failed: %s", source["name"], exc, exc_info=True)
        # Be polite between sources
        time.sleep(1)

    log.info("Total raw articles collected: %d", len(all_raw))
    return all_raw


def enrich_with_content(articles: list[dict]) -> list[dict]:
    """Fetch the full body text for articles that don't have it yet."""
    session = _session()
    enriched = []
    for art in articles:
        if not art.get("content"):
            log.debug("Fetching content from %s", art["url"])
            art["content"] = fetch_article_text(art["url"], session)
            time.sleep(0.5)   # polite delay
        enriched.append(art)
    return enriched
