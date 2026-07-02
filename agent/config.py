"""
Marrakech Daily — AI Agent Configuration
"""

import os

# ── SOURCES ──────────────────────────────────────────────────────────────────
SOURCES = [
    {
        "name": "Kech24",
        "url": "https://fr.kech24.com/",
        "lang": "fr",
        "weight": 10,          # max articles to attempt per run
        "selectors": {
            "article_links": "a[href]",
            "title": "h1",
            "body": "article, .entry-content, .post-content, .article-content",
        },
    },
    {
        "name": "MadeInCity",
        "url": "https://www.madein.city/marrakech/fr/stories/",
        "lang": "fr",
        "weight": 7,
        "selectors": {
            "article_links": "a[href]",
            "title": "h1",
            "body": "article, .story-content, .content",
        },
    },
    {
        "name": "AlphaBourse",
        "url": "https://alphabourse.ma/",
        "lang": "fr",
        "weight": 5,
        "selectors": {
            "article_links": "a[href]",
            "title": "h1",
            "body": "article, .article-body, .entry-content",
        },
    },
]

# ── TARGETS ──────────────────────────────────────────────────────────────────
ARTICLES_PER_RUN   = 20       # target articles published per daily run
MAX_ATTEMPTS       = 40       # scrape up to N links before stopping
MIN_CONTENT_WORDS  = 60       # skip articles with fewer words in source
MAX_CONTENT_WORDS  = 8000     # truncate source before sending to AI

# ── AI ───────────────────────────────────────────────────────────────────────
AI_MODEL        = "claude-sonnet-4-6"
AI_MAX_TOKENS   = 1800
ANTHROPIC_KEY   = os.environ.get("ANTHROPIC_API_KEY", "")

# ── CATEGORIES ───────────────────────────────────────────────────────────────
CATEGORIES = [
    "breaking-news",
    "business",
    "tourism",
    "real-estate",
    "culture",
    "events",
    "lifestyle",
    "sport",
    "national",
    "international",
]

# ── PATHS ────────────────────────────────────────────────────────────────────
ROOT_DIR         = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ARTICLES_DIR     = os.path.join(ROOT_DIR, "articles")
PUBLISHED_LOG    = os.path.join(ROOT_DIR, "articles", "published.json")
INDEX_HTML       = os.path.join(ROOT_DIR, "index.html")
LOG_DIR          = os.path.join(ROOT_DIR, "logs")

# ── RETRY ────────────────────────────────────────────────────────────────────
HTTP_TIMEOUT     = 15
HTTP_RETRIES     = 3
HTTP_BACKOFF     = 2          # seconds between retries
AI_RETRIES       = 2

# ── SITE META ────────────────────────────────────────────────────────────────
SITE_NAME        = "Marrakech Daily"
SITE_URL         = "https://imadazhar.github.io/marrakech-daily/"
SITE_TAGLINE     = "Your English-Language Window to the Red City"
TIMEZONE         = "Africa/Casablanca"   # Morocco timezone (GMT / GMT+1 summer)
