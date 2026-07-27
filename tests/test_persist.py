"""persist.py: analyse + idempotent storage, and the facts-only guarantee."""
import db
import persist

FAKE = {
    "title": "Steak met prei",
    "ingredients": ["300 g steak", "1 prei", "zout"],
    "servings": 2,
    "total_min": 30,
    "parser": "wild",
    "parser_version": "test",
    "instructions": "SECRET PROSE THAT MUST NEVER BE STORED",
}


def _fresh_db():
    conn = db.connect(":memory:")
    db.init(conn)
    return conn


def _parent_chain(conn, url, sid):
    # recipes.url -> pages.url -> frontier.url, so both parents must exist first
    conn.execute(
        "INSERT INTO frontier(url, source_id, status, discovered_at) "
        "VALUES (?,?,'fetched','now')", (url, sid))
    conn.execute(
        "INSERT INTO pages(url, fetched_at, content_hash, html) VALUES (?,?,?,?)",
        (url, "now", "hash", "<html/>"))
    conn.commit()


def test_store_is_idempotent_across_reparses():
    conn = _fresh_db()
    sid = db.upsert_source(conn, "delhaize", "https://d", "nl")
    url = "https://d/r/1"
    _parent_chain(conn, url, sid)

    diet, ev, parsed = persist.analyse(FAKE)
    r1 = persist.store_recipe(conn, url, sid, "nl", FAKE, diet, ev, parsed)
    r2 = persist.store_recipe(conn, url, sid, "nl", FAKE, diet, ev, parsed)  # re-parse

    assert r1 == r2
    assert conn.execute("SELECT COUNT(*) c FROM recipes").fetchone()["c"] == 1
    n_ing = conn.execute("SELECT COUNT(*) c FROM recipe_ingredients").fetchone()["c"]
    assert n_ing == len(FAKE["ingredients"])          # not doubled on re-parse


def test_analyse_diet_and_hero():
    diet, ev, parsed = persist.analyse(FAKE)
    assert diet == "omnivore"                          # steak is now caught
    prei = next(p for p in parsed if p["canonical"] == "prei")
    assert prei["is_hero"] is True                      # named in the title


def test_instructions_are_never_stored():
    conn = _fresh_db()
    sid = db.upsert_source(conn, "d", "https://d", "nl")
    url = "https://d/r/2"
    _parent_chain(conn, url, sid)

    diet, ev, parsed = persist.analyse(FAKE)
    persist.store_recipe(conn, url, sid, "nl", FAKE, diet, ev, parsed)

    cols = [r[1] for r in conn.execute("PRAGMA table_info(recipes)")]
    assert "instructions" not in cols
    blob = " ".join(
        str(x) for row in conn.execute("SELECT * FROM recipes") for x in row)
    assert "SECRET PROSE" not in blob
