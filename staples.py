"""Staple-base classifier: potato / rice / grain / pasta / bread.

A NEW axis alongside the seasonal hero. The planner centres each day of the
week on a staple base ("every day has a main ingredient it is built around"),
so each main dish is tagged with the one staple it rests on. Like the hero and
the season score, this is DERIVED -- recompute freely, never treat as input.

The base is chosen like the seasonal hero:
  1. if the TITLE names a staple, that's the base (strongest statement);
  2. otherwise the bulkiest staple ingredient by mass;
  3. None if the recipe has no staple at all -- a pure salad or soup is a valid
     dish but not a staple-centred main, and the planner treats it separately.

Run `py staples.py` to see the distribution over cookbook.db and write
dumps/staples.txt (every recipe -> detected base + the staple ingredients) so
the classification can be eyeballed the way ingredients.txt was for diet.
"""
from collections import Counter

import config
import db
from classify import norm, deaccent, tokens

# Order matters: the first family that matches a token wins, so the more
# specific compounds (rice noodles are pasta, not rice) are placed to win.
BASE_ORDER = ["pasta", "potato", "rice", "grain", "bread"]

STAPLE_TERMS = {
    "pasta": {
        "pasta", "spaghetti", "penne", "macaroni", "tagliatelle", "fusilli",
        "farfalle", "tortellini", "ravioli", "cannelloni", "lasagne", "lasagna",
        "orzo", "vermicelli", "gnocchi", "spatzle", "noedel", "noodle", "mie",
        "udon", "soba", "bami", "mihoen", "rijstnoedel", "eiernoedel",
        "cappellini", "linguine", "rigatoni", "conchiglie", "fettuccine",
    },
    "potato": {
        "aardappel", "krielaardappel", "kriel", "krieltje", "patat", "friet",
        "frietaardappel", "aardappelpuree",
    },
    "rice": {
        "rijst", "basmati", "risotto", "risottorijst", "paella", "jasmijnrijst",
        "zilvervliesrijst", "sushirijst", "pandanrijst", "arborio",
    },
    "grain": {
        "couscous", "bulgur", "quinoa", "boekweit", "gierst", "spelt",
        "parelgort", "polenta", "gort", "farro", "freekeh", "griesmeel",
    },
    "bread": {
        "brood", "broodje", "stokbrood", "baguette", "ciabatta", "focaccia",
        "pita", "naan", "naanbrood", "wrap", "miniwrap", "tortilla", "taco",
        "quesadilla", "burgerbroodje", "hamburgerbroodje", "pistolet", "toast",
        "bagel", "roti", "flatbread", "boterham", "pannenkoek", "tortiwrap",
    },
}

# Compounds that CONTAIN a staple stem but are not that staple. Stripped before
# matching, exactly like SAFE_COMPOUNDS in the diet lexicon.
NOT_A_STAPLE = {
    "rijstmelk", "rijstazijn", "rijstwijn", "rijstpapier",       # not rice base
    "aardappelzetmeel", "aardappelmeel",                         # potato starch
    "paneermeel", "panko", "broodkruimels", "broodkruim",        # breadcrumbs
    "broodbeleg",
}

MIN_PREFIX = 4


def staple_of_text(text: str):
    """Return the staple base a single ingredient/title string names, or None."""
    flat = deaccent(norm(text))
    for bad in NOT_A_STAPLE:
        if bad in flat:
            flat = flat.replace(bad, " ")
    # tokens() splits on alpha-runs, so "torti'wraps" -> ["torti","wraps"] and
    # digits/punctuation drop out (same tokeniser the diet lexicon uses).
    toks = tokens(flat)
    for base in BASE_ORDER:
        for tok in toks:
            for term in STAPLE_TERMS[base]:
                dterm = deaccent(term)
                if tok == dterm or (len(dterm) >= MIN_PREFIX and tok.startswith(dterm)):
                    return base
    return None


def _text(ing) -> str:
    return (ing.get("ingredient_text") or ing.get("raw")
            or ing.get("raw_text") or "")


def _mass(ing) -> float:
    qty, unit = ing.get("qty") or 0, ing.get("unit")
    if unit == "kg":
        return qty * 1000
    if unit == "g":
        return qty
    return qty * 100          # pieces/None: rough grams-equivalent


def classify_staple(title: str, ings: list) -> str | None:
    """Pick the one staple base a recipe is built on (title first, then bulk)."""
    tb = staple_of_text(title or "")
    if tb:
        return tb
    best, best_mass = None, -1.0
    for ing in ings:
        base = staple_of_text(_text(ing))
        if base is None:
            continue
        m = _mass(ing)
        if m > best_mass:
            best, best_mass = base, m
    return best


# --- reporting over the db --------------------------------------------------
def by_recipe(conn):
    """Yield (recipe_id, title, base, staple_ingredient_texts) per recipe."""
    rows = conn.execute(
        "SELECT r.id, r.title, ri.ingredient_text, ri.raw_text, ri.qty, ri.unit "
        "FROM recipes r JOIN recipe_ingredients ri ON ri.recipe_id=r.id "
        "ORDER BY r.id, ri.position").fetchall()
    cur_id = None
    title = None
    ings = []
    for row in rows:
        if row["id"] != cur_id:
            if cur_id is not None:
                yield _emit(cur_id, title, ings)
            cur_id, title, ings = row["id"], row["title"], []
        ings.append({"ingredient_text": row["ingredient_text"],
                     "raw_text": row["raw_text"], "qty": row["qty"],
                     "unit": row["unit"]})
    if cur_id is not None:
        yield _emit(cur_id, title, ings)


def _emit(rid, title, ings):
    base = classify_staple(title or "", ings)
    staples = [_text(i) for i in ings if staple_of_text(_text(i))]
    return rid, title, base, staples


def distribution(conn) -> Counter:
    c = Counter()
    for _rid, _title, base, _staples in by_recipe(conn):
        c[base or "none"] += 1
    return c


def main():
    conn = db.connect()
    db.init(conn)
    n = conn.execute("SELECT COUNT(*) c FROM recipes").fetchone()["c"]
    if not n:
        print("no recipes yet -- run crawl.py first.")
        return

    config.DUMP_DIR.mkdir(exist_ok=True)
    dump_path = config.DUMP_DIR / "staples.txt"
    dist = Counter()
    with open(dump_path, "w", encoding="utf-8") as f:
        for rid, title, base, staples in by_recipe(conn):
            dist[base or "none"] += 1
            f.write(f"[{base or 'none':<6}] {title}\n")
            f.write(f"         staples: {staples or '-'}\n")

    print("=" * 60)
    print(f"STAPLE BASE distribution over {n:,} recipes")
    print("=" * 60)
    for base in BASE_ORDER + ["none"]:
        c = dist.get(base, 0)
        print(f"   {base:<8} {c:>5,}  {100*c/n:4.0f}%")
    print(f"\neyeball the classification: {dump_path}")


if __name__ == "__main__":
    main()
