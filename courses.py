"""Course filter: is a recipe a MAIN, or a dessert/side to leave out?

The planner is mains-only. The crawl includes desserts (cakes, koekjes, mousse,
ijs) and the odd side/snack, and those must not be planned as dinner. Derived
like the staple base -- recompute freely, never store as authoritative.

Bias: DEFAULT TO MAIN. This is a dinner-recipe corpus, so a recipe is a main
unless it trips a clear dessert or side signal. Ambiguous bakes (taart/tarte/
vlaai) are dessert UNLESS they carry savoury markers (kaas/prei/zalm/spek...),
which is how a quiche-style 'champignon-aardappeltaart' stays a main.

Eyeball it with `py courses.py` -> dumps/courses.txt, the same workflow the diet
and staple classifiers used.
"""
from collections import Counter

import config
import db
from classify import norm, deaccent, tokens

# Unambiguous sweet titles, matched as substrings (chosen to avoid savoury
# friends: 'compote' is out -- tomatencompote/uiencompote are savoury).
SWEET_SUBSTR = {
    "cake", "cheesecake", "brownie", "blondie", "cupcake", "muffin", "tiramisu",
    "bavarois", "semifreddo", "meringue", "sabayon", "frangipane", "speculaas",
    "clafoutis", "macaron", "ganache", "praline", "shortbread", "chiffon",
    "smoutebol", "biscuit", "confituur", "sorbet", "parfait", "pudding",
    "nougat", "pavlova", "panna cotta", "chiboust", "flottante", "eton mess",
    "mousse", "curd", "krispie", "wafel", "sinaascake",
}
SWEET_PREFIX = {"koekje", "gebakje", "taartje"}      # token-initial

AMBIG_BAKE = {"taart", "tarte", "vlaai"}             # savoury OR sweet
SAVOURY_MARKERS = {
    "kaas", "prei", "aardappel", "ui", "ajuin", "spek", "zalm", "ham", "vis",
    "champignon", "gehakt", "prosciutto", "spinazie", "tomaat", "courgette",
    "broccoli", "kip", "groente", "look", "mosterd", "witloof", "warmoes",
    "chorizo", "pens", "worst", "bacon", "feta", "geitenkaas", "mozzarella",
    "ei", "gerookte", "pesto",
}
# 'crumble' is savoury too (chorizocrumble, pankocrumble) -- dessert only with a
# fruity/sweet context word.
DESSERT_CONTEXT = {
    "chocolade", "karamel", "vanille", "slagroom", "suiker", "aardbei",
    "framboos", "peer", "banaan", "rabarber", "amandel", "hazelnoot", "kaneel",
    "amarena", "kers", "appel", "abrikoos", "kruidnoten",
}
SIDE_SUBSTR = {"loempia", "frietjes uit", "kroketten uit", "bitterbal",
               "smoothie", "milkshake", "cocktail", "mocktail"}


def _is_ice(tok: str) -> bool:
    return tok in {"ijs", "ijsje", "roomijs", "softijs", "schepijs"} or \
           (tok.endswith("ijs") and len(tok) > 4 and tok != "prijs")


def classify_course(title: str, ingredient_texts=()) -> str:
    t = deaccent(norm(title or ""))
    toks = tokens(t)
    joined = t + " " + deaccent(norm(" ".join(ingredient_texts or ())))

    if any(s in t for s in SWEET_SUBSTR):
        return "dessert"
    if any(_is_ice(tok) for tok in toks):
        return "dessert"
    if any(tok.startswith(p) for tok in toks for p in SWEET_PREFIX):
        return "dessert"
    if "crumble" in t and any(d in joined for d in DESSERT_CONTEXT):
        return "dessert"

    if any(b in t for b in AMBIG_BAKE):
        if any(m in joined for m in SAVOURY_MARKERS):
            return "main"
        return "dessert"

    if any(s in t for s in SIDE_SUBSTR):
        return "side"
    return "main"


# --- reporting over the db --------------------------------------------------
def by_recipe(conn):
    """Yield (recipe_id, title, course) per recipe."""
    rows = conn.execute(
        "SELECT r.id, r.title, ri.ingredient_text FROM recipes r "
        "JOIN recipe_ingredients ri ON ri.recipe_id=r.id "
        "ORDER BY r.id, ri.position").fetchall()
    cur_id = title = None
    texts = []
    for row in rows:
        if row["id"] != cur_id:
            if cur_id is not None:
                yield cur_id, title, classify_course(title or "", texts)
            cur_id, title, texts = row["id"], row["title"], []
        texts.append(row["ingredient_text"] or "")
    if cur_id is not None:
        yield cur_id, title, classify_course(title or "", texts)


def distribution(conn) -> Counter:
    c = Counter()
    for _rid, _title, course in by_recipe(conn):
        c[course] += 1
    return c


def main():
    conn = db.connect()
    db.init(conn)
    n = conn.execute("SELECT COUNT(*) c FROM recipes").fetchone()["c"]
    if not n:
        print("no recipes yet -- run crawl.py first.")
        return

    config.DUMP_DIR.mkdir(exist_ok=True)
    dump_path = config.DUMP_DIR / "courses.txt"
    dist = Counter()
    with open(dump_path, "w", encoding="utf-8") as f:
        for _rid, title, course in by_recipe(conn):
            dist[course] += 1
            f.write(f"[{course:<7}] {title}\n")

    print("=" * 60)
    print(f"COURSE distribution over {n:,} recipes")
    print("=" * 60)
    for course in ("main", "dessert", "side"):
        c = dist.get(course, 0)
        print(f"   {course:<8} {c:>5,}  {100*c/n:4.0f}%")
    print(f"\nmains are the planner pool. eyeball: {dump_path}")


if __name__ == "__main__":
    main()
