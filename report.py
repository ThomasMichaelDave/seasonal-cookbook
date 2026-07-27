"""Read-only corpus report over cookbook.db. No network, no writes.

Answers the gating question from CLAUDE.md -- how many scraped recipes have a
seasonal hero at all -- plus the coverage the planner will need (servings and
parsed quantities, for scaling to a household) and the diet mix.

    py report.py

A hero is a non-aromatic seasonal produce item the recipe is built on
(classify.mark_heroes). Because mark_heroes always promotes at least one hero
when any non-aromatic produce is present, "has a hero" is effectively "has a
seasonal produce item to score against". Recipes with none are SEASON-NEUTRAL
(pasta carbonara), not out of season -- the planner keeps them.
"""
from collections import Counter

import config
import courses
import db
import season
import staples
from classify import AROMATICS

_ARO = tuple(AROMATICS)
_ARO_Q = ",".join("?" * len(_ARO))


def _n(conn, sql, args=()):
    return conn.execute(sql, args).fetchone()[0]


def compute(conn):
    s = {}
    s["n_recipes"] = _n(conn, "SELECT COUNT(*) FROM recipes")
    if not s["n_recipes"]:
        return s

    s["n_ing"] = _n(conn, "SELECT COUNT(*) FROM recipe_ingredients")
    s["n_matched"] = _n(
        conn, "SELECT COUNT(*) FROM recipe_ingredients WHERE canonical_id IS NOT NULL")

    s["by_source"] = conn.execute(
        "SELECT s.name, COUNT(*) c FROM recipes r JOIN sources s ON r.source_id=s.id "
        "GROUP BY s.name ORDER BY c DESC").fetchall()
    s["by_parser"] = conn.execute(
        "SELECT COALESCE(parser,'?') p, COUNT(*) c FROM recipes GROUP BY p "
        "ORDER BY c DESC").fetchall()
    s["diet"] = conn.execute(
        "SELECT diet, COUNT(*) c FROM recipes GROUP BY diet ORDER BY c DESC").fetchall()

    # THE gating number: recipes with at least one seasonal hero.
    s["hero_recipes"] = _n(
        conn, "SELECT COUNT(DISTINCT recipe_id) FROM recipe_ingredients WHERE is_hero=1")
    # recipes carrying any NON-AROMATIC seasonal produce (whether hero or side)
    s["produce_recipes"] = _n(
        conn,
        "SELECT COUNT(DISTINCT ri.recipe_id) FROM recipe_ingredients ri "
        "JOIN canonical c ON ri.canonical_id=c.id "
        f"WHERE c.name_nl NOT IN ({_ARO_Q})", _ARO)
    s["neutral_recipes"] = s["n_recipes"] - s["produce_recipes"]

    s["top_heroes"] = conn.execute(
        "SELECT c.name_nl, COUNT(DISTINCT ri.recipe_id) c FROM recipe_ingredients ri "
        "JOIN canonical c ON ri.canonical_id=c.id WHERE ri.is_hero=1 "
        "GROUP BY c.name_nl ORDER BY c DESC LIMIT 20").fetchall()

    # planner readiness: scaling needs servings + parsed quantities
    s["servings_known"] = _n(
        conn, "SELECT COUNT(*) FROM recipes WHERE servings IS NOT NULL")
    s["qty_lines"] = _n(
        conn, "SELECT COUNT(*) FROM recipe_ingredients WHERE qty IS NOT NULL")
    s["hero_per_source"] = conn.execute(
        "SELECT s.name, COUNT(DISTINCT r.id) tot, "
        "  COUNT(DISTINCT CASE WHEN ri.is_hero=1 THEN r.id END) heroed "
        "FROM recipes r JOIN sources s ON r.source_id=s.id "
        "LEFT JOIN recipe_ingredients ri ON ri.recipe_id=r.id "
        "GROUP BY s.name ORDER BY tot DESC").fetchall()

    s["staples"] = staples.distribution(conn)   # the planner's second axis

    # course + the actual planner pool: mains that have a staple base
    base_by_id = {rid: base for rid, _t, base, _s in staples.by_recipe(conn)}
    course_by_id = {}
    s["courses"] = Counter()
    s["mains_with_base"] = 0
    for rid, _title, course in courses.by_recipe(conn):
        course_by_id[rid] = course
        s["courses"][course] += 1
        if course == "main" and base_by_id.get(rid):
            s["mains_with_base"] += 1

    # THE honest gating metric (review P3): per month, how many MAINS have a
    # hero actually in season -- not just "contains a produce word". This is the
    # number that says whether the planner has a pool; expect it well below the
    # produce-presence figure and to vary a lot by month.
    s["by_month"] = in_season_mains_by_month(conn, course_by_id)
    s["n_mains"] = s["courses"].get("main", 0)
    return s


