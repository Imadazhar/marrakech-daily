"""
Marrakech Daily — AI Writing Pipeline (Groq)
Produces 100% original English journalism from source material.
"""
import json
import logging
import re
import time
from datetime import datetime

from groq import Groq

from config import (
    GROQ_API_KEY, GROQ_MODEL, GROQ_FALLBACK,
    AI_RETRIES, AI_DELAY, CATEGORIES, SITE_NAME, AUTHOR_DEFAULT,
)

logger = logging.getLogger("writer")
client = Groq(api_key=GROQ_API_KEY)

# ── PROMPTS ───────────────────────────────────────────────────────────────────

SYSTEM = f"""\
You are the Editor-in-Chief of {SITE_NAME}, a professional English-language \
news website covering Marrakech and Morocco. Your readers are expats, tourists, \
investors and international business people.

MISSION: Write 100% original English journalism. NEVER translate. NEVER copy. \
Extract facts → verify they make sense → rewrite entirely in your own voice.

STYLE: American newspaper style. Clear, factual, engaging. No fluff.
ATTRIBUTION: Always note which outlet originally reported the story.
ACCURACY: Only state facts present in the source. Never invent.

OUTPUT FORMAT: Return ONLY valid JSON. No markdown. No explanation. No code fences.\
"""

ARTICLE_PROMPT = """\
SOURCE MATERIAL ({lang}):
HEADLINE: {raw_title}
BODY:
{raw_body}

Original URL: {url}
Source outlet: {source_name}
Today's date: {today}

Write a completely original English news article based only on the facts above.
Return this exact JSON (no extra keys):
{{
  "title": "Compelling SEO headline, max 85 chars",
  "slug": "lowercase-url-slug-max-70-chars",
  "excerpt": "2 sentences, max 180 chars, for homepage card",
  "seo_description": "Google meta description, max 155 chars",
  "category": "pick one: {categories}",
  "tags": ["tag1","tag2","tag3","tag4","tag5"],
  "reading_time": 3,
  "is_breaking": false,
  "image_query": "3 words for Unsplash photo search (no people, no text)",
  "body_html": "<p>Full article HTML. Min 350 words. Max 600 words. Use only p, h2, h3, strong, em tags. End with a source attribution paragraph.</p>"
}}"""

MANUAL_PROMPT = """\
Editor request: Write an original article about "{topic}" related to Marrakech/Morocco.
Today's date: {today}

Use realistic, plausible facts consistent with Morocco's current context.
Return this exact JSON:
{{
  "title": "Compelling SEO headline, max 85 chars",
  "slug": "lowercase-url-slug-max-70-chars",
  "excerpt": "2 sentences, max 180 chars",
  "seo_description": "Google meta description, max 155 chars",
  "category": "pick one: {categories}",
  "tags": ["tag1","tag2","tag3","tag4","tag5"],
  "reading_time": 3,
  "is_breaking": false,
  "image_query": "3 words for Unsplash photo search",
  "body_html": "<p>Full original article HTML. Min 400 words. Professional journalism.</p>"
}}"""


# ── HELPERS ───────────────────────────────────────────────────────────────────

def _slugify(text: str) -> str:
    s = text.lower().strip()
    s = re.sub(r"[^a-z0-9\s-]", "", s)
    s = re.sub(r"\s+", "-", s)
    s = re.sub(r"-+", "-", s).strip("-")
    return s[:70]


def _clean_json(raw: str) -> str:
    """Strip markdown fences if model accidentally adds them."""
    raw = raw.strip()
    raw = re.sub(r"^```(?:json)?\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw)
    # Extract first {...} block if there's preamble text
    m = re.search(r"\{.*\}", raw, re.DOTALL)
    return m.group(0) if m else raw


def _validate(data: dict, source_url: str, source_name: str, today: str) -> dict:
    """Ensure all required fields exist and are valid."""
    if not data.get("slug"):
        data["slug"] = _slugify(data.get("title", f"article-{today}"))

    if data.get("category") not in CATEGORIES:
        data["category"] = "national"

    if not isinstance(data.get("tags"), list) or not data["tags"]:
        data["tags"] = ["Marrakech", "Morocco"]

    try:
        data["reading_time"] = max(1, int(data.get("reading_time", 3)))
    except (TypeError, ValueError):
        data["reading_time"] = 3

    data["is_breaking"]    = bool(data.get("is_breaking", False))
    data["published_at"]   = today
    data["source_url"]     = source_url
    data["source_name"]    = source_name
    data["author"]         = AUTHOR_DEFAULT

    # Ensure attribution is in body
    if data.get("body_html") and "source" not in data["body_html"].lower():
        data["body_html"] += (
            f'\n<p class="source-credit"><em>Reporting based on information '
            f'originally published by <a href="{source_url}" target="_blank" '
            f'rel="noopener noreferrer">{source_name}</a>.</em></p>'
        )

    return data


def _call_ai(prompt: str, model: str = GROQ_MODEL) -> dict:
    """Call Groq with retry + fallback model."""
    last_exc = None
    for attempt in range(1, AI_RETRIES + 1):
        try:
            resp = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": SYSTEM},
                    {"role": "user",   "content": prompt},
                ],
                max_tokens=1800,
                temperature=0.65,
            )
            raw = resp.choices[0].message.content or ""
            cleaned = _clean_json(raw)
            return json.loads(cleaned)

        except json.JSONDecodeError as exc:
            logger.warning(f"JSON parse error (attempt {attempt}): {exc}")
            logger.debug(f"Raw response: {raw[:300]}")
            last_exc = exc

        except Exception as exc:
            logger.warning(f"AI error (attempt {attempt}): {exc}")
            last_exc = exc
            # Try fallback model on second attempt
            if attempt == 2 and model != GROQ_FALLBACK:
                model = GROQ_FALLBACK
                logger.info(f"Switching to fallback model: {GROQ_FALLBACK}")

        if attempt < AI_RETRIES:
            time.sleep(AI_DELAY * attempt)

    raise RuntimeError(f"AI writing failed after {AI_RETRIES} retries: {last_exc}")


# ── PUBLIC API ────────────────────────────────────────────────────────────────

def write_from_source(raw: dict) -> dict:
    """Convert scraped raw article into published-ready dict."""
    today = datetime.now().strftime("%B %d, %Y")
    prompt = ARTICLE_PROMPT.format(
        lang=raw.get("source_lang", "fr").upper(),
        raw_title=raw["raw_title"],
        raw_body=raw["raw_body"],
        url=raw["url"],
        source_name=raw["source_name"],
        today=today,
        categories=", ".join(CATEGORIES),
    )
    data = _call_ai(prompt)
    return _validate(data, raw["url"], raw["source_name"], today)


def write_manual(topic: str) -> dict:
    """Generate article from a manual topic prompt."""
    today = datetime.now().strftime("%B %d, %Y")
    prompt = MANUAL_PROMPT.format(
        topic=topic,
        today=today,
        categories=", ".join(CATEGORIES),
    )
    data = _call_ai(prompt)
    return _validate(data, SITE_NAME, "Editorial Team", today)
