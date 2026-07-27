"""report.py: corpus coverage math over a synthetic in-memory db."""
import db
import report


def _seed(conn):
    sid = db.upsert_source(conn, "15gram", "https://15gram.be", "nl")
    # canonical: one aromatic (ui), two real produce (prei, tomaat)
    for nl, kind in [("ui", "vegetable"), ("prei", "vegetable"), ("tomaat", "vegetable")]:
        conn.execute("INSERT INTO canonical(name_nl, kind) VALUES (?,?)", (nl, kind))
    cid = {r["name_nl"]: r["id"] for r in conn.execute("SELECT id, name_nl FROM canonical")}

    def recipe(url, diet, servings, rows):
        conn.execute("INSERT INTO frontier(url, source_id, status, discovered_at) "
                     "VALUES (?,?,'fetched','now')", (url, sid))
        conn.execute("INSERT INTO pages(url, fetched_at, content_hash, html) "
                     "VALUES (?,?,?,?)", (url, "now", "h", "<html/>"))
        conn.execute("INSERT INTO recipes(url, source_id, lang, diet, servings, "
                     "parsed_at, parser) VALUES (?,?,?,?,?,?,?)",
                     (url, sid, "nl", diet, servings, "now", "recipe_scrapers"))
        rid = conn.execute("SELECT id FROM recipes WHERE url=?", (url,)).fetchone()["id"]
        for pos, (canon, qty, hero) in enumerate(rows):
            conn.execute(
                "INSERT INTO recipe_ingredients(recipe_id, position, raw_text, qty, "
                "unit, ingredient_text, canonical_id, is_hero) VALUES (?,?,?,?,?,?,?,?)",
                (rid, pos, "x", qty, None, "x",
                 cid.get(canon) if canon else None, hero))

    # R1: prei hero (+ aromatic ui)         -> heroed, has produce
    recipe("u/1", "vegan", 4, [("prei", 1.0, 1), ("ui", 1.0, 0)])
    # R2: tomaat hero                        -> heroed, has produce
    recipe("u/2", "omnivore", 2, [("tomaat", 2.0, 1), (None, None, 0)])
    # R3: only aromatic ui + non-produce     -> NOT heroed, season-neutral
    recipe("u/3", "vegetarian", None, [("ui", 1.0, 0), (None, None, 0)])
    conn.commit()


def test_coverage_numbers():
    conn = db.connect(":memory:")
    db.init(conn)
    _seed(conn)
    s = report.compute(conn)

    assert s["n_recipes"] == 3
    assert s["hero_recipes"] == 2                # R1, R2
    assert s["produce_recipes"] == 2             # ui-only R3 doesn't count
    assert s["neutral_recipes"] == 1             # R3
    assert s["servings_known"] == 2              # R3 has no servings
    assert s["qty_lines"] == 4                   # prei, ui, tomaat, ui
    heroes = {r["name_nl"] for r in s["top_heroes"]}
    assert heroes == {"prei", "tomaat"}          # ui is never a hero


def test_empty_db_is_graceful():
    conn = db.connect(":memory:")
    db.init(conn)
    s = report.compute(conn)
    assert s["n_recipes"] == 0
    report.render(s)                             # must not raise
