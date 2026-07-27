"""Staple-base classifier: potato / rice / grain / pasta / bread.

A NEW axis alongside the seasonal hero. The planner centres each day of the
week on a staple base ("every day has a main ingredient it is built around"),
so each main dish is tagged with the one staple it rests on. Like the hero and
the season score, this is DERIVED -- recompute freely, never treat as input.

How the base is chosen (learned from dumps/staples.txt on the real crawl):

  1. The TITLE decides first. A non-bread staple named in the title (pasta,
     rijst, risotto, couscous, quinoa, aardappel, krieltjes...) is the base. So
     is a bread FORM in the title -- burger, pizza, broodje, pita, naan, wrap,
     taco, panini... -- because those dishes ARE bread even when the bun/dough
     is only implied and never listed as an ingredient.
  2. Otherwise the bulkiest NON-BREAD staple ingredient (pasta/rice/potato/
     grain). Bread ingredients are deliberately excluded here: a bread roll
     served alongside a waterzooi or a salad is a SIDE, not the base.
  3. Otherwise bread, but only if a HANDHELD bread form is an ingredient
     (pita/naan/wrap/tortilla/taco/quesadilla/bun/flatbread) -- not a loose
     'stokbrood'/'lookbrood' accompaniment.
  4. Otherwise None -- a salad, soup or dessert is a valid dish but not a
     staple-centred main, and the planner treats it separately.

Run `py staples.py` to see the distribution over cookbook.db and write
dumps/staples.txt (every recipe -> detected base + the staple ingredients) so
the classification can be eyeballed, the way ingredients.txt was for diet.
"""
from collections import Counter

import config
import db
from matching import norm, deaccent, tokens, hit, strip_false_friends

BASE_ORDER = ["pasta", "potato", "rice", "grain", "bread"]
NONBREAD = ("pasta", "potato", "rice", "grain")

STAPLE_TERMS = {
    "pasta": {
        "pasta", "spaghetti", "penne", "macaroni", "tagliatelle", "fusilli",
        "farfalle", "tortellini", "ravioli", "cannelloni", "lasagne", "lasagna",
        "orzo", "vermicelli", "gnocchi", "spatzle", "noedel", "noodle", "mie",
        "udon", "soba", "bami", "mihoen", "rijstnoedel", "eiernoedel",
        "cappellini", "linguine", "rigatoni", "conchiglie", "fettuccine",
        "orecchiette", "casarecce", "spirelli", "fregola",
    },
    "potato": {
        "aardappel", "krielaardappel", "kriel", "krieltje", "patat", "friet",
        "frietaardappel", "aardappelpuree",
    },
    "rice": {
        "rijst", "basmati", "risotto", "risottorijst", "paella", "jasmijnrijst",
        "zilvervliesrijst", "sushirijst", "sushi", "pandanrijst", "arborio",
    },
    "grain": {
        "couscous", "parelcouscous", "bulgur", "quinoa", "boekweit", "gierst",
        "spelt", "parelgort", "polenta", "gort", "farro", "freekeh", "griesmeel",
    },
    "bread": {
        "brood", "broodje", "stokbrood", "baguette", "ciabatta", "focaccia",
        "pita", "naan", "naanbrood", "wrap", "miniwrap", "tortilla", "taco",
        "quesadilla", "burgerbroodje", "hamburgerbroodje", "pistolet", "toast",
        "roti", "flatbread", "boterham", "pannenkoek", "tortiwrap", "durum",
    },
}

# Compounds that CONTAIN a staple stem but are not that staple -- stripped
# before matching, like SAFE_COMPOUNDS in the diet lexicon. The pastes matter:
# 'harissa/gochujang/miso pasta' are CONDIMENTS, and 'spaghettikruiden' is a
# spice mix -- none of them is a noodle.
NOT_A_STAPLE = {
    "rijstmelk", "rijstazijn", "rijstwijn", "rijstpapier",       # not rice base
    "aardappelzetmeel", "aardappelmeel",                         # potato starch
    "paneermeel", "panko", "broodkruimels", "broodkruim", "broodbeleg",
    "harissa pasta", "gochujang pasta", "miso pasta", "spaghettikruiden",
}

