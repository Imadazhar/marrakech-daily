"""
Marrakech Daily — Agent Configuration
All settings in one place. No hard-coded secrets.
"""
import os

# ── API ───────────────────────────────────────────────────────────────────────
GROQ_API_KEY   = os.environ.get("GROQ_API_KEY", "")
GROQ_MODEL     = "llama-3.3-70b-versatile"   # fast, high quality
GROQ_FALLBACK  = "llama3-8b-8192"            # smaller fallback if rate-limited

# ── PATHS ─────────────────────────────────────────────────────────────────────
ROOT_DIR      = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AGENT_DIR     = os.path.join(ROOT_DIR, "agent")
ARTICLES_DIR  = os.path.join(ROOT_DIR, "articles")
LOGS_DIR      = os.path.join(ROOT_DIR, "logs")
INDEX_HTML    = os.path.join(ROOT_DIR, "index.html")
PUBLISHED_DB  = os.path.join(ROOT_DIR, "articles", "published.json")
SITEMAP_XML   = os.path.join(ROOT_DIR, "sitemap.xml")
RSS_XML       = os.path.join(ROOT_DIR, "feed.xml")

# ── SITE ──────────────────────────────────────────────────────────────────────
SITE_NAME     = "Marrakech Daily"
SITE_URL      = "https://imadazhar.github.io/marrakech-daily"
SITE_TAGLINE  = "Your English-Language Window to the Red City"
SITE_LANG     = "en"
SITE_LOCALE   = "en_US"
AUTHOR_DEFAULT = "Marrakech Daily Staff"

# ── SCRAPING ──────────────────────────────────────────────────────────────────
HTTP_TIMEOUT  = 20
HTTP_RETRIES  = 3
CRAWL_DELAY   = 1.2   # seconds between requests (be polite)
MIN_WORDS     = 50    # skip articles with less than this many words in source

# ── PUBLISHING ────────────────────────────────────────────────────────────────
ARTICLES_PER_RUN   = 30
MAX_PER_SOURCE     = 12   # safety cap per source
AI_RETRIES         = 3
AI_DELAY           = 1.5  # seconds between AI calls

# ── SOURCES (in priority order) ───────────────────────────────────────────────
SOURCES = [
    # Primary — Local Marrakech news
    {
        "id": "kech24",
        "name": "Kech24",
        "url": "https://fr.kech24.com/",
        "lang": "fr",
        "quota": 10,
        "category_hint": "breaking-news",
        "link_pattern": r"kech24\.com/[a-z0-9\-]+/$",
        "rss": "https://fr.kech24.com/feed/",
    },
    # Lifestyle & events
    {
        "id": "madein",
        "name": "MadeInCity Marrakech",
        "url": "https://www.madein.city/marrakech/fr/stories/",
        "lang": "fr",
        "quota": 5,
        "category_hint": "lifestyle",
        "link_pattern": r"madein\.city/marrakech/fr/stories/[a-z0-9\-]+",
        "rss": None,
    },
    # Finance & economy
    {
        "id": "alphabourse",
        "name": "AlphaBourse",
        "url": "https://alphabourse.ma/",
        "lang": "fr",
        "quota": 3,
        "category_hint": "business",
        "link_pattern": r"alphabourse\.ma/[a-z0-9\-/]+",
        "rss": None,
    },
    # Government / tourism
    {
        "id": "visitmorocco",
        "name": "Visit Morocco",
        "url": "https://www.visitmorocco.com/en/news",
        "lang": "en",
        "quota": 3,
        "category_hint": "tourism",
        "link_pattern": r"visitmorocco\.com/en/",
        "rss": None,
    },
    # International
    {
        "id": "reuters_morocco",
        "name": "Reuters",
        "url": "https://www.reuters.com/search/news?blob=morocco&sortBy=date",
        "lang": "en",
        "quota": 3,
        "category_hint": "national",
        "link_pattern": r"reuters\.com/",
        "rss": "https://feeds.reuters.com/reuters/topNews",
    },
    # Sports
    {
        "id": "caf",
        "name": "CAF Online",
        "url": "https://www.cafonline.com/news/",
        "lang": "en",
        "quota": 2,
        "category_hint": "sport",
        "link_pattern": r"cafonline\.com/news/",
        "rss": None,
    },
    # Tourism
    {
        "id": "lonelyplanet",
        "name": "Lonely Planet",
        "url": "https://www.lonelyplanet.com/articles?destination=morocco",
        "lang": "en",
        "quota": 2,
        "category_hint": "tourism",
        "link_pattern": r"lonelyplanet\.com/articles/",
        "rss": None,
    },
]

# ── CATEGORIES ────────────────────────────────────────────────────────────────
CATEGORIES = [
    "breaking-news",
    "business",
    "economy",
    "tourism",
    "lifestyle",
    "technology",
    "science",
    "culture",
    "food",
    "sport",
    "travel",
    "opinion",
    "national",
    "international",
]

# ── UNSPLASH (free, no key needed for source.unsplash.com) ───────────────────
UNSPLASH_BASE = "https://source.unsplash.com/1200x630"
