"""Ingredient parsing, diet classification, and seasonal scoring."""
import re

from lexicon.animal import (
    SAFE_COMPOUNDS, MEAT, FISH, DAIRY, EGG, HONEY, AMBIGUOUS,
    MEAT_PREFIXES, FISH_PREFIXES, DAIRY_PREFIXES, EGG_PREFIXES,
    HONEY_PREFIXES, MIN_PREFIX,
)
from lexicon.seasonal import PRODUCE
# One tokeniser for the whole project. Re-exported here so existing
# `from classify import norm/deaccent/tokens` imports keep working.
from matching import norm, deaccent, tokens

_WS = re.compile(r"\s+")


# ---------------------------------------------------------------------------
# Quantity / unit parsing
# ---------------------------------------------------------------------------
UNITS = {
    "g": "g", "gr": "g", "gram": "g", "grammen": "g",
    "kg": "kg", "kilo": "kg",
    "ml": "ml", "cl": "cl", "dl": "dl", "deciliter": "dl", "deciliters": "dl",
    "l": "l", "liter": "l",
    "el": "tbsp", "eetlepel": "tbsp", "eetlepels": "tbsp", "tbsp": "tbsp",
    # Belgian recipes abbreviate koffielepel -> 'kl' (tsp), the partner of
    # 'el' (eetlepel -> tbsp). Without it 'kl' leaks into the ingredient text.
    "tl": "tsp", "theelepel": "tsp", "theelepels": "tsp", "koffielepel": "tsp",
    "koffielepels": "tsp", "kl": "tsp", "tsp": "tsp",
    "snuf": "pinch", "snufje": "pinch", "mespunt": "pinch",
    "teen": "clove", "teentje": "clove", "teentjes": "clove",
    "stuk": "piece", "stuks": "piece", "stuk(s)": "piece",
    "bosje": "bunch", "bos": "bunch", "handvol": "handful",
    "blikje": "can", "blik": "can", "pot": "jar", "zakje": "sachet",
}

_FRACTIONS = {"½": 0.5, "¼": 0.25, "¾": 0.75, "⅓": 1 / 3, "⅔": 2 / 3}

_QTY_RE = re.compile(
    r"^\s*(?P<qty>\d+[\.,]?\d*(?:\s*[-–/]\s*\d+[\.,]?\d*)?|[½¼¾⅓⅔])\s*"
    r"(?P<unit>[a-zà-ÿ\(\)]+)?\.?\s+",
    re.IGNORECASE,
)

# Some sources put the amount AFTER the name instead of before it. Delhaize's
# 'wild' route emits 'bloem 25 g', 'citroen 1', 'komkommer 0,3'. This matches a
# quantity (+ optional unit) anchored to the END of the string, and is only
# tried when the leading pattern above finds nothing.
_TRAIL_QTY_RE = re.compile(
    r"\s+(?P<qty>\d+\s*[-–/]\s*\d+|\d+[\.,]?\d*|[½¼¾⅓⅔])\s*"
    r"(?P<unit>[a-zà-ÿ\(\)]+)?\.?\s*$",
    re.IGNORECASE,
)


def _to_qty(raw_qty: str):
    """'2,5' -> 2.5, '½' -> 0.5, '2-3'/'1/2' -> lower bound. None if unparseable."""
    if raw_qty in _FRACTIONS:
        return _FRACTIONS[raw_qty]
    first = re.split(r"[-–/]", raw_qty)[0]
    try:
        return float(first.replace(",", "."))
    except ValueError:
        return None


def parse_ingredient(raw: str) -> dict:
    """Split '500 g prei, in ringen' -> qty/unit/ingredient/prep.

    Deliberately forgiving. The dump produced by spike.py is what tells you
    which real-world shapes still need handling -- do not tune this blind.
    """
    text = norm(raw)
    qty = unit = None

    m = _QTY_RE.match(text)
    if m:
        qty = _to_qty(m.group("qty"))
        cand = (m.group("unit") or "").strip(".()")
        if cand in UNITS:
            unit = UNITS[cand]
            text = text[m.end():]
        elif cand and qty is not None:
            # number followed by a word that is not a unit -> the word is the
            # ingredient ("2 uien"). Keep it.
            text = text[m.start("unit"):] if m.group("unit") else text[m.end():]
        else:
            text = text[m.end():]
    else:
        # No leading quantity -> try a trailing one (Delhaize-style).
        tm = _TRAIL_QTY_RE.search(text)
        if tm:
            name = text[:tm.start()].strip(" .,")
            cand = (tm.group("unit") or "").strip(".()")
            q = _to_qty(tm.group("qty"))
            # Accept only if a name survives and the trailer is a real unit or a
            # bare count ('citroen 1'). A trailing non-unit word ('2 blokken')
            # means the number probably isn't a quantity -- leave text intact.
            if name and q is not None and (cand in UNITS or not cand):
                qty, unit, text = q, UNITS.get(cand), name

    prep = None
    if "," in text:
        text, _, prep = text.partition(",")
        prep = prep.strip() or None

    return {
        "qty": qty,
        "unit": unit,
        "ingredient_text": text.strip(" .()"),
        "prep_note": prep,
    }


