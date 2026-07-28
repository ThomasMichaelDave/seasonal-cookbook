"""recipes.cuisine (v2 prerequisite): a per-source fact, stored and migrated.

Cuisine is declared in config.SOURCES and denormalized onto recipes at persist
time (like lang), so a Belgian stoofpotje and a Sichuan stir-fry are
distinguishable at plan time. These tests are pure -- no network, no fixtures.
"""
import config
import db
import persist

FAKE = {
    "title": "Fakies (lentil soup)",
    "ingredients": ["250 g linzen", "2 wortelen", "1 ui", "zout"],
    "servings": 4,
    "total_min": 45,
    "parser": "wild",
    "parser_version": "test",
    "instructions": "Kook de linzen.",
}


def _fresh():
    conn = db.connect(":memory:")
    db.init(conn)
    return conn


def _parents(conn, url, sid):
    # recipes.url -> pages.url -> frontier.url: both parents must exist first.
    conn.execute("INSERT INTO frontier(url, source_id, status, discovered_at) "
                 "VALUES (?,?,'fetched','now')", (url, sid))
    conn.execute("INSERT INTO pages(url, fetched_at, content_hash, html) "
                 "VALUES (?,?,?,?)", (url, "now", "h", "<html/>"))
    conn.commit()


def _store(conn, url, sid, **kw):
    diet, ev, parsed = persist.analyse(FAKE)
    return persist.store_recipe(conn, url, sid, "en", FAKE, diet, ev, parsed, **kw)


def test_fresh_schema_has_cuisine_column():
    cols = [r[1] for r in _fresh().execute("PRAGMA table_info(recipes)")]
    assert "cuisine" in cols


def test_store_recipe_persists_cuisine():
    conn = _fresh()
    sid = db.upsert_source(conn, "miakouppa", "https://m", "en")
    url = "https://m/fakies/"
    _parents(conn, url, sid)
    _store(conn, url, sid, cuisine="greek")
    got = conn.execute("SELECT cuisine FROM recipes WHERE url=?", (url,)).fetchone()
    assert got["cuisine"] == "greek"


def test_cuisine_defaults_to_null_when_omitted():
    # Backward compatible: existing callers that pass no cuisine still work.
    conn = _fresh()
    sid = db.upsert_source(conn, "d", "https://d", "nl")
    url = "https://d/r/"
    _parents(conn, url, sid)
    _store(conn, url, sid)                      # no cuisine kwarg
    got = conn.execute("SELECT cuisine FROM recipes WHERE url=?", (url,)).fetchone()
    assert got["cuisine"] is None


def test_reparse_backfills_cuisine_on_existing_row():
    # A row first stored without cuisine (as the live db's 686 were) picks it up
    # on re-store, without duplicating -- the reparse backfill path.
    conn = _fresh()
    sid = db.upsert_source(conn, "m", "https://m", "en")
    url = "https://m/x/"
    _parents(conn, url, sid)
    _store(conn, url, sid)                      # cuisine NULL
    _store(conn, url, sid, cuisine="greek")    # reparse
    assert conn.execute("SELECT COUNT(*) c FROM recipes").fetchone()["c"] == 1
    got = conn.execute("SELECT cuisine FROM recipes WHERE url=?", (url,)).fetchone()
    assert got["cuisine"] == "greek"


def test_migration_adds_cuisine_to_older_db():
    # Simulate a pre-cuisine db: a recipes table lacking the column. init() must
    # ALTER it in (like it does for instructions), not choke.
    conn = db.connect(":memory:")
    conn.execute("CREATE TABLE recipes (id INTEGER PRIMARY KEY, url TEXT UNIQUE, "
                 "source_id INTEGER, lang TEXT, title TEXT, diet TEXT, parsed_at TEXT)")
    conn.commit()
    db.init(conn)
    cols = [r[1] for r in conn.execute("PRAGMA table_info(recipes)")]
    assert "cuisine" in cols and "instructions" in cols


def test_every_source_declares_a_cuisine():
    # Guard: a new source without a cuisine would silently store NULL and be
    # invisible to any cuisine-aware planning. Fail loudly instead.
    missing = [n for n, c in config.SOURCES.items() if not c.get("cuisine")]
    assert not missing, f"sources missing a cuisine: {missing}"
