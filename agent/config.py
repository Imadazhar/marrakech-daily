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

# Create directories if they don't exist
DATA_DIR.mkdir(parents=True, exist_ok=True)
LOGS_DIR.mkdir(parents=True, exist_ok=True)

# ── News sources ──────────────────────────────────────────────────────────────
NEWS_SOURCES = [
    {
        "name": "Kech24",
        "id": "kech24",
        "base_url": "https://fr.kech24.com",
        "listing_url": "https://fr.kech24.com/category/actualites/marrakech/",
        "language": "fr",
        "scraper": "kech24",
    },
    {
        "name": "Kech24 National",
        "id": "kech24_national",
        "base_url": "https://fr.kech24.com",
        "listing_url": "https://fr.kech24.com/category/actualites/maroc/",
        "language": "fr",
        "scraper": "kech24",
    },
    {
        "name": "Made In City Marrakech",
        "id": "madein_city",
        "base_url": "https://www.madein.city",
        "listing_url": "https://www.madein.city/marrakech/fr/stories",
        "language": "fr",
        "scraper": "madein_city",
    },
    {
        "name": "Alphabourse",
        "id": "alphabourse",
        "base_url": "https://alphabourse.ma",
        "listing_url": "https://alphabourse.ma/fr/marches",
        "language": "fr",
        "scraper": "alphabourse",
    },
]

# ── Publishing limits ─────────────────────────────────────────────────────────
MAX_ARTICLES_PER_RUN   = 20
MAX_PER_SOURCE         = 8          # cap per source to keep diversity
MIN_SOURCE_TEXT_WORDS  = 60         # skip if extracted content is too short

# ── OpenAI settings ───────────────────────────────────────────────────────────
OPENAI_API_KEY  = os.environ.get("OPENAI_API_KEY", "")
OPENAI_MODEL    = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
OPENAI_TEMP     = 0.65
OPENAI_MAX_TOKENS = 2200

# ── Site metadata ─────────────────────────────────────────────────────────────
SITE_TITLE       = "Marrakech Daily"
SITE_TAGLINE     = "Morocco's English-Language Newspaper"
SITE_DESCRIPTION = ("Independent English-language journalism covering Marrakech, "
                    "Morocco and the region — business, culture, tourism and breaking news.")
SITE_URL         = "https://imadazhar.github.io/marrakech-daily"
SITE_TWITTER     = "@MarrakechDaily"

# ── Article categories ────────────────────────────────────────────────────────
CATEGORIES = [
    "Breaking", "National", "Business", "Sport",
    "Culture", "Tourism", "Society", "Technology", "Health", "International",
]

CATEGORY_KEYWORDS = {
    "Breaking":      ["urgent", "breaking", "alert", "live", "just in"],
    "Sport":         ["sport", "football", "foot", "athletisme", "marathon", "copa", "mundial", "world cup", "fifa", "caf"],
    "Business":      ["bourse", "economie", "finance", "investissement", "marche", "pib", "croissance",
                      "entreprise", "emploi", "immobilier", "industrie", "export"],
    "Culture":       ["culture", "art", "festival", "musique", "cinema", "theatre", "patrimoine",
                      "musee", "artiste", "concert", "exposition"],
    "Tourism":       ["tourisme", "hotel", "riad", "restaurant", "voyageur", "visiteur", "gastronomie",
                      "sejour", "hebergement", "aeroport"],
    "Technology":    ["technologie", "numerique", "startup", "innovation", "ia", "intelligence artificielle",
                      "digital", "tech", "application"],
    "Health":        ["sante", "hopital", "medecin", "vaccin", "maladie", "clinique", "covid"],
    "National":      ["maroc", "gouvernement", "ministre", "roi", "parlement", "politique", "loi",
                      "election", "region", "province"],
    "International": ["international", "europe", "france", "espagne", "ue", "monde", "onu", "union"],
    "Society":       ["societe", "famille", "education", "jeunesse", "femme", "social", "logement",
                      "urbanisme", "environnement", "eau"],
}

# ── Author pool ───────────────────────────────────────────────────────────────
AUTHORS = [
    {"name": "Karim Benali",   "role": "Senior Reporter"},
    {"name": "Sofia Alaoui",   "role": "Business Editor"},
    {"name": "Hassan Tazi",    "role": "Culture Correspondent"},
    {"name": "Nadia Chraibi",  "role": "Sports Editor"},
    {"name": "Omar Fassi",     "role": "Staff Writer"},
    {"name": "Fatima Zahra",   "role": "Deputy Editor"},
    {"name": "Youssef Kadiri", "role": "Economics Reporter"},
    {"name": "Leila Berrada",  "role": "Tourism Correspondent"},
]

# ── Unsplash curated images per category ─────────────────────────────────────
# Free-to-use photos from Unsplash (no API key needed for direct URLs)
CATEGORY_IMAGES = {
    "Breaking":      [
        "photo-1504711434969-e33886168f5c",  # crowd
        "photo-1588681664899-f142ff2dc9b1",  # news
    ],
    "National":      [
        "photo-1539578703015-e8a5eb1c3c6d",  # Moroccan flag
        "photo-1528360983277-13d401cdc186",  # Marrakech medina
    ],
    "Business":      [
        "photo-1611974789855-9c2a0a7236a3",  # stocks
        "photo-1486406146926-c627a92ad1ab",  # business building
        "photo-1580519542036-c47de6196ba5",  # casablanca finance
    ],
    "Sport":         [
        "photo-1574629810360-7efbbe195018",  # football
        "photo-1560272564-c83b66b1ad12",     # Morocco fans
        "photo-1553778263-73a83bab9b0c",     # sport
    ],
    "Culture":       [
        "photo-1539020140153-e479b8b22e73",  # Marrakech art
        "photo-1489424731084-a5d8b219a5bb",  # festival lights
        "photo-1524492412937-b28074a5d7da",  # India/Marrakech vibe
    ],
    "Tourism":       [
        "photo-1518548419970-58e3b4079ab2",  # Marrakech palm
        "photo-1489392191049-fc10c97e64b6",  # Marrakech riad pool
        "photo-1548018560-c7196548a87e",     # luxury hotel
    ],
    "Technology":    [
        "photo-1518770660439-4636190af475",  # tech
        "photo-1531297484001-80022131f5a1",  # laptop code
    ],
    "Health":        [
        "photo-1559757148-5c350d0d3c56",    # health
        "photo-1576671081837-49000212a370",  # medicine
    ],
    "International": [
        "photo-1529156069898-49953e39b3ac",  # world
        "photo-1451187580459-43490279c0fa",  # globe
    ],
    "Society":       [
        "photo-1491438590914-bc09fcaaf77a",  # people
        "photo-1573497620053-ea5300f94f21",  # community
    ],
}

DEFAULT_IMAGE_ID = "photo-1528360983277-13d401cdc186"  # Marrakech medina

# ── HTTP request settings ─────────────────────────────────────────────────────
REQUEST_TIMEOUT  = 20          # seconds
REQUEST_HEADERS  = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/125.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "fr-FR,fr;q=0.9,en;q=0.8",
}
MAX_RETRY_ATTEMPTS = 3
RETRY_WAIT_MIN     = 2    # seconds
RETRY_WAIT_MAX     = 10   # seconds

# ── Deduplication settings ────────────────────────────────────────────────────
SIMILARITY_THRESHOLD = 0.85   # cosine similarity above which we consider it a duplicate
MAX_HASH_HISTORY     = 5000   # maximum hashes to store
