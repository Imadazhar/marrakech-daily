"""
AI pipeline: transforms raw French source articles into original English articles.

Uses the OpenAI Chat Completions API (gpt-4o-mini by default).
Each call produces a fully structured article JSON.
"""

from __future__ import annotations

import hashlib
import json
import logging
import random
import re
import unicodedata
from datetime import datetime, timezone, timedelta
from typing import Optional

import html as html_module
import re as _re

from openai import OpenAI
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)

from config import (
    OPENAI_API_KEY,
    OPENAI_MODEL,
    OPENAI_TEMP,
    OPENAI_MAX_TOKENS,
    AUTHORS,
    CATEGORIES,
    CATEGORY_KEYWORDS,
    CATEGORY_IMAGES,
    DEFAULT_IMAGE_ID,
    MAX_RETRY_ATTEMPTS,
)

log = logging.getLogger(__name__)

# Morocco Standard Time (UTC+1, year-round since 2019)
MOROCCO_TZ = timezone(timedelta(hours=1))


# ── Client ─────────────────────────────────────────────────────────────────────

def _client() -> OpenAI:
    if not OPENAI_API_KEY:
        raise RuntimeError(
            "OPENAI_API_KEY environment variable is not set. "
            "Add it as a GitHub Actions secret."
        )
    return OpenAI(api_key=OPENAI_API_KEY)


# ── Slug generation ────────────────────────────────────────────────────────────

def make_slug(title: str) -> str:
    """Generate a clean URL slug from a title."""
    # normalise accents
    title = unicodedata.normalize("NFKD", title)
    title = title.encode("ascii", "ignore").decode("ascii")
    title = title.lower()
    title = re.sub(r"[^\w\s-]", "", title)
    title = re.sub(r"[\s_]+", "-", title)
    title = re.sub(r"-+", "-", title).strip("-")
    # truncate slug to 80 chars at a word boundary
    if len(title) > 80:
        title = title[:80].rsplit("-", 1)[0]
    return title


# ── Category inference ─────────────────────────────────────────────────────────

def infer_category(title: str, content: str, hint: Optional[str]) -> str:
    """
    Infer the best category from keywords in title+content and an optional hint
    from the scraper. Falls back to 'National'.
    """
    text = (title + " " + (content or "")).lower()

    # Priority: Breaking detection
    breaking_words = ["urgent", "breaking", "alerte", "flash", "just in"]
    if any(w in text for w in breaking_words):
        return "Breaking"

    # Hint-based fast path
    if hint:
        hint_lower = hint.lower()
        for cat, keywords in CATEGORY_KEYWORDS.items():
            if any(k in hint_lower for k in keywords):
                return cat

    # Keyword scan
    scores: dict[str, int] = {c: 0 for c in CATEGORIES}
    for cat, keywords in CATEGORY_KEYWORDS.items():
        for kw in keywords:
            if kw in text:
                scores[cat] += 1

    best = max(scores, key=lambda c: scores[c])
    return best if scores[best] > 0 else "National"


# ── Image selection ────────────────────────────────────────────────────────────

def pick_image(category: str, source_image: Optional[str] = None) -> str:
    """
    Return an Unsplash image URL for the article.
    Prefer the scraped source image if it looks usable, otherwise
    pick from our curated per-category set.
    """
    if source_image and source_image.startswith("https://") and len(source_image) > 30:
        # Use source image directly
        return source_image

    pool = CATEGORY_IMAGES.get(category, [DEFAULT_IMAGE_ID])
    photo_id = random.choice(pool)
    return f"https://images.unsplash.com/{photo_id}?w=1200&q=80"


def pick_image_thumb(category: str, source_image: Optional[str] = None) -> str:
    """Thumbnail variant (600px width)."""
    full = pick_image(category, source_image)
    return re.sub(r"\?.*", "?w=600&q=70", full)


# ── Reading time ───────────────────────────────────────────────────────────────


# ── HTML sanitiser ─────────────────────────────────────────────────────────────

# Only these tags are allowed in article body HTML.
_ALLOWED_TAGS = {"p", "em", "strong", "br"}
_ALLOWED_TAG_WITH_HREF = {"a"}   # only href allowed, and only http(s)/mailto


def _safe_href(href: str) -> str:
    href = href.strip()
    if href.startswith(("http://", "https://", "mailto:")):
        return href
    return "#"