# Bread FORMS that, as an INGREDIENT, make a dish bread-based. A loose
# 'stokbrood'/'lookbrood'/'broodje' served on the side does NOT -- it is an
# accompaniment, so those are excluded here (the title still catches a real
# 'Broodje ...' sandwich via TITLE_BREAD).
BREAD_STRONG = {
    "pita", "pitabroodje", "naan", "naanbrood", "wrap", "miniwrap", "tortilla",
    "tortiwrap", "taco", "quesadilla", "burgerbroodje", "hamburgerbroodje",
    "flatbread", "durum",
}

# A bread FORM in the title makes the dish bread-based even with no bread
# ingredient. Distinctive forms count ANYWHERE in the title; 'burger'/'pizza'
# are matched as a substring to catch Dutch compounds (rundsburger, pompoenpizza).
TITLE_BREAD_STRONG = {
    "pita", "naan", "wrap", "taco", "quesadilla", "panini", "bruschetta",
    "panzanella", "flatbread", "focaccia", "pistolet", "durum", "enchilada",
    "enchillada", "fajita", "tortilla", "banh", "hotdog",
}
# Generic bread words only count in the title CORE (before ' met '): 'Broodje
# kip' is a sandwich, but 'waterzooi met knapperig brood' has bread as a SIDE.
TITLE_BREAD_WEAK = {"brood", "broodje", "toast"}


def _family_of(text: str, families) -> str | None:
    """First family (in `families` order) whose term matches a token, else None."""
    toks = tokens(strip_false_friends(text, NOT_A_STAPLE))
    for base in families:
        if hit(toks, STAPLE_TERMS[base]):
            return base
    return None


def staple_of_text(text: str) -> str | None:
    """The staple family a single ingredient/string names, any base. For the dump."""
    return _family_of(text, BASE_ORDER)


def _has_strong_bread(text: str) -> bool:
    return hit(tokens(deaccent(norm(text))), BREAD_STRONG)


def _title_base(title: str) -> str | None:
    # non-bread staple in the title wins first, so a veg/grain burger keeps its
    # grain ('quinoaburger' -> grain) and 'steak met pasta' -> pasta.
    nb = _family_of(title or "", NONBREAD)
    if nb:
        return nb
    flat = deaccent(norm(title or ""))
    for tok in tokens(flat):                       # distinctive forms, anywhere
        # substring so Dutch compounds are caught: rundsburger, pompoenpizza,
        # komkommersandwich. 'sushi sandwich' is already rice (checked above).
        if "pizza" in tok or "burger" in tok or "sandwich" in tok:
            return "bread"
        if any(tok.startswith(p) for p in TITLE_BREAD_STRONG):
            return "bread"
    core = flat.split(" met ")[0]                  # generic bread: dish word only
    for tok in tokens(core):
        if any(tok.startswith(p) for p in TITLE_BREAD_WEAK):
            return "bread"
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
    """Pick the one staple base a recipe is built on (see module docstring)."""
    tb = _title_base(title)
    if tb:
        return tb
    best, best_mass = None, -1.0
    for ing in ings:
        base = _family_of(_text(ing), NONBREAD)   # bread excluded: side, not base
        if base is None:
            continue
        m = _mass(ing)
        if m > best_mass:
            best, best_mass = base, m
    if best:
        return best
    if any(_has_strong_bread(_text(i)) for i in ings):
        return "bread"
    return None


# --- reporting over the db --------------------------------------------------
def by_recipe(conn):
    """Yield (recipe_id, title, base, staple_ingredient_texts) per recipe."""
    rows = conn.execute(
        "SELECT r.id, r.title, ri.ingredient_text, ri.raw_text, ri.qty, ri.unit "
        "FROM recipes r JOIN recipe_ingredients ri ON ri.recipe_id=r.id "
        "ORDER BY r.id, ri.position").fetchall()
    cur_id = title = None
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
        for _rid, title, base, staples in by_recipe(conn):
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
