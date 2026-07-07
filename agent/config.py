"""Configuration for the Marrakech Daily AI Editorial Agent."""

import os
from pathlib import Path

# ── Directory layout ──────────────────────────────────────────────────────────
ROOT_DIR      = Path(__file__).parent.parent
DATA_DIR      = ROOT_DIR / "_data"
ARTICLES_FILE = DATA_DIR / "articles.json"
HASHES_FILE   = DATA_DIR / "published_hashes.json"
TEMPLATES_DIR = ROOT_DIR / "templates"
LOGS_DIR      = ROOT_DIR / "agent" / "logs"

DATA_DIR.mkdir(parents=True, exist_ok=True)
LOGS_DIR.mkdir(parents=True, exist_ok=True)

# ── Site metadata ─────────────────────────────────────────────────────────────
SITE_TITLE       = "Marrakech Daily"
SITE_TAGLINE     = "Your English-Language Window to the Red City"
SITE_DESCRIPTION = (
    "Breaking news, business, tourism, sport, culture and lifestyle "
    "from Marrakech and Morocco. Independent English journalism for "
    "expats, tourists, investors and international businesses."
)
SITE_URL         = "https://imadazhar.github.io/marrakech-daily"
SITE_TWITTER     = "@MarrakechDaily"

# ── News sources (updated per editorial brief) ────────────────────────────────
NEWS_SOURCES = [
    # ── PRIMARY: Marrakech local news (8 articles/day) ──────────────────────
    {
        "name": "Kech24",
        "id": "kech24",
        "base_url": "https://fr.kech24.com",
        "listing_url": "https://fr.kech24.com/",
        "language": "fr",
        "scraper": "kech24",
        "daily_quota": 5,
        "category_hint": "National",
    },
    {
        "name": "Kech24 Marrakech",
        "id": "kech24_marrakech",
        "base_url": "https://fr.kech24.com",
        "listing_url": "https://fr.kech24.com/category/actualites/marrakech/",
        "language": "fr",
        "scraper": "kech24",
        "daily_quota": 3,
        "category_hint": "Breaking",
    },
    # ── LIFESTYLE: Restaurants, hotels, events (5 articles/day) ─────────────
    {
        "name": "Made In City Marrakech",
        "id": "madein_city",
        "base_url": "https://www.madein.city",
        "listing_url": "https://www.madein.city/marrakech/fr/stories",
        "language": "fr",
        "scraper": "madein_city",
        "daily_quota": 5,
        "category_hint": "Tourism",
    },
    # ── BUSINESS / FINANCE (3 articles/day) ──────────────────────────────────
    {
        "name": "AlphaBourse",
        "id": "alphabourse",
        "base_url": "https://alphabourse.ma",
        "listing_url": "https://alphabourse.ma/",
        "language": "fr",
        "scraper": "alphabourse",
        "daily_quota": 3,
        "category_hint": "Business",
    },
    # ── GOVERNMENT / OFFICIAL SOURCES ────────────────────────────────────────
    {
        "name": "MAP Express",
        "id": "mapexpress",
        "base_url": "https://www.mapexpress.ma",
        "listing_url": "https://www.mapexpress.ma/actualite/",
        "language": "fr",
        "scraper": "generic",
        "daily_quota": 3,
        "category_hint": "National",
    },
    {
        "name": "Maroc.ma",
        "id": "marocma",
        "base_url": "https://www.maroc.ma",
        "listing_url": "https://www.maroc.ma/fr/actualites",
        "language": "fr",
        "scraper": "generic",
        "daily_quota": 2,
        "category_hint": "National",
    },
    {
        "name": "Visit Morocco",
        "id": "visitmorocco",
        "base_url": "https://www.visitmorocco.com",
        "listing_url": "https://www.visitmorocco.com/en/news",
        "language": "en",
        "scraper": "generic",
        "daily_quota": 2,
        "category_hint": "Tourism",
    },
    {
        "name": "ONDA Morocco",
        "id": "onda",
        "base_url": "https://www.onda.ma",
        "listing_url": "https://www.onda.ma/fr/media/actualites",
        "language": "fr",
        "scraper": "generic",
        "daily_quota": 2,
        "category_hint": "National",
    },
    # ── SPORTS ───────────────────────────────────────────────────────────────
    {
        "name": "Le Matin Sport",
        "id": "lematin_sport",
        "base_url": "https://lematin.ma",
        "listing_url": "https://lematin.ma/journal/sport/",
        "language": "fr",
        "scraper": "generic",
        "daily_quota": 3,
        "category_hint": "Sport",
    },
    # ── TECH / HEALTH ─────────────────────────────────────────────────────────
    {
        "name": "Hespress",
        "id": "hespress",
        "base_url": "https://www.hespress.com",
        "listing_url": "https://www.hespress.com/",
        "language": "fr",
        "scraper": "generic",
        "daily_quota": 3,
        "category_hint": "National",
    },
    # ── WORLD ─────────────────────────────────────────────────────────────────
    {
        "name": "Reuters Africa",
        "id": "reuters",
        "base_url": "https://www.reuters.com",
        "listing_url": "https://feeds.reuters.com/reuters/topNews",
        "language": "en",
        "scraper": "rss",
        "daily_quota": 2,
        "category_hint": "International",
    },
]

