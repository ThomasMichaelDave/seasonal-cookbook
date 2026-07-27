"""planner.py: seasonal, varied, diet-correct weeks over a seeded corpus."""
import config
import db
import planner


def seed_corpus(conn):
    """A tiny corpus with known seasons so planner behaviour is predictable."""
    sid = db.upsert_source(conn, "15gram", "https://15gram.be", "nl")
    for name in ("aardappel", "asperge", "pompoen", "prei", "tomaat", "courgette"):
        conn.execute("INSERT INTO canonical(name_nl, kind) VALUES (?,?)", (name, "vegetable"))
    cid = {r["name_nl"]: r["id"] for r in conn.execute("SELECT id, name_nl FROM canonical")}
    allyear = list(range(1, 13))
    seasons = {"asperge": [5, 6], "pompoen": [9, 10, 11], "tomaat": [7, 8, 9],
               "courgette": [7, 8, 9], "prei": allyear, "aardappel": allyear}
    for name, months in seasons.items():
        for m in months:
            conn.execute("INSERT INTO seasonality(canonical_id, month, availability, "
                         "cultivation) VALUES (?,?,?,?)", (cid[name], m, 3, "velt"))

    def recipe(url, title, diet, servings, rows):
        conn.execute("INSERT INTO frontier(url, source_id, status, discovered_at) "
                     "VALUES (?,?,'fetched','now')", (url, sid))
        conn.execute("INSERT INTO pages(url, fetched_at, content_hash, html) "
                     "VALUES (?,?,?,?)", (url, "now", "h", "<html/>"))
        conn.execute("INSERT INTO recipes(url, source_id, lang, title, diet, servings, "
                     "parsed_at, parser) VALUES (?,?,?,?,?,?,?,?)",
                     (url, sid, "nl", title, diet, servings, "now", "recipe_scrapers"))
        rid = conn.execute("SELECT id FROM recipes WHERE url=?", (url,)).fetchone()["id"]
        for pos, (canon, hero, text) in enumerate(rows):
            conn.execute("INSERT INTO recipe_ingredients(recipe_id, position, raw_text, "
                         "ingredient_text, qty, unit, canonical_id, is_hero) "
                         "VALUES (?,?,?,?,?,?,?,?)",
                         (rid, pos, text, text, None, None, cid.get(canon), int(hero)))

    recipe("u1", "Aspergesoep met aardappel", "vegan", 4,
           [("asperge", 1, "asperges"), ("aardappel", 0, "aardappelen")])   # potato
    recipe("u2", "Pompoenrisotto met prei", "vegetarian", 4,
           [("pompoen", 1, "pompoen"), ("prei", 0, "prei"), (None, 0, "risottorijst")])  # rice
    recipe("u3", "Pasta met courgette en tomaat", "vegan", 2,
           [("courgette", 1, "courgette"), ("tomaat", 1, "tomaten"), (None, 0, "spaghetti")])  # pasta
    recipe("u4", "Broodje kip met tomaat", "omnivore", 2,
           [("tomaat", 1, "tomaat"), (None, 0, "kipfilet")])                 # bread
    recipe("u5", "Couscous met pompoen", "vegan", 6,
           [("pompoen", 1, "pompoen"), (None, 0, "couscous")])               # grain
    recipe("u6", "Chocoladecake", "vegetarian", 8,
           [(None, 0, "chocolade"), (None, 0, "suiker")])                    # DESSERT
    recipe("u7", "Prei-aardappelstoemp", "vegetarian", 4,
           [("prei", 1, "prei"), ("aardappel", 0, "aardappelen")])          # potato
    recipe("u8", "Pasta carbonara met spek", "omnivore", 4,
           [(None, 0, "spaghetti"), (None, 0, "spekblokjes")])               # pasta, NEUTRAL
    conn.commit()


def _db():
    conn = db.connect(":memory:")
    db.init(conn)
    seed_corpus(conn)
    return conn


def _titles(week):
    return [c["title"] for c in week]


def test_september_excludes_dessert_and_out_of_season():
    week = planner.plan_week(_db(), month=9, diet="any", size=7)
    titles = _titles(week)
    assert "Chocoladecake" not in titles                 # dessert filtered
    assert "Aspergesoep met aardappel" not in titles      # asperge out of season in Sep
    assert len(week) == 6                                  # the 6 eligible mains
    assert all(c["course"] == "main" for c in week)


def test_variety_across_staple_bases():
    week = planner.plan_week(_db(), month=9, diet="any", size=7)
    bases = [c["base"] for c in week]
    assert len({b for b in bases if b}) >= 4               # spread over the bases


def test_season_neutral_is_kept_as_filler():
    week = planner.plan_week(_db(), month=9, diet="any", size=7)
    assert "Pasta carbonara met spek" in _titles(week)     # n==0 neutral, allowed


def test_june_differs_from_september():
    june = _titles(planner.plan_week(_db(), month=6, diet="any", size=7))
    assert "Aspergesoep met aardappel" in june             # asperge in season in June
    assert "Pompoenrisotto met prei" not in june           # pompoen out of season
    assert "Pasta met courgette en tomaat" not in june     # summer produce, out


def test_diet_filter():
    veg = _titles(planner.plan_week(_db(), month=9, diet="vegetarian", size=7))
    assert "Broodje kip met tomaat" not in veg             # omnivore excluded
    assert "Pasta carbonara met spek" not in veg
    vegan = planner.plan_week(_db(), month=9, diet="vegan", size=7)
    assert {c["title"] for c in vegan} == {"Pasta met courgette en tomaat",
                                           "Couscous met pompoen"}


def test_deterministic_for_a_seed():
    a = [c["id"] for c in planner.plan_week(_db(), month=9, seed=3)]
    b = [c["id"] for c in planner.plan_week(_db(), month=9, seed=3)]
    assert a == b


def test_servings_scale_to_household():
    week = planner.plan_week(_db(), month=9, diet="vegan", size=7)
    by_title = {c["title"]: c for c in week}
    hh = config.household_servings()                       # 3.0 by default
    assert by_title["Couscous met pompoen"]["scale"] == round(hh / 6, 2)   # 0.5
    assert by_title["Pasta met courgette en tomaat"]["scale"] == round(hh / 2, 2)  # 1.5
