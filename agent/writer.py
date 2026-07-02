"""
Marrakech Daily — AI Writing Pipeline
Transforms raw scraped content into original English articles.
"""

import json
import logging
import re
import time
from datetime import datetime

import anthropic

from config import AI_MODEL, AI_MAX_TOKENS, ANTHROPIC_KEY, AI_RETRIES, CATEGORIES, SITE_NAME

logger = logging.getLogger(__name__)

client = anthropic.Anthropic(api_key=ANTHROPIC_KEY)

SYSTEM_PROMPT = f"""You are the senior editor of {SITE_NAME}, an independent English-language news website covering Marrakech and Morocco. Your readers are expats, tourists, investors and international business people.

YOUR TASK: Given raw French-language source material, write a completely ORIGINAL English article. Do NOT translate. Do NOT copy sentences. Extract the key facts and rewrite everything in your own authoritative journalistic voice.

RULES:
- Extract factual information only (names, numbers, dates, places, events).
- Write fresh, original prose — zero copied sentences from the source.
- British/American neutral English, professional tone.
- Include specific Marrakech/Morocco context where relevant.
- Be concise and informative. No fluff, no filler.
- Always attribute facts to the original source (e.g. "according to kech24.com").

OUTPUT: Return ONLY valid JSON, no markdown fences, no explanation."""

ARTICLE_PROMPT = """Source material (French):
TITLE: {raw_title}
CONTENT: {raw_body}

Source URL: {source_url}
Source name: {source_name}
Today's date: {today}

Write an original English article based on the above. Return this exact JSON structure:
{{
  "title": "SEO-optimized English headline (max 90 chars, compelling)",
  "slug": "url-friendly-slug-from-title",
  "excerpt": "2–3 sentence summary for the homepage card (max 200 chars)",
  "seo_description": "Meta description for Google (max 155 chars)",
  "category": "one of: {categories}",
  "tags": ["tag1", "tag2", "tag3", "tag4", "tag5"],
  "reading_time": 3,
  "body_html": "<p>Full article HTML using only <p>, <h2>, <h3>, <strong>, <em> tags. Minimum 350 words. Maximum 600 words.</p>",
  "image_query": "3-word Unsplash search query for a relevant photo (no people, no text)",
  "is_breaking": false
}}"""

MANUAL_PROMPT = """Topic requested by editor: "{topic}"
Today's date: {today}

Research and write a plausible, factual-sounding original English article about this Marrakech/Morocco topic.
Use realistic details consistent with the current Moroccan context.
Return this exact JSON structure:
{{
  "title": "SEO-optimized English headline (max 90 chars)",
  "slug": "url-friendly-slug",
  "excerpt": "2–3 sentence summary (max 200 chars)",
  "seo_description": "Meta description (max 155 chars)",
  "category": "one of: {categories}",
  "tags": ["tag1", "tag2", "tag3", "tag4", "tag5"],
  "reading_time": 3,
  "body_html": "<p>Full article HTML minimum 400 words.</p>",
  "image_query": "3-word Unsplash search query",
  "is_breaking": false
}}"""


def _call_ai(prompt: str, retries: int = AI_RETRIES) -> dict:
    """Call Claude API with retry logic. Returns parsed JSON dict."""
    for attempt in range(1, retries + 1):
        try:
            response = client.messages.create(
                model=AI_MODEL,
                max_tokens=AI_MAX_TOKENS,
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": prompt}],
            )
            raw_text = response.content[0].text.strip()

            # Strip accidental markdown fences
            raw_text = re.sub(r"^```(?:json)?\s*", "", raw_text)
            raw_text = re.sub(r"\s*```$", "", raw_text)

            return json.loads(raw_text)

        except json.JSONDecodeError as exc:
            logger.warning(f"AI JSON parse error (attempt {attempt}): {exc}")
        except anthropic.APIError as exc:
            logger.warning(f"AI API error (attempt {attempt}): {exc}")
        except Exception as exc:
            logger.warning(f"Unexpected AI error (attempt {attempt}): {exc}")

        if attempt < retries:
            time.sleep(3 * attempt)

    raise RuntimeError("AI writing failed after all retries")


def _slug_from_title(title: str) -> str:
    """Fallback slug generator."""
    slug = title.lower()
    slug = re.sub(r"[^a-z0-9\s-]", "", slug)
    slug = re.sub(r"\s+", "-", slug.strip())
    slug = re.sub(r"-+", "-", slug)
    return slug[:80]


def _validate_article(data: dict, source_url: str, source_name: str, today: str) -> dict:
    """Ensure all required fields are present and well-formed."""
    # Slug fallback
    if not data.get("slug"):
        data["slug"] = _slug_from_title(data.get("title", "article"))

    # Category fallback
    if data.get("category") not in CATEGORIES:
        data["category"] = "national"

    # Tags fallback
    if not isinstance(data.get("tags"), list) or not data["tags"]:
        data["tags"] = ["Morocco", "Marrakech"]

    # Reading time
    try:
        data["reading_time"] = max(1, int(data.get("reading_time", 3)))
    except (TypeError, ValueError):
        data["reading_time"] = 3

    # Boolean
    data["is_breaking"] = bool(data.get("is_breaking", False))

    # Inject metadata
    data["published_at"] = today
    data["source_url"]   = source_url
    data["source_name"]  = source_name

    # Ensure body has source attribution
    attribution = (
        f'<p class="article-source">Source: '
        f'<a href="{source_url}" target="_blank" rel="noopener">{source_name}</a> '
        f'— Original reporting in French. This article was independently written in English.</p>'
    )
    if "body_html" in data and attribution not in data["body_html"]:
        data["body_html"] += "\n" + attribution

    return data


def write_from_source(raw: dict) -> dict:
    """Convert a scraped raw article into a published-ready article dict."""
    today = datetime.now().strftime("%B %d, %Y")
    prompt = ARTICLE_PROMPT.format(
        raw_title=raw["raw_title"],
        raw_body=raw["raw_body"][:4000],   # cap to avoid huge prompts
        source_url=raw["url"],
        source_name=raw["source_name"],
        today=today,
        categories=", ".join(CATEGORIES),
    )
    data = _call_ai(prompt)
    return _validate_article(data, raw["url"], raw["source_name"], today)


def write_manual(topic: str) -> dict:
    """Generate an article from a manual topic string."""
    today = datetime.now().strftime("%B %d, %Y")
    prompt = MANUAL_PROMPT.format(
        topic=topic,
        today=today,
        categories=", ".join(CATEGORIES),
    )
    data = _call_ai(prompt)
    return _validate_article(data, SITE_NAME, "Editor Submission", today)
