"""grocery.py: aggregate + scale + merge + aisle-group a planned week."""
import db
import grocery


def _corpus(conn):
    sid = db.upsert_source(conn, "15gram", "https://15gram.be", "nl")
    for name in ("aardappel", "ui"):
        conn.execute("INSERT INTO canonical(name_nl, kind) VALUES (?,?)", (name, "vegetable"))
    cid = {r["name_nl"]: r["id"] for r in conn.execute("SELECT id, name_nl FROM canonical")}

    def recipe(url, title, servings, rows):
        conn.execute("INSERT INTO frontier(url, source_id, status, discovered_at) "
                     "VALUES (?,?,'fetched','now')", (url, sid))
        conn.execute("INSERT INTO pages(url, fetched_at, content_hash, html) "
                     "VALUES (?,?,?,?)", (url, "now", "h", "<html/>"))
        conn.execute("INSERT INTO recipes(url, source_id, lang, title, diet, servings, "
                     "parsed_at, parser) VALUES (?,?,?,?,?,?,?,?)",
                     (url, sid, "nl", title, "omnivore", servings, "now", "recipe_scrapers"))
        rid = conn.execute("SELECT id FROM recipes WHERE url=?", (url,)).fetchone()["id"]
        for pos, (canon, text, qty, unit) in enumerate(rows):
            conn.execute("INSERT INTO recipe_ingredients(recipe_id, position, raw_text, "
                         "ingredient_text, qty, unit, canonical_id, is_hero) "
                         "VALUES (?,?,?,?,?,?,?,0)",
                         (rid, pos, text, text, qty, unit, cid.get(canon)))
        return rid

    a = recipe("uA", "Stoofpotje", 4, [
        ("aardappel", "aardappelen", 400, "g"),
        ("ui", "gele ui", 1, None),
        (None, "room", 200, "ml"),
        (None, "olijfolie", None, None)])
    b = recipe("uB", "Puree", 4, [
        ("aardappel", "aardappelen", 600, "g"),
        ("ui", "rode ui", 2, None),
        (None, "zout", None, None)])
    conn.commit()
    return a, b


def _db_and_week():
    conn = db.connect(":memory:")
    db.init(conn)
    a, b = _corpus(conn)
    week = [{"id": a, "scale": 0.75}, {"id": b, "scale": 0.75}]   # 4 servings -> 3.0
    return conn, week


def _find(by_aisle, label):
    for rows in by_aisle.values():
        for it in rows:
            if it["label"] == label:
                return it
    return None


def test_scale_and_merge_across_recipes():
    conn, week = _db_and_week()
    g = grocery.build_grocery(conn, week)
    # 400*0.75 + 600*0.75 = 300 + 450 = 750 g, merged under canonical 'aardappel'
    aardappel = _find(g, "aardappel")
    assert aardappel["qty"] == "750 g"
    assert aardappel["n_recipes"] == 2


def test_canonical_merges_colour_variants():
    conn, week = _db_and_week()
    g = grocery.build_grocery(conn, week)
    # 'gele ui' + 'rode ui' collapse to canonical 'ui'; 1*0.75 + 2*0.75 = 2.25
    ui = _find(g, "ui")
    assert ui is not None
    assert ui["qty"] == f"{round(2.25, 1):g}"     # rounds to 2.2 (banker's)


def test_produce_and_dairy_aisles():
    conn, week = _db_and_week()
    g = grocery.build_grocery(conn, week)
    assert any(it["label"] == "aardappel" for it in g["Groenten & fruit"])
    assert any(it["label"] == "room" for it in g["Zuivel & eieren"])


def test_unquantified_is_to_taste():
    conn, week = _db_and_week()
    g = grocery.build_grocery(conn, week)
    olijfolie = _find(g, "olijfolie")
    assert olijfolie["qty"] == "naar smaak"
    zout = _find(g, "zout")
    assert zout["qty"] == "naar smaak"


def test_format_runs():
    conn, week = _db_and_week()
    out = grocery.format_grocery(grocery.build_grocery(conn, week))
    assert "Groenten & fruit" in out and "aardappel" in out