def sanitise_body_html(raw_html: str) -> str:
    """
    Strip all HTML tags except a safe allowlist.
    Allowed: <p>, <em>, <strong>, <br>, <a href="…"> (http/https/mailto only).
    All other tags are removed; their text content is preserved inside <p>.
    Attributes other than href on <a> are stripped.
    """
    from html.parser import HTMLParser

    class _Sanitiser(HTMLParser):
        def __init__(self) -> None:
            super().__init__(convert_charrefs=True)
            self.out: list[str] = []
            self._stack: list[str] = []

        def handle_starttag(self, tag: str, attrs: list) -> None:
            tag = tag.lower()
            if tag in _ALLOWED_TAGS:
                self.out.append(f"<{tag}>")
                self._stack.append(tag)
            elif tag in _ALLOWED_TAG_WITH_HREF:
                attr_dict = dict(attrs)
                href = _safe_href(attr_dict.get("href", "#"))
                self.out.append(
                    f'<a href="{html_module.escape(href)}" '
                    'target="_blank" rel="noopener noreferrer">'
                )
                self._stack.append("a")
            # else: skip tag, keep text

        def handle_endtag(self, tag: str) -> None:
            tag = tag.lower()
            if self._stack and self._stack[-1] == tag and tag in (_ALLOWED_TAGS | _ALLOWED_TAG_WITH_HREF):
                self.out.append(f"</{tag}>")
                self._stack.pop()

        def handle_data(self, data: str) -> None:
            self.out.append(html_module.escape(data))

    s = _Sanitiser()
    s.feed(raw_html)
    # Close any unclosed allowed tags
    for tag in reversed(s._stack):
        s.out.append(f"</{tag}>")
    result = "".join(s.out)
    # Collapse multiple blank lines
    result = _re.sub(r"(<p>\s*</p>)+", "", result)
    return result.strip()


def estimate_reading_time(text: str) -> int:
    words = len(text.split())
    return max(1, round(words / 220))   # average reading speed 220 wpm


# ── The AI rewrite call ────────────────────────────────────────────────────────

SYSTEM_PROMPT = """\
You are the chief editor of Marrakech Daily, an independent English-language newspaper
covering Marrakech, Morocco and the region.

Your job: given raw source material (in French), write a completely original English article.

Rules:
- NEVER translate directly. Extract the key facts and write an original article.
- Preserve only factual information — no opinions, no fabrications.
- English must be fluent, journalistic, and publication-ready.
- Do NOT copy any sentence from the source.
- Attribute the original source with its name and URL.
- Do not mention that you are an AI.
- Write as if you are a seasoned journalist.
- Do not use emojis in the body text.
"""

USER_PROMPT_TEMPLATE = """\
SOURCE MATERIAL (French, do NOT translate — extract facts only):

Title: {title}
URL: {url}
Source: {source}

Content:
{content}

---

Return ONLY a valid JSON object (no markdown fences, no extra text) with these exact fields:
{{
  "title":        "<SEO-friendly English headline, max 90 chars, compelling and factual>",
  "excerpt":      "<2-sentence teaser that makes the reader want to click, 30-50 words>",
  "description":  "<SEO meta description, 130-155 chars, includes primary keywords>",
  "body":         "<Full article body in HTML. Use <p> tags only. 4-7 paragraphs. 350-600 words. End with attribution sentence.>",
  "tags":         ["<tag1>", "<tag2>", "<tag3>", "<tag4>", "<tag5>"],
  "category":     "<one of: Breaking | National | Business | Sport | Culture | Tourism | Society | Technology | Health | International>",
  "is_breaking":  <true or false>
}}

The body MUST end with this attribution paragraph:
<p><em>Source: <a href="{url}" target="_blank" rel="noopener">{source}</a>. Marrakech Daily presents this independently written report based on information from the original source.</em></p>
"""


@retry(
    stop=stop_after_attempt(MAX_RETRY_ATTEMPTS),
    wait=wait_exponential(min=2, max=15),
    reraise=True,
)
def _call_openai(client: OpenAI, messages: list[dict]) -> str:
    response = client.chat.completions.create(
        model=OPENAI_MODEL,
        messages=messages,
        temperature=OPENAI_TEMP,
        max_tokens=OPENAI_MAX_TOKENS,
        response_format={"type": "json_object"},
    )
    return response.choices[0].message.content


