"""Weekly menu planner: pick a seasonal, varied week of MAIN dishes.

Given a month (+ diet + strictness + seed), choose WEEK_SIZE mains such that:
  * every dish is a MAIN (courses filter) -- no desserts/sides;
  * its diet is allowed (classify.diet_allows, with the allow_uncertain switch);
  * its seasonal hero is IN SEASON for the month, OR it is season-neutral
    (pasta carbonara is a valid Tuesday); out-of-season heroes are dropped;
  * the week is VARIED by staple base (round-robin over potato/rice/pasta/bread/
    grain) and avoids repeating the same seasonal hero while options remain.

Servings scale to the household (config.household_servings()). Deterministic for
a given seed; change the seed to reroll.

    py planner.py --month 9 --diet vegetarian
"""
import argparse
from collections import defaultdict

import config
import courses
import db
import season
import staples
from classify import diet_allows

MONTHS_NL = ["", "januari", "februari", "maart", "april", "mei", "juni", "juli",
             "augustus", "september", "oktober", "november", "december"]
BASE_ORDER = ["potato", "rice", "pasta", "bread", "grain"]


def build_candidates(conn, month, strictness="greenhouse"):
    """One dict per recipe with everything the planner ranks on."""
    ings_by = season.ingredients_by_recipe(conn)
    scores = season.score_all(conn, month, strictness, ings_by_recipe=ings_by)
    base_by = {rid: base for rid, _t, base, _s in staples.by_recipe(conn)}
    course_by = {rid: c for rid, _t, c in courses.by_recipe(conn)}

    cands = []
    for r in conn.execute(
        "SELECT id, title, diet, servings, url FROM recipes"
    ):
        rid = r["id"]
        score, hero_ok, n = scores.get(rid, (0.0, False, 0))
        cands.append({
            "id": rid, "title": r["title"], "url": r["url"],
            "diet": r["diet"] or "uncertain", "servings": r["servings"],
            "base": base_by.get(rid), "course": course_by.get(rid, "main"),
            "score": score, "hero_ok": hero_ok, "n": n,
            "in_season": n > 0 and hero_ok,
            "heroes": season.heroes_of(ings_by.get(rid, [])),
        })
    return cands


def _eligible(c, diet, allow_uncertain):
    return (c["course"] == "main"
            and c["servings"]                       # need servings to scale
            and diet_allows(c["diet"], diet, allow_uncertain)
            and (c["n"] == 0 or c["hero_ok"]))       # drop out-of-season heroes


def plan_week(conn, month, diet="any", strictness="greenhouse",
              allow_uncertain=False, size=None, seed=0):
    """Return a list of chosen candidate dicts (with a 'scale' factor added)."""
    import random
    size = size or config.WEEK_SIZE
    rng = random.Random(seed)

    pool = [c for c in build_candidates(conn, month, strictness)
            if _eligible(c, diet, allow_uncertain)]
    # rank: in-season before neutral, then higher score, seeded tiebreak
    for c in pool:
        c["_key"] = (1 if c["in_season"] else 0, round(c["score"], 3), rng.random())
    pool.sort(key=lambda c: c["_key"], reverse=True)

    by_base = defaultdict(list)
    for c in pool:
        by_base[c["base"]].append(c)               # base None = flex bucket
    # bases with a real staple first (best option first), flex bucket last
    order = sorted((b for b in by_base if b is not None),
                   key=lambda b: by_base[b][0]["_key"], reverse=True)
    if None in by_base:
        order.append(None)

    chosen, used_ids, used_heroes = [], set(), set()
    while len(chosen) < size:
        progressed = False
        for b in order:
            if len(chosen) >= size:
                break
            pick = _next_pick(by_base[b], used_ids, used_heroes)
            if pick:
                chosen.append(pick)
                used_ids.add(pick["id"])
                used_heroes |= pick["heroes"]
                progressed = True
        if not progressed:                          # pool exhausted
            break

    hh = config.household_servings()
    for c in chosen:
        c["scale"] = round(hh / c["servings"], 2) if c["servings"] else None
    return chosen


def _next_pick(bucket, used_ids, used_heroes):
    """Best unused recipe in a base bucket; prefer one whose hero isn't repeated."""
    fallback = None
    for c in bucket:
        if c["id"] in used_ids:
            continue
        if fallback is None:
            fallback = c
        if not (c["heroes"] & used_heroes):
            return c
    return fallback                                  # all remaining repeat a hero


# --- presentation -----------------------------------------------------------
def format_week(chosen, month, size):
    lines = [f"Weekmenu — {MONTHS_NL[month]}  ({len(chosen)}/{size} dishes)", "=" * 68]
    if len(chosen) < size:
        lines.append(f"  (only {len(chosen)} found — loosen diet/strictness or "
                     f"crawl more recipes)")
    for i, c in enumerate(chosen, 1):
        hero = ", ".join(sorted(c["heroes"])) or "—"
        tag = "in-season" if c["in_season"] else "neutral"
        base = c["base"] or "flex"
        scale = f"x{c['scale']}" if c["scale"] else "?"
        lines.append(f"{i}. [{base:<6}] {(c['title'] or '')[:48]:<48}")
        lines.append(f"     hero: {hero:<22} {tag:<10} diet={c['diet']:<10} "
                     f"scale {scale}")
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser(description="Plan a seasonal week of mains.")
    ap.add_argument("--month", type=int, required=True, choices=range(1, 13),
                    metavar="1-12")
    ap.add_argument("--diet", default="any", choices=["any", "vegetarian", "vegan"])
    ap.add_argument("--strictness", default="greenhouse",
                    choices=["field", "greenhouse", "storage"])
    ap.add_argument("--allow-uncertain", action="store_true",
                    help="include recipes whose diet is 'uncertain'.")
    ap.add_argument("--size", type=int, default=None, help="dishes (default WEEK_SIZE).")
    ap.add_argument("--seed", type=int, default=0, help="change to reroll.")
    args = ap.parse_args()

    conn = db.connect()
    db.init(conn)
    if not conn.execute("SELECT COUNT(*) c FROM seasonality").fetchone()["c"]:
        print("seasonality empty -- run `python load_velt.py` first.")
        return
    week = plan_week(conn, args.month, args.diet, args.strictness,
                     args.allow_uncertain, args.size, args.seed)
    print(format_week(week, args.month, args.size or config.WEEK_SIZE))


if __name__ == "__main__":
    main()
