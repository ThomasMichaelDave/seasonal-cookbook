"""Season scoring over the database.

Wraps classify.season_score with the DB plumbing: it loads the Velt seasonality
table and reconstructs each recipe's canonical/hero ingredients, so the planner
can ask "which mains have a hero in season in month M at strictness S?".

season_score returns (score, hero_in_season, n_seasonal) per recipe:
  * n_seasonal == 0        -> SEASON-NEUTRAL (pasta carbonara): plannable filler
  * hero_in_season == True -> IN SEASON: plannable, ranked by score
  * else                   -> out-of-season hero: the planner drops it
"""
from classify import season_score


def load_seasonality(conn) -> dict:
    """{canonical_nl: {(month, cultivation): availability}} from the Velt table."""
    out = {}
    for r in conn.execute(
        "SELECT c.name_nl n, s.month m, s.cultivation cult, s.availability a "
        "FROM seasonality s JOIN canonical c ON s.canonical_id=c.id"
    ):
        out.setdefault(r["n"], {})[(r["m"], r["cult"])] = r["a"]
    return out


def ingredients_by_recipe(conn) -> dict:
    """{recipe_id: [{canonical, is_hero, qty, unit}, ...]} for season_score."""
    out = {}
    for row in conn.execute(
        "SELECT r.id rid, c.name_nl canon, ri.is_hero hero, ri.qty qty, ri.unit unit "
        "FROM recipes r JOIN recipe_ingredients ri ON ri.recipe_id=r.id "
        "LEFT JOIN canonical c ON ri.canonical_id=c.id ORDER BY r.id, ri.position"
    ):
        out.setdefault(row["rid"], []).append(
            {"canonical": row["canon"], "is_hero": bool(row["hero"]),
             "qty": row["qty"], "unit": row["unit"]})
    return out


def score_all(conn, month: int, strictness: str = "greenhouse",
              ings_by_recipe: dict | None = None) -> dict:
    """{recipe_id: (score, hero_in_season, n_seasonal)} for every recipe."""
    seas = load_seasonality(conn)
    ings = ings_by_recipe if ings_by_recipe is not None else ingredients_by_recipe(conn)
    return {rid: season_score(lst, month, seas, strictness)
            for rid, lst in ings.items()}


def heroes_of(ingredients) -> set:
    """The seasonal-hero canonicals of one recipe (non-aromatic by construction)."""
    return {i["canonical"] for i in ingredients if i["is_hero"] and i["canonical"]}