# ── Publishing targets ────────────────────────────────────────────────────────
MAX_ARTICLES_PER_RUN   = 30   # target per daily run
MAX_PER_SOURCE         = 8    # hard cap per source
MIN_SOURCE_TEXT_WORDS  = 60   # skip thin content

# ── AI provider (Groq → Gemini → OpenAI fallback) ────────────────────────────
GROQ_API_KEY   = os.environ.get("GROQ_API_KEY", "")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")

if GROQ_API_KEY:
    _AI_KEY         = GROQ_API_KEY
    OPENAI_MODEL    = os.environ.get("OPENAI_MODEL", "llama-3.3-70b-versatile")
    OPENAI_BASE_URL = "https://api.groq.com/openai/v1"
elif GEMINI_API_KEY:
    _AI_KEY         = GEMINI_API_KEY
    OPENAI_MODEL    = os.environ.get("OPENAI_MODEL", "gemini-2.0-flash")
    OPENAI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai/"
else:
    _AI_KEY         = OPENAI_API_KEY
    OPENAI_MODEL    = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
    OPENAI_BASE_URL = None

OPENAI_TEMP       = 0.65
OPENAI_MAX_TOKENS = 2200

# ── Categories ────────────────────────────────────────────────────────────────
CATEGORIES = [
    "Breaking",
    "National",
    "Business",
    "Sport",
    "Culture",
    "Tourism",
    "Society",
    "Tech",
    "Health",
    "World",
]

# ── Category keywords for auto-classification ─────────────────────────────────
CATEGORY_KEYWORDS = {
    "Breaking":    ["urgent", "breaking", "alerte", "flash", "just in", "developing"],
    "Business":    ["économie", "business", "investissement", "bourse", "finance",
                    "entreprise", "marché", "banque", "croissance", "pib", "emploi",
                    "investment", "economy", "market", "finance", "startup"],
    "Sport":       ["football", "sport", "fifa", "caf", "atlas lions", "botola",
                    "marathon", "tennis", "basketball", "équipe nationale",
                    "coupe du monde", "world cup", "ligue"],
    "Culture":     ["culture", "festival", "art", "musique", "cinéma", "théâtre",
                    "patrimoine", "exposition", "concert", "film", "musée",
                    "gnawa", "artiste", "musique", "caftan"],
    "Tourism":     ["tourisme", "hôtel", "riad", "voyage", "aéroport", "aviation",
                    "menara", "visiteurs", "tourism", "hotel", "restaurant",
                    "restaurant", "café", "luxury", "lifestyle"],
    "Society":     ["société", "social", "famille", "éducation", "femme", "jeunesse",
                    "solidarité", "association", "droits", "humanitarian"],
    "Tech":        ["technologie", "digital", "numérique", "intelligence artificielle",
                    "startup", "innovation", "tech", "ai", "data", "cyber"],
    "Health":      ["santé", "médecine", "hôpital", "maladie", "vaccin", "covid",
                    "health", "medical", "clinique", "médicament"],
    "World":       ["international", "monde", "mondial", "onu", "europe", "usa",
                    "afrique", "moyen-orient", "diplomatie", "global"],
    "National":    ["maroc", "marrakech", "rabat", "casablanca", "gouvernement",
                    "ministre", "roi", "parlement", "commune", "région",
                    "infrastructure", "projet", "travaux", "sécurité"],
}