def in_season_mains_by_month(conn, course_by_id, strictness="greenhouse"):
    """{month: (mains_with_hero_in_season, season_neutral_mains)} for months 1-12."""
    ings = season.ingredients_by_recipe(conn)
    out = {}
    for m in range(1, 13):
        scores = season.score_all(conn, m, strictness, ings_by_recipe=ings)
        in_season = neutral = 0
        for rid, (_score, hero_ok, n) in scores.items():
            if course_by_id.get(rid) != "main":
                continue
            if hero_ok:
                in_season += 1
            elif n == 0:
                neutral += 1
        out[m] = (in_season, neutral)
    return out


def _pct(n, d):
    return f"{100*n/d:4.0f}%" if d else "   -"


def render(s):
    def line(msg=""):
        print(msg)

    n = s["n_recipes"]
    line("=" * 70)
    line(f"CORPUS REPORT  ({config.DB_PATH.name})")
    line("=" * 70)
    if not n:
        line("no recipes yet -- run crawl.py first.")
        return

    line(f"\nrecipes: {n:,}   ingredient lines: {s['n_ing']:,}   "
         f"seasonal matches: {s['n_matched']:,} ({_pct(s['n_matched'], s['n_ing']).strip()})")
    line("  by source:")
    for r in s["by_source"]:
        line(f"     {r['name']:<16} {r['c']:,}")
    line("  by parser route:")
    for r in s["by_parser"]:
        line(f"     {r['p']:<16} {r['c']:,}")

    line("\ndiet mix:")
    for r in s["diet"]:
        line(f"     {r['diet']:<12} {r['c']:>5,}  {_pct(r['c'], n)}")

    line("\nSEASONAL PRODUCE PRESENCE  (NOT the gating number -- see per-month below)")
    line(f"     contains seasonal produce: {s['produce_recipes']:>5,}  {_pct(s['produce_recipes'], n)}"
         "   (a produce word is present; mark_heroes always")
    line(f"     season-neutral (no produce): {s['neutral_recipes']:>5,}  {_pct(s['neutral_recipes'], n)}"
         "    picks one, so this over-counts salience)")
    line("  hero coverage by source:")
    for r in s["hero_per_source"]:
        line(f"     {r['name']:<16} {r['heroed']:>5,}/{r['tot']:<5,} {_pct(r['heroed'], r['tot'])}")

    line("\n  top heroes:")
    for r in s["top_heroes"]:
        line(f"     {r['name_nl']:<18} {r['c']:,}")

    line("\nSTAPLE BASE  (the planner's second axis -- one main-ingredient/day)")
    for base in staples.BASE_ORDER + ["none"]:
        c = s["staples"].get(base, 0)
        note = "   (no staple: salad/soup, handled separately)" if base == "none" else ""
        line(f"     {base:<8} {c:>5,}  {_pct(c, n)}{note}")

    line("\nCOURSE  (mains-only planner: desserts/sides are excluded)")
    for course in ("main", "dessert", "side"):
        c = s["courses"].get(course, 0)
        line(f"     {course:<8} {c:>5,}  {_pct(c, n)}")
    line(f"  >> planner pool (mains with a staple base): {s['mains_with_base']:,}")

    line(f"\nIN-SEASON MAINS BY MONTH  (the gating number; of {s['n_mains']:,} mains, "
         "greenhouse strictness)")
    line("     month    1   2   3   4   5   6   7   8   9  10  11  12")
    row_hero = "     hero  " + "".join(f"{s['by_month'][m][0]:>4}" for m in range(1, 13))
    row_neu = "     +neut " + "".join(f"{s['by_month'][m][1]:>4}" for m in range(1, 13))
    line(row_hero)
    line(row_neu + "   (season-neutral mains, always plannable)")
    feb = s["by_month"][2][0]
    line(f"  >> February in-season mains: {feb}  -- if thin, that's the v2 winter-crawl "
         "signal, not a bug (docs/vegan_sources.md)")

    line("\nPLANNER READINESS")
    line(f"     recipes with servings: {s['servings_known']:>5,}  {_pct(s['servings_known'], n)}"
         "   (needed to scale to a household)")
    line(f"     ingredient lines with qty: {s['qty_lines']:>5,}  {_pct(s['qty_lines'], s['n_ing'])}")


def main():
    conn = db.connect()
    db.init(conn)
    render(compute(conn))


if __name__ == "__main__":
    main()