# ---------------------------------------------------------------------------
# Diet classification
# ---------------------------------------------------------------------------
def _phrase_hits(text: str, vocab: set) -> set:
    """Whole-word / whole-phrase matching. Never bare substring."""
    hits = set()
    padded = f" {text} "
    for term in vocab:
        t = norm(term)
        if " " in t:
            if f" {t} " in padded:
                hits.add(t)
        else:
            if re.search(rf"\b{re.escape(t)}\b", padded):
                hits.add(t)
    return hits


def _prefix_hits(text: str, prefixes: set) -> set:
    """Word-INITIAL matching, for compounds that hide the animal term:
    'kippenbouten' -> kip, 'roomijs' -> room, 'vissticks' -> vis.

    Only safe because SAFE_COMPOUNDS has already been stripped from `text`.
    """
    hits = set()
    for tok in tokens(text):
        flat = deaccent(tok)
        for p in prefixes:
            if len(p) < MIN_PREFIX:
                continue
            if flat.startswith(deaccent(p)) and len(flat) >= len(p):
                hits.add(p)
                break
    return hits


def classify_ingredient(raw: str) -> tuple[str, set]:
    """-> (verdict, evidence) where verdict is vegan|vegetarian|omnivore|uncertain."""
    text = norm(raw)
    toks = set(tokens(text))

    # 1. Safe compounds win outright. Strip them so their inner animal token
    #    ("vlees" inside "vleestomaat") can never fire below.
    safe = {t for t in toks if t in SAFE_COMPOUNDS}
    safe |= {t for t in toks if deaccent(t) in SAFE_COMPOUNDS}
    for s in safe:
        text = re.sub(rf"\b{re.escape(s)}\b", " ", text)
    # multi-word safe phrases
    for s in SAFE_COMPOUNDS:
        if " " in s and s in text:
            text = text.replace(s, " ")
    text = _WS.sub(" ", text).strip()

    if not text:
        return "vegan", set()

    meat = (_phrase_hits(text, MEAT) | _phrase_hits(text, FISH)
            | _prefix_hits(text, MEAT_PREFIXES) | _prefix_hits(text, FISH_PREFIXES))
    if meat:
        return "omnivore", meat

    animal = (_phrase_hits(text, DAIRY) | _phrase_hits(text, EGG)
              | _phrase_hits(text, HONEY) | _prefix_hits(text, DAIRY_PREFIXES)
              | _prefix_hits(text, EGG_PREFIXES) | _prefix_hits(text, HONEY_PREFIXES))
    if animal:
        return "vegetarian", animal

    amb = _phrase_hits(text, AMBIGUOUS)
    if amb:
        return "uncertain", amb

    return "vegan", set()


DIET_RANK = {"vegan": 0, "vegetarian": 1, "uncertain": 2, "omnivore": 3}


def classify_recipe(ingredient_lines) -> tuple[str, list]:
    """Worst ingredient wins. 'uncertain' outranks 'vegetarian' on purpose:
    an unidentified stock cube is a worse failure than a known knob of butter."""
    verdict, evidence = "vegan", []
    for line in ingredient_lines:
        v, ev = classify_ingredient(line)
        if ev:
            evidence.append(f"{line.strip()} -> {v} ({', '.join(sorted(ev))})")
        if DIET_RANK[v] > DIET_RANK[verdict]:
            verdict = v
    return verdict, evidence


