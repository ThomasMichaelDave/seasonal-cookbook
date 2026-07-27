"""Shared recipe persistence: analyse a parsed recipe and store it idempotently.

Used by BOTH `spike.py` (the small probe) and `crawl.py` (the wider crawl) so
the two can never drift -- in particular the idempotent upsert that lets a
recipe be re-parsed from cache many times (decision #1) without duplicating
rows or tripping the recipe_ingredients foreign key.

Stores FACTS ONLY: ingredients, quantities, servings, timings, source url.
Never instruction text, headnotes or images -- those are the copyrightable
parts, and `recipes` has no column for them on purpose. See docs/research.md
and docs/decisions.md #8.
"""
from datetime import datetime, timezone

from classify import (
    parse_ingredient, match_seasonal, classify_recipe, mark_heroes,
)


def _now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def analyse(rec: dict):
    """rec (from parse.parse_recipe) -> (diet, evidence, parsed_ingredients).

    Each parsed ingredient carries raw/qty/unit/ingredient_text/prep_note plus
    `canonical` (seasonal match) and `is_hero`. `rec['instructions']` is
    deliberately ignored -- it is never read here and never stored.
    """
    diet, evidence = classify_recipe(rec["ingredients"])
    parsed = []
    for ing in rec["ingredients"]:
        p = parse_ingredient(ing)
        p["raw"] = ing
        p["canonical"] = match_seasonal(p["ingredient_text"] or ing)
        parsed.append(p)
    mark_heroes(rec.get("title") or "", parsed)
    return diet, evidence, parsed


def store_recipe(conn, url, source_id, lang, rec, diet, evidence, parsed) -> int:
    """Idempotent upsert of one recipe + its ingredient rows. Returns recipe id.

    Re-parsing from cache is a supported, repeated operation, so this must not
    duplicate rows or rely on lastrowid (which is 0 when an INSERT OR IGNORE is
    ignored -- the child insert would then trip the FK). Upsert the recipe,
    read its real id, clear prior ingredient rows, reinsert.
    """
    conn.execute(
        "INSERT INTO recipes(url, source_id, lang, title, servings, total_min, "
        "diet, diet_evidence, parsed_at, parser, parser_version) "
        "VALUES (?,?,?,?,?,?,?,?,?,?,?) "
        "ON CONFLICT(url) DO UPDATE SET "
        "  lang=excluded.lang, title=excluded.title, servings=excluded.servings, "
        "  total_min=excluded.total_min, diet=excluded.diet, "
        "  diet_evidence=excluded.diet_evidence, parsed_at=excluded.parsed_at, "
        "  parser=excluded.parser, parser_version=excluded.parser_version",
        (url, source_id, lang, rec.get("title"), rec.get("servings"),
         rec.get("total_min"), diet, "\n".join(evidence), _now(),
         rec["parser"], rec.get("parser_version")),
    )
    rid = conn.execute("SELECT id FROM recipes WHERE url=?", (url,)).fetchone()["id"]
    conn.execute("DELETE FROM recipe_ingredients WHERE recipe_id=?", (rid,))
    for i, p in enumerate(parsed):
        cid = None
        if p["canonical"]:
            row = conn.execute(
                "SELECT id FROM canonical WHERE name_nl=?", (p["canonical"],)
            ).fetchone()
            cid = row["id"] if row else None
        conn.execute(
            "INSERT INTO recipe_ingredients(recipe_id, position, raw_text, qty, "
            "unit, ingredient_text, prep_note, canonical_id, is_hero) "
            "VALUES (?,?,?,?,?,?,?,?,?)",
            (rid, i, p["raw"], p["qty"], p["unit"], p["ingredient_text"],
             p["prep_note"], cid, int(p.get("is_hero", False))),
        )
    return rid
