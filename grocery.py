"""Grocery list for a planned week.

Takes the planner's chosen week, scales each recipe's ingredients to the
household (the 'scale' factor plan_week already attached), merges duplicates
across recipes, and groups the result by supermarket aisle.

Merge key: the seasonal canonical when there is one (so 'gele ui', 'rode ui' and
'uien' all collapse to 'ui'), else the normalised ingredient text. Quantities
sum per unit; an ingredient that some recipes quantify and others don't shows
the sum "+ naar smaak". Fully unquantified seasonings (73% quantity coverage
leaves salt/pepper/oil bare) list as "naar smaak".

    py grocery.py --month 9 --diet vegetarian
"""
import argparse
from collections import defaultdict

import config
import db
import planner
from matching import norm, tokens, hit

# Canonical -> the produce aisle. Everything else is keyword-matched, in order.
PRODUCE_AISLE = "Groenten & fruit"
AISLE_RULES = [
    ("Vlees & vis", {
        "kip", "kipfilet", "kippendij", "kippenbout", "rund", "rundsvlees",
        "gehakt", "spek", "spekjes", "worst", "chorizo", "ham", "hesp", "bacon",
        "varken", "varkenshaas", "varkensreepjes", "lam", "kalf", "kalkoen",
        "steak", "entrecote", "vis", "visfilet", "zalm", "kabeljauw", "tonijn",
        "garnaal", "garnalen", "scampi", "mossel", "mosselen", "ansjovis",
        "sardien", "sardienen", "seitan", "tofu", "tempeh"}),
    ("Zuivel & eieren", {
        "melk", "room", "slagroom", "boter", "kaas", "geitenkaas", "feta",
        "mozzarella", "parmezaan", "mascarpone", "ricotta", "yoghurt", "kwark",
        "ei", "eieren", "eierdooier", "burrata", "halloumi"}),
    ("Pasta, rijst & granen", {
        "pasta", "spaghetti", "penne", "macaroni", "tagliatelle", "orzo",
        "noedel", "noedels", "udon", "soba", "mie", "rijst", "risottorijst",
        "basmati", "couscous", "bulgur", "quinoa", "polenta", "bloem", "meel",
        "paneermeel", "panko", "gnocchi", "lasagne"}),
    ("Brood & bakkerij", {
        "brood", "broodje", "broodjes", "stokbrood", "baguette", "pita",
        "pitabroodje", "naan", "naanbrood", "wrap", "wraps", "tortilla", "taco",
        "pistolet", "focaccia", "ciabatta", "panini"}),
    ("Kruiden & specerijen", {
        "peper", "zout", "kruiden", "paprikapoeder", "komijn", "komijnpoeder",
        "kaneel", "currypoeder", "kurkuma", "oregano", "tijm", "rozemarijn",
        "basilicum", "peterselie", "koriander", "bieslook", "munt", "laurier",
        "nootmuskaat", "dragon", "chilivlokken", "sesamzaad"}),
    ("Sauzen, olie & conserven", {
        "saus", "ketchup", "mosterd", "mayonaise", "mayo", "olie", "olijfolie",
        "azijn", "sojasaus", "kokosmelk", "tomatenpulp", "tomatenblokjes",
        "passata", "bouillon", "currypasta", "pesto", "honing", "suiker",
        "tahin", "harissa", "gochujang", "miso", "kappertjes", "olijven",
        "kikkererwten", "nierbonen", "linzen"}),
]

DISPLAY_UNIT = {
    "g": "g", "kg": "kg", "ml": "ml", "cl": "cl", "dl": "dl", "l": "l",
    "tbsp": "el", "tsp": "kl", "clove": "teentje(s)", "piece": "st",
    "bunch": "bosje", "pinch": "snuf", "can": "blik", "jar": "pot",
    "sachet": "zakje", "handful": "handvol",
}
AISLE_ORDER = [PRODUCE_AISLE, "Vlees & vis", "Zuivel & eieren",
               "Pasta, rijst & granen", "Brood & bakkerij",
               "Sauzen, olie & conserven", "Kruiden & specerijen", "Overig"]