def diet_allows(recipe_diet: str, wanted: str, allow_uncertain: bool = False) -> bool:
    """wanted in {'any','vegetarian','vegan'} -- the switch your UI exposes."""
    if wanted == "any":
        return True
    if recipe_diet == "uncertain":
        return allow_uncertain
    if wanted == "vegetarian":
        return recipe_diet in ("vegan", "vegetarian")
    if wanted == "vegan":
        return recipe_diet == "vegan"
    raise ValueError(wanted)


# ---------------------------------------------------------------------------
# Seasonal matching + scoring
# ---------------------------------------------------------------------------
def build_alias_index() -> dict:
    """alias -> canonical_nl. Longest alias wins on overlap.

    Dutch recipe writing is full of diminutives and they are not optional:
    'worteltjes', 'uitjes', 'kerstomaatjes', 'boontjes', 'aardappeltjes' are
    the NORMAL way to write these, not edge cases. Rather than enumerate them
    by hand in the lexicon, generate the forms forwards from each alias --
    forward generation can't invent a false match the base alias didn't
    already imply.

    Plurals also SHORTEN a doubled vowel that closes the stem: 'raap' -> 'rapen'
    (not 'raapen'), 'bloemkool' -> 'bloemkolen', 'pastinaak' -> 'pastinaken',
    'koolraap' -> 'koolrapen', 'aardpeer' -> 'aardperen'. Eight of the ten
    affected words are Velt crops, so plain suffix-appending was silently
    missing these on the Belgian corpus, not just prospective ones.
    """
    idx = {}

    def add(term, canon):
        t = norm(term)
        if not t:
            return
        idx.setdefault(t, canon)
        idx.setdefault(deaccent(t), canon)

    for nl, (_kind, en, aliases) in PRODUCE.items():
        for base in [nl, en, *aliases]:
            if not base:
                continue
            add(base, nl)
            if " " in base:          # don't inflect multi-word aliases
                continue
            for suffix in ("s", "en", "je", "jes", "tje", "tjes", "ke", "kes"):
                add(base + suffix, nl)
            shortened = _shorten_plural(base)
            if shortened:
                add(shortened, nl)
    return idx


# aa/ee/oo/uu closing a stem shorten to a single vowel before the plural -en:
# raap -> rapen, kool -> kolen, peer -> peren, pastinaak -> pastinaken.
_VOWEL_SHORTEN = re.compile(r"^(.*)(aa|ee|oo|uu)([bcdfghjklmnpqrstvwxz])$")


def _shorten_plural(word: str) -> str | None:
    m = _VOWEL_SHORTEN.match(word)
    if not m:
        return None
    stem, vowels, cons = m.groups()
    return f"{stem}{vowels[0]}{cons}en"


ALIAS_INDEX = build_alias_index()


def match_seasonal(ingredient_text: str) -> str | None:
    """Return canonical_nl for a seasonal item, else None.

    Longest-match-first so 'rode bes' beats 'bes' and 'knolselder' beats
    'selder'.
    """
    text = norm(ingredient_text)
    flat = deaccent(text)
    for alias in sorted(ALIAS_INDEX, key=len, reverse=True):
        if re.search(rf"\b{re.escape(alias)}\b", text) or \
           re.search(rf"\b{re.escape(alias)}\b", flat):
            return ALIAS_INDEX[alias]
    return None


# Aromatics are background in most Belgian home cooking. They are seasonal
# produce and DO belong on the grocery list, but a recipe is never "a leek
# dish" because it contains one clove of garlic. Never heroes.
AROMATICS = {"ui", "sjalot", "knoflook"}

HERO_MASS_G = 250        # grams-equivalent for "this dish is built on it"
HERO_PIECES = 2          # pieces/bunches
NON_BULK_UNITS = {"clove", "pinch", "tsp", "tbsp", "sachet"}


def _in_title(canon: str, title_norm: str) -> bool:
    names = [canon, PRODUCE[canon][1], *PRODUCE[canon][2]]
    return any(
        re.search(rf"\b{re.escape(norm(n))}", title_norm) for n in names if n
    )


def _is_bulky(ing: dict) -> bool:
    qty, unit = ing.get("qty"), ing.get("unit")
    if qty is None or unit in NON_BULK_UNITS:
        return False
    if unit == "kg":
        return qty * 1000 >= HERO_MASS_G
    if unit == "g":
        return qty >= HERO_MASS_G
    if unit in (None, "piece", "bunch"):
        return qty >= HERO_PIECES
    return False