# ── Author pool ───────────────────────────────────────────────────────────────
AUTHORS = [
    {"name": "Sarah Mitchell",  "role": "Senior Correspondent"},
    {"name": "Karim Benali",    "role": "Culture & Tourism Editor"},
    {"name": "Jessica Hart",    "role": "Lifestyle & Real Estate"},
    {"name": "Youssef Kadiri",  "role": "Economics Reporter"},
    {"name": "Sofia Alaoui",    "role": "Business Editor"},
    {"name": "Nadia Chraibi",   "role": "Sports Editor"},
    {"name": "Omar Fassi",      "role": "Staff Reporter"},
    {"name": "Leila Berrada",   "role": "Tourism Correspondent"},
    {"name": "Hassan Tazi",     "role": "National Affairs"},
    {"name": "Fatima Zahra",    "role": "Society Editor"},
]

# ── Unsplash images per category ──────────────────────────────────────────────
CATEGORY_IMAGES = {
    "Breaking":  ["photo-1504711434969-e33886168f5c","photo-1588681664899-f142ff2dc9b1"],
    "National":  ["photo-1539578703015-e8a5eb1c3c6d","photo-1528360983277-13d401cdc186",
                  "photo-1562564055-71e051d33c19"],
    "Business":  ["photo-1611974789855-9c2a0a7236a3","photo-1486406146926-c627a92ad1ab",
                  "photo-1580519542036-c47de6196ba5","photo-1551288049-bebda4e38f71"],
    "Sport":     ["photo-1574629810360-7efbbe195018","photo-1560272564-c83b66b1ad12",
                  "photo-1553778263-73a83bab9b0c","photo-1540747913346-19212a4b423f"],
    "Culture":   ["photo-1578662996442-48f60103fc96","photo-1489424731084-a5d8b219a5bb",
                  "photo-1533174072545-7a4b6ad7a6c3","photo-1507838153414-b4b713384a76"],
    "Tourism":   ["photo-1518548419970-58e3b4079ab2","photo-1489392191049-fc10c97e64b6",
                  "photo-1548018560-c7196548a87e","photo-1540541338537-1220059af4dc"],
    "Society":   ["photo-1491438590914-bc09fcaaf77a","photo-1573497620053-ea5300f94f21",
                  "photo-1529156069898-49953e39b3ac"],
    "Tech":      ["photo-1518770660439-4636190af475","photo-1531297484001-80022131f5a1",
                  "photo-1519389950473-47ba0277781c"],
    "Health":    ["photo-1559757148-5c350d0d3c56","photo-1576671081837-49000212a370",
                  "photo-1505751172876-fa1923c5c528"],
    "World":     ["photo-1529156069898-49953e39b3ac","photo-1451187580459-43490279c0fa",
                  "photo-1489392191049-fc10c97e64b6"],
}
DEFAULT_IMAGE_ID = "photo-1528360983277-13d401cdc186"

# ── HTTP settings ─────────────────────────────────────────────────────────────
REQUEST_TIMEOUT  = 20
REQUEST_HEADERS  = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/125.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "fr-FR,fr;q=0.9,en;q=0.8",
}
MAX_RETRY_ATTEMPTS   = 3
RETRY_WAIT_MIN       = 2
RETRY_WAIT_MAX       = 10
SIMILARITY_THRESHOLD = 0.85
MAX_HASH_HISTORY     = 5000