def _aisle(ingredient_text: str, is_produce: bool) -> str:
    if is_produce:
        return PRODUCE_AISLE
    toks = tokens(ingredient_text or "")
    for aisle, terms in AISLE_RULES:
        if hit(toks, terms):
            return aisle
    return "Overig"


def build_grocery(conn, week):
    """week: list of dicts with 'id' and 'scale'. -> {aisle: [item, ...]}.

    Each item: {label, qty (display string), n_recipes}.
    """
    items = {}
    for r in week:
        scale = r.get("scale") or 1.0
        for ing in conn.execute(
            "SELECT ri.ingredient_text itext, ri.raw_text raw, ri.qty qty, "
            "ri.unit unit, c.name_nl canon FROM recipe_ingredients ri "
            "LEFT JOIN canonical c ON ri.canonical_id=c.id "
            "WHERE ri.recipe_id=? ORDER BY ri.position", (r["id"],)
        ):
            text = ing["itext"] or ing["raw"] or ""
            key = ing["canon"] or norm(text)
            if not key:
                continue
            slot = items.setdefault(key, {
                "label": ing["canon"] or text, "produce": ing["canon"] is not None,
                "units": defaultdict(float), "to_taste": False, "recipes": set()})
            slot["recipes"].add(r["id"])
            if ing["qty"] is None:
                slot["to_taste"] = True
            else:
                slot["units"][ing["unit"]] += ing["qty"] * scale

    by_aisle = defaultdict(list)
    for slot in items.values():
        aisle = _aisle(slot["label"], slot["produce"])
        by_aisle[aisle].append({
            "label": slot["label"],
            "qty": _fmt_qty(slot["units"], slot["to_taste"]),
            "n_recipes": len(slot["recipes"]),
        })
    for lst in by_aisle.values():
        lst.sort(key=lambda it: it["label"])
    return dict(by_aisle)


def _fmt_qty(units: dict, to_taste: bool) -> str:
    parts = []
    for unit, q in units.items():
        q = round(q, 1)
        qs = f"{q:g}"
        parts.append(f"{qs} {DISPLAY_UNIT.get(unit, '')}".strip() if unit else qs)
    s = " + ".join(parts)
    if to_taste:
        s = (s + " + naar smaak") if s else "naar smaak"
    return s


def format_grocery(by_aisle) -> str:
    lines = ["Boodschappenlijst", "=" * 50]
    for aisle in AISLE_ORDER:
        rows = by_aisle.get(aisle)
        if not rows:
            continue
        lines.append(f"\n{aisle}")
        for it in rows:
            q = f"  ({it['qty']})" if it["qty"] else ""
            lines.append(f"  - {it['label']}{q}")
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser(description="Grocery list for a planned week.")
    ap.add_argument("--month", type=int, required=True, choices=range(1, 13), metavar="1-12")
    ap.add_argument("--diet", default="any", choices=["any", "vegetarian", "vegan"])
    ap.add_argument("--strictness", default="greenhouse",
                    choices=["field", "greenhouse", "storage"])
    ap.add_argument("--allow-uncertain", action="store_true")
    ap.add_argument("--seed", type=int, default=0)
    args = ap.parse_args()

    conn = db.connect()
    db.init(conn)
    if not conn.execute("SELECT COUNT(*) c FROM seasonality").fetchone()["c"]:
        print("seasonality empty -- run `python load_velt.py` first.")
        return
    week = planner.plan_week(conn, args.month, args.diet, args.strictness,
                             args.allow_uncertain, seed=args.seed)
    print(planner.format_week(week, args.month, config.WEEK_SIZE))
    print("\n" + format_grocery(build_grocery(conn, week)))


if __name__ == "__main__":
    main()
