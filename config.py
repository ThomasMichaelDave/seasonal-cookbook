"""Central configuration for the seasonal cookbook pipeline."""
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "cookbook.db"
DUMP_DIR = BASE_DIR / "dumps"

# --- Politeness -------------------------------------------------------------
# Put a real contact address here. It is the single cheapest thing you can do
# to stay on the right side of a site operator who notices your traffic.
CONTACT = "you@example.be"
USER_AGENT = f"SeasonalCookbookBot/0.1 (personal, non-commercial; {CONTACT})"

REQUEST_DELAY = 1.5      # seconds between requests to the SAME domain
JITTER = 0.6             # random extra delay, 0..JITTER
TIMEOUT = 30
MAX_RETRIES = 3
BACKOFF_BASE = 2.0       # seconds; doubled each retry

# --- Sources ----------------------------------------------------------------
# url_patterns: regexes a sitemap URL must match to be treated as a recipe.
# They are deliberately loose for the spike. Step 1 of spike.py reports the
# most common path prefixes it actually finds, so you tighten these from
# evidence rather than from guesswork.
SOURCES = {
    "15gram": {
        "base_url": "https://15gram.be",
        "lang": "nl",
        "url_patterns": [r"/recepten?/"],
        "parser": "recipe_scrapers",      # native scraper: FifteenGram
    },
    "dagelijksekost": {
        "base_url": "https://dagelijksekost.vrt.be",
        "lang": "nl",
        "url_patterns": [r"/gerechten/", r"/recept"],
        "parser": "recipe_scrapers",      # native scraper: DagelijkseKost
    },
    "delhaize": {
        "base_url": "https://www.delhaize.be",
        "lang": "nl",
        # Delhaize serves NL and FR; keep to NL for v1 so the lexicon stays
        # single-language. Add /fr/recettes/ later if you want the FR half.
        "url_patterns": [r"/nl/recept", r"/nl/inspiratie/recept"],
        "parser": "wild",                 # no native scraper -> wild_mode/JSON-LD
        # robots.txt disallows */search/* and */search?* -- never enqueue those
        "url_excludes": [r"/search"],
    },
}

# Spike sample sizes: small on purpose. The point is to learn, not to harvest.
SPIKE_SAMPLE = {"15gram": 20, "dagelijksekost": 5, "delhaize": 5}
