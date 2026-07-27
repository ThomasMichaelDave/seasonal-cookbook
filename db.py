"""SQLite schema + connection.

Design notes that matter later:
  * pages.html is the raw cache. Parse from here, never from the network.
  * recipes.parser_version lets you re-parse only stale rows after you improve
    the ingredient parser.
  * recipe_ingredients.canonical_id is nullable and mostly NULL. Only the ~60
    Velt vegetables ever get one -- salt does not need an identity.
  * season scores are DERIVED, recomputed whenever the lexicon or Velt data
    changes. They are cached in recipe_season_score but never authoritative.
"""
import sqlite3
from config import DB_PATH

SCHEMA = """
PRAGMA journal_mode=WAL;

CREATE TABLE IF NOT EXISTS sources (
    id                INTEGER PRIMARY KEY,
    name              TEXT UNIQUE NOT NULL,
    base_url          TEXT NOT NULL,
    lang              TEXT NOT NULL,
    robots_checked_at TEXT
);

-- URL frontier: the crawl queue. status in
-- (new, fetched, failed, skipped_robots, skipped_pattern)
CREATE TABLE IF NOT EXISTS frontier (
    url           TEXT PRIMARY KEY,
    source_id     INTEGER NOT NULL REFERENCES sources(id),
    status        TEXT NOT NULL DEFAULT 'new',
    discovered_at TEXT NOT NULL,
    fetched_at    TEXT,
    http_status   INTEGER,
    attempts      INTEGER NOT NULL DEFAULT 0,
    note          TEXT
);
CREATE INDEX IF NOT EXISTS ix_frontier_status ON frontier(status, source_id);

-- Raw HTML cache. content_hash lets a later re-crawl re-parse only what changed.
CREATE TABLE IF NOT EXISTS pages (
    url          TEXT PRIMARY KEY REFERENCES frontier(url),
    fetched_at   TEXT NOT NULL,
    content_hash TEXT NOT NULL,
    html         TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS recipes (
    id             INTEGER PRIMARY KEY,
    url            TEXT UNIQUE NOT NULL REFERENCES pages(url),
    source_id      INTEGER NOT NULL REFERENCES sources(id),
    lang           TEXT,
    title          TEXT,
    servings       INTEGER,
    total_min      INTEGER,
    course         TEXT,
    diet           TEXT,      -- vegan | vegetarian | omnivore | uncertain
    diet_evidence  TEXT,      -- which terms triggered it, for auditing
    parsed_at      TEXT NOT NULL,
    parser         TEXT,      -- recipe_scrapers | wild | jsonld | nextdata
    parser_version TEXT
);

CREATE TABLE IF NOT EXISTS recipe_ingredients (
    id              INTEGER PRIMARY KEY,
    recipe_id       INTEGER NOT NULL REFERENCES recipes(id) ON DELETE CASCADE,
    position        INTEGER NOT NULL,
    raw_text        TEXT NOT NULL,
    qty             REAL,
    unit            TEXT,
    ingredient_text TEXT,
    prep_note       TEXT,
    canonical_id    INTEGER REFERENCES canonical(id),
    is_hero         INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS ix_ri_recipe ON recipe_ingredients(recipe_id);
CREATE INDEX IF NOT EXISTS ix_ri_canon  ON recipe_ingredients(canonical_id);

-- The ~60-80 things that actually have a season.
CREATE TABLE IF NOT EXISTS canonical (
    id      INTEGER PRIMARY KEY,
    name_nl TEXT UNIQUE NOT NULL,
    name_en TEXT,
    kind    TEXT NOT NULL      -- vegetable | fruit | herb
);

CREATE TABLE IF NOT EXISTS aliases (
    alias        TEXT NOT NULL,
    lang         TEXT NOT NULL,
    canonical_id INTEGER NOT NULL REFERENCES canonical(id),
    PRIMARY KEY (alias, lang)
);

-- Loaded from the Velt seizoenskalender via load_velt.py.
-- availability: 0 none | 1 limited | 2 normal | 3 peak
--   Velt is binary, so it only ever writes 3. Levels 1 and 2 are reserved
--   for a source with a real supply gradient (VLAM).
-- cultivation:  velt | field | greenhouse | storage
--   'velt' = listed by Velt, cultivation unspecified. The printed calendar
--   makes no field/greenhouse/storage distinction, so its rows must not
--   claim one. See docs/velt.md.
CREATE TABLE IF NOT EXISTS seasonality (
    canonical_id INTEGER NOT NULL REFERENCES canonical(id),
    month        INTEGER NOT NULL CHECK (month BETWEEN 1 AND 12),
    availability INTEGER NOT NULL,
    cultivation  TEXT NOT NULL,
    PRIMARY KEY (canonical_id, month, cultivation)
);

-- Derived. Safe to DELETE and recompute at any time.
CREATE TABLE IF NOT EXISTS recipe_season_score (
    recipe_id     INTEGER NOT NULL REFERENCES recipes(id) ON DELETE CASCADE,
    month         INTEGER NOT NULL,
    strictness    TEXT NOT NULL,   -- field | greenhouse | storage
    score         REAL NOT NULL,
    hero_in_season INTEGER NOT NULL,
    n_seasonal    INTEGER NOT NULL,
    PRIMARY KEY (recipe_id, month, strictness)
);
"""


def connect(path=DB_PATH):
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init(conn):
    conn.executescript(SCHEMA)
    conn.commit()


def upsert_source(conn, name, base_url, lang):
    conn.execute(
        "INSERT INTO sources(name, base_url, lang) VALUES (?,?,?) "
        "ON CONFLICT(name) DO UPDATE SET base_url=excluded.base_url",
        (name, base_url, lang),
    )
    conn.commit()
    return conn.execute("SELECT id FROM sources WHERE name=?", (name,)).fetchone()["id"]