def mark_heroes(title: str, parsed_ingredients: list) -> None:
    """Set ['is_hero'] in place, in strict order of evidence.

    A recipe is 'in season' because of what it is BUILT ON, not because it
    happens to contain an onion. So:

      1. If any non-aromatic produce appears in the TITLE, those are the
         heroes and nothing else is. The title is the strongest signal a
         recipe gives you about what it is.
      2. Otherwise, produce used in bulk (>=250 g, >=1 kg, >=3 pieces).
      3. Otherwise, fall back to the single largest produce item, so every
         recipe with any produce has at least one hero to score against.

    Position in the ingredient list is deliberately NOT used -- sites order
    ingredients by use, not by importance, and it promoted every onion.
    """
    t = norm(title or "")
    for ing in parsed_ingredients:
        ing["is_hero"] = False

    produce = [
        i for i in parsed_ingredients
        if i.get("canonical") and i["canonical"] not in AROMATICS
    ]
    if not produce:
        return

    titled = [i for i in produce if _in_title(i["canonical"], t)]
    if titled:
        for i in titled:
            i["is_hero"] = True
        return

    bulky = [i for i in produce if _is_bulky(i)]
    if bulky:
        for i in bulky:
            i["is_hero"] = True
        return

    def mass(i):
        q, u = i.get("qty") or 0, i.get("unit")
        return q * 1000 if u == "kg" else (q if u == "g" else q * 100)

    max(produce, key=mass)["is_hero"] = True


# How much a strictness level is willing to accept.
#
# `velt` is the tier the Velt Groente- en fruitkalender loads into. The printed
# calendar gives NO field/greenhouse/storage split -- it is a flat monthly list
# -- so its rows can't honestly claim a cultivation type. It therefore appears
# in all three sets, which means the strictness dial is currently INERT: with
# Velt-only data all three levels return the same answer. The dial starts
# discriminating once VLAM's gradient (or a hand-built storage overlay) adds
# rows tagged field/greenhouse/storage. See docs/velt.md.
STRICTNESS_CULTIVATION = {
    "field":      {"field", "velt"},
    "greenhouse": {"field", "greenhouse", "velt"},
    "storage":    {"field", "greenhouse", "storage", "velt"},
}

HERO_WEIGHT = 3.0
SIDE_WEIGHT = 1.0


def season_score(parsed_ingredients, month, seasonality, strictness="greenhouse"):
    """Weighted share of a recipe's seasonal produce that is available in `month`.

    seasonality: {canonical_nl: {(month, cultivation): availability}}
    Returns (score 0..1, hero_in_season bool, n_seasonal int).

    Two things are deliberately EXCLUDED from scoring rather than counted as
    out-of-season:

    1. AROMATICS (ui, sjalot, knoflook). Stored year-round and present in most
       savoury cooking, so counting them inflates every score toward "in
       season" and tells you nothing. They keep their canonical_id -- they
       belong on the grocery list -- they just don't get a vote.

    2. Produce with NO rows in `seasonality` at all. Absence of data is not
       evidence of absence: the Velt calendar doesn't list chanterelles or
       gooseberries, and penalising every recipe containing them would be
       wrong. Unknown is skipped, not scored zero. (Produce that IS in the
       calendar but absent in THIS month scores zero, correctly.)

    n == 0 means nothing in the recipe carries a usable seasonal signal. That
    is SEASON-NEUTRAL, not out of season: the planner must not filter it out.
    Pasta carbonara is a valid Tuesday in February.
    """
    allowed = STRICTNESS_CULTIVATION[strictness]
    total = got = 0.0
    n = 0
    hero_ok = True
    any_hero = False

    for ing in parsed_ingredients:
        canon = ing.get("canonical")
        if not canon or canon in AROMATICS:
            continue
        months = seasonality.get(canon)
        if not months:          # no data anywhere -> unknown, not out of season
            continue
        n += 1
        w = HERO_WEIGHT if ing.get("is_hero") else SIDE_WEIGHT
        total += w

        avail = 0
        for (m, cult), a in months.items():
            if m == month and cult in allowed:
                avail = max(avail, a)
        got += w * (avail / 3.0)

        if ing.get("is_hero"):
            any_hero = True
            if avail == 0:
                hero_ok = False

    if n == 0:
        return 0.0, False, 0
    return got / total, (hero_ok and any_hero), n
