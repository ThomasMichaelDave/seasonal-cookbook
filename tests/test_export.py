"""export.py: facts-only, standalone, self-contained single-file build."""
import json

import db
import export
from tests.test_planner import seed_corpus


def _data():
    conn = db.connect(":memory:")
    db.init(conn)
    seed_corpus(conn)
    return export.build_data(conn)


def test_only_mains_with_servings_exported():
    data = _data()
    titles = {r["title"] for r in data["recipes"]}
    assert "Chocoladecake" not in titles          # dessert excluded
    assert all(r["servings"] for r in data["recipes"])
    assert data["meta"]["nMains"] == len(data["recipes"])


def test_recipe_shape_is_facts_only():
    data = _data()
    r = next(r for r in data["recipes"] if r["title"].startswith("Pompoen"))
    assert r["base"] == "rice" and "pompoen" in r["heroes"]
    assert r["url"] and r["diet"] and r["servings"]
    assert "pompoen" in r["produce"] and r["flexible"] is False   # waste/scraps fields
    ing = r["ingredients"][0]
    assert set(ing) == {"text", "qty", "unit", "unitDisplay", "canonical", "aisle"}
    # no instruction/prose field anywhere
    assert "instructions" not in r and "instruction" not in json.dumps(r).lower()


def test_produce_excludes_aromatics_and_flexible_flag():
    import export
    assert export.is_flexible("Traybake met kip en groenten") is True
    assert export.is_flexible("Ovenschotel met prei") is True
    assert export.is_flexible("Pasta arrabiata") is False
    data = _data()
    # 'ui' is an aromatic -> must not appear in any recipe's produce list
    assert all("ui" not in r["produce"] for r in data["recipes"])


def test_seasonality_map_present():
    data = _data()
    assert data["seasonality"]["asperge"] == [5, 6]
    assert 9 in data["seasonality"]["pompoen"]


def test_html_is_self_contained_and_offline():
    html = export.render_html(_data())
    assert html.lstrip().startswith("<!doctype html>")
    assert "const DATA = {" in html                # data inlined, not fetched
    assert "/*__DATA__*/" not in html              # placeholder was replaced
    # no external resources -> works offline by double-click
    for bad in ['src="http', "href=\"http://", "cdn.", "fetch(", "XMLHttpRequest"]:
        assert bad not in html
    # the recipe titles made it in
    assert "Pompoenrisotto" in html


def test_no_recipes_still_renders():
    conn = db.connect(":memory:")
    db.init(conn)
    # seasonality present but no recipes
    conn.execute("INSERT INTO canonical(name_nl, kind) VALUES ('prei','vegetable')")
    cid = conn.execute("SELECT id FROM canonical").fetchone()[0]
    conn.execute("INSERT INTO seasonality(canonical_id,month,availability,cultivation) "
                 "VALUES (?,?,?,?)", (cid, 1, 3, "velt"))
    conn.commit()
    data = export.build_data(conn)
    assert data["recipes"] == []
    export.render_html(data)                        # must not raise