def rewrite_article(raw: dict) -> Optional[dict]:
    """
    Take a raw scraped article dict and return a fully structured article dict,
    or None if the pipeline fails.
    """
    content = (raw.get("content") or raw.get("excerpt") or "").strip()
    if len(content.split()) < 30:
        log.warning("Skipping '%s' — source content too short (%d words)",
                    raw.get("title", "?"), len(content.split()))
        return None

    title   = raw.get("title", "")
    url     = raw.get("url", "")
    source  = raw.get("source", "Unknown")

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            "content": USER_PROMPT_TEMPLATE.format(
                title=title,
                url=url,
                source=source,
                content=content[:4000],   # truncate to stay within token budget
            ),
        },
    ]

    try:
        client = _client()
        raw_json = _call_openai(client, messages)
        data = json.loads(raw_json)
    except Exception as exc:
        log.error("OpenAI call failed for '%s': %s", title, exc, exc_info=True)
        return None

    # Validate required fields
    required = ["title", "excerpt", "description", "body", "tags", "category"]
    for field in required:
        if field not in data:
            log.warning("AI response missing field '%s' for '%s'", field, title)
            return None

    # Sanitise category
    category = data.get("category", "National")
    if category not in CATEGORIES:
        category = infer_category(data["title"], data.get("body", ""), raw.get("category_hint"))

    # Build slug
    slug = make_slug(data["title"])
    if not slug:
        slug = hashlib.md5(url.encode()).hexdigest()[:16]

    # Pick images
    hero_image  = pick_image(category, raw.get("image"))
    thumb_image = pick_image_thumb(category, raw.get("image"))

    # Reading time (from body text stripped of HTML tags)
    body_text = re.sub(r"<[^>]+>", " ", data.get("body", ""))
    reading_time = estimate_reading_time(body_text)

    # Author
    author = random.choice(AUTHORS)

    # Timestamp (Morocco time)
    now = datetime.now(tz=MOROCCO_TZ)

    safe_body = sanitise_body_html(data["body"].strip())

    article = {
        "slug":          slug,
        "title":         data["title"].strip()[:120],
        "excerpt":       data["excerpt"].strip()[:300],
        "description":   data["description"].strip()[:160],
        "body":          safe_body,
        "category":      category,
        "tags":          [t.lower().strip()[:40] for t in data.get("tags", [])[:8]],
        "is_breaking":   bool(data.get("is_breaking", False)),
        "author":        author,
        "reading_time":  reading_time,
        "hero_image":    hero_image,
        "thumb_image":   thumb_image,
        "published_at":  now.isoformat(),
        "date_display":  now.strftime("%B %-d, %Y"),
        "sources": [
            {
                "name": source,
                "url":  url,
                "original_title": title,
            }
        ],
        # Internal tracking
        "_source_url": url,
    }

    log.info("✓ Generated: [%s] %s", category, article["title"])
    return article


def rewrite_from_headline(headline: str) -> Optional[dict]:
    """
    Generate an article from just a headline/topic string (for manual publish mode).
    The AI generates the article from background knowledge (Morocco/Marrakech context).
    """
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            "content": f"""\
Write an original English news article for Marrakech Daily based on this topic/headline:

"{headline}"

Use your knowledge of Morocco, Marrakech and the region to write a plausible,
factual-sounding article. If the topic is very specific and you don't have
confirmed facts, note that in the article ("according to local reports",
"as reported by local media", etc.).

Return ONLY a valid JSON object with these exact fields:
{{
  "title":        "<SEO English headline, max 90 chars>",
  "excerpt":      "<2-sentence teaser, 30-50 words>",
  "description":  "<SEO meta description, 130-155 chars>",
  "body":         "<Full article in HTML <p> tags, 4-7 paragraphs, 350-500 words>",
  "tags":         ["<tag1>", "<tag2>", "<tag3>", "<tag4>", "<tag5>"],
  "category":     "<one of: Breaking | National | Business | Sport | Culture | Tourism | Society | Technology | Health | International>",
  "is_breaking":  <true or false>
}}

End the body with:
<p><em>This is an original report by Marrakech Daily editorial staff.</em></p>
""",
        },
    ]

    try:
        client = _client()
        raw_json = _call_openai(client, messages)
        data = json.loads(raw_json)
    except Exception as exc:
        log.error("OpenAI call failed for headline '%s': %s", headline, exc, exc_info=True)
        return None

    category = data.get("category", "National")
    if category not in CATEGORIES:
        category = "National"

    slug = make_slug(data["title"])
    hero_image  = pick_image(category)
    thumb_image = pick_image_thumb(category)
    body_text   = re.sub(r"<[^>]+>", " ", data.get("body", ""))
    now         = datetime.now(tz=MOROCCO_TZ)

    safe_body = sanitise_body_html(data["body"].strip())

    return {
        "slug":          slug,
        "title":         data["title"].strip()[:120],
        "excerpt":       data["excerpt"].strip()[:300],
        "description":   data["description"].strip()[:160],
        "body":          safe_body,
        "category":      category,
        "tags":          [t.lower().strip()[:40] for t in data.get("tags", [])[:8]],
        "is_breaking":   bool(data.get("is_breaking", False)),
        "author":        random.choice(AUTHORS),
        "reading_time":  estimate_reading_time(re.sub(r"<[^>]+>", " ", safe_body)),
        "hero_image":    hero_image,
        "thumb_image":   thumb_image,
        "published_at":  now.isoformat(),
        "date_display":  now.strftime("%B %-d, %Y"),
        "sources":       [{"name": "Marrakech Daily", "url": "", "original_title": headline}],
        "_source_url":   "",
    }
