"""Central configuration for the seasonal cookbook pipeline."""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "cookbook.db"
DUMP_DIR = BASE_DIR / "dumps"
LOG_DIR = BASE_DIR / "logs"     # per-run tee logs from spike.py / crawl.py

# --- Politeness -------------------------------------------------------------
# A real contact address is the single cheapest thing you can do to stay on the
# right side of a site operator who notices your traffic. Set it via the
# COOKBOOK_CONTACT environment variable so you never have to edit this tracked
# file (which would collide on every `git pull`):
#     Windows:  setx COOKBOOK_CONTACT "you@example.be"   (then reopen the shell)
#     bash:     export COOKBOOK_CONTACT="you@example.be"
_PLACEHOLDER = "you@example.be"
CONTACT = os.environ.get("COOKBOOK_CONTACT", _PLACEHOLDER)
CONTACT_IS_PLACEHOLDER = CONTACT == _PLACEHOLDER
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
        # /gerechten/zoeken is the search/listing page, not a recipe -- it
        # matched the pattern and was the lone parse_failed in the first crawl.
        "url_excludes": [r"/gerechten/zoeken"],
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

    # --- v2: incidentally-vegan winter crawl (docs/vegan_sources.md) ---------
    # The survey's three starters, chosen for BELGIAN WINTER coverage (witloof,
    # spruiten, boerenkool, pastinaak, knolselderij...) rather than vegan
    # volume. English-language, so no new language layer -- but the produce
    # lexicon still needs the transliterated-Hindi / romanised-Korean+Japanese
    # ALIAS PASS, and `recipes` needs a `cuisine` COLUMN, before any crawl.
    # Both prerequisites are listed in CLAUDE.md; adding the entries here does
    # not crawl -- crawl.py / spike.py are the only things that touch the net.
    #
    # url_patterns below are UNVERIFIED GUESSES (these are WordPress food blogs
    # with recipe posts at the site root). Tighten each from the real sitemap
    # prefixes -- run `py check_source.py <a recipe url>` and `crawl.py
    # --list-only --source <name>` first, exactly as for the v1 sources.
    "vegrecipesofindia": {
        "base_url": "https://www.vegrecipesofindia.com",
        "lang": "en",
        "url_patterns": [r"/[^/]+/?$"],   # GUESS: root-slug posts
        "parser": "recipe_scrapers",      # native scraper (per survey)
    },
    "redhousespice": {
        "base_url": "https://redhousespice.com",
        "lang": "en",
        "url_patterns": [r"/[^/]+/?$"],   # GUESS: root-slug posts
        "parser": "recipe_scrapers",      # native scraper, Northern Chinese
    },
    "miakouppa": {
        "base_url": "https://www.miakouppa.com",
        "lang": "en",
        "url_patterns": [r"/[^/]+/?$"],   # GUESS: root-slug posts
        "parser": "wild",                 # no native scraper -> wild_mode/JSON-LD
    },
    "plantyou": {
        "base_url": "https://plantyou.com",
        "lang": "en",
        # Recipes are root-slug posts (/easy-vegan-banana-bread/). Anchor to the
        # domain so ONLY single-segment paths match -- this structurally drops
        # the /category/, /tag/, /author/ and /page/N listing pages the old
        # catch-all `/[^/]+/?$` swept in via .search() (they were the bulk of
        # the parse_failed in the first crawl). Root-level editorial posts
        # (travel, listicles) still match but are harmlessly rejected by the
        # wild route -- no recipe JSON-LD, so they never reach the corpus.
        "url_patterns": [r"^https?://[^/]+/[^/]+/?$"],
        "parser": "wild",                 # no native scraper -> wild_mode/JSON-LD
    },
}

# Spike sample sizes: small on purpose. The point is to learn, not to harvest.
SPIKE_SAMPLE = {"15gram": 20, "dagelijksekost": 5, "delhaize": 5}

# --- Planner / household ----------------------------------------------------
WEEK_SIZE = 7                # dinners per planned week

# Household to scale recipe servings to: 2 adults + 2 kids, a kid counting as
# KID_PORTION of an adult serving. Configurable -- the UI will expose it.
HOUSEHOLD_ADULTS = 2
HOUSEHOLD_KIDS = 2
KID_PORTION = 0.5           # kid = half an adult serving -> 3.0 adult-equivalents


def household_servings() -> float:
    """Adult-equivalent servings a recipe should scale to."""
    return HOUSEHOLD_ADULTS + HOUSEHOLD_KIDS * KID_PORTION
