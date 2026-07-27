"""Canonical seasonal produce + aliases.

Scope discipline: this list is intentionally SMALL. Only things that have a
Belgian season live here. Salt, flour and olive oil have no season and never
get a canonical id -- they only need fuzzy grouping on the grocery list.

KEYS MATCH VELT. The canonical key is spelled the way the Velt Groente- en
fruitkalender spells it, because Velt is the authority on what a crop is
called in a Belgian seasonal context. Where the lexicon previously used a
different spelling, that spelling survives as an alias so recipe matching is
unaffected. Renamed in the 2019-calendar reconciliation:

    bleekselder   -> bleekselderij      erwt         -> doperwt
    knolselder    -> knolselderij       maïs         -> mais
    sla           -> kropsla            champignon   -> paddenstoelen
    sperzieboon   -> prinsessenboon     spruitjes    -> spruiten
    snijbiet      -> warmoes

ONE DELIBERATE DEVIATION: Velt writes `witlof` (Netherlands spelling); the key
here stays `witloof` (Belgian spelling) because this is a Belgian project and
Belgian recipe sites write `witloof`. `witlof` is an alias, so the Velt row
still lands. This is the only place the match-Velt rule is knowingly broken.

`spitskool` was split out of `wittekool`: Velt lists them as separate crops
with different month ranges (spitskool May-Oct, wittekool Jul-Feb).

Format:  canonical_nl: (kind, name_en, [aliases across nl/fr/en])
"""

PRODUCE = {
    # --- leaf & brassica ---------------------------------------------------
    "witloof":       ("vegetable", "chicory",        ["witlof", "grondwitloof", "chicon", "chicons", "endive", "belgian endive"]),
    "roodlof":       ("vegetable", "red chicory",    ["rood witloof", "rode witloof", "roodloof", "chicon rouge"]),
    "spruiten":      ("vegetable", "brussels sprouts", ["spruitjes", "choux de bruxelles", "brussels sprout"]),
    "boerenkool":    ("vegetable", "kale",           ["kale", "chou frisé", "palmkool", "cavolo nero"]),
    "savooikool":    ("vegetable", "savoy cabbage",  ["savooiekool", "chou de milan", "savoy"]),
    "rodekool":      ("vegetable", "red cabbage",    ["rode kool", "chou rouge", "red cabbage"]),
    "wittekool":     ("vegetable", "white cabbage",  ["witte kool", "chou blanc", "white cabbage"]),
    "spitskool":     ("vegetable", "pointed cabbage", ["puntkool", "spitse kool", "chou pointu"]),
    "chinese kool":  ("vegetable", "chinese cabbage", ["chinakool", "pe-tsai", "chou chinois", "napa cabbage"]),
    "paksoi":        ("vegetable", "pak choi",       ["pak choi", "paksoy", "paksoï", "bok choy", "pak-choi"]),
    "bloemkool":     ("vegetable", "cauliflower",    ["chou-fleur", "cauliflower"]),
    "broccoli":      ("vegetable", "broccoli",       ["brocoli"]),
    "koolrabi":      ("vegetable", "kohlrabi",       ["chou-rave", "kohlrabi"]),
    "spinazie":      ("vegetable", "spinach",        ["épinards", "epinards", "spinach"]),
    "warmoes":       ("vegetable", "chard",          ["snijbiet", "snijbietjes", "bette", "blette", "swiss chard"]),
    "andijvie":      ("vegetable", "escarole",       ["scarole", "escarole"]),
    "veldsla":       ("vegetable", "lamb's lettuce", ["mâche", "mache", "lamb's lettuce", "corn salad"]),
    "kropsla":       ("vegetable", "lettuce",        ["sla", "botersla", "ijsbergsla", "laitue", "lettuce"]),
    "rucola":        ("vegetable", "rocket",         ["roquette", "rocket", "arugula"]),
    "postelein":     ("vegetable", "purslane",       ["pourpier", "purslane", "zomerpostelein"]),
    "winterpostelein": ("vegetable", "winter purslane", ["claytonia", "witte winterpostelein", "pourpier d'hiver"]),
    "waterkers":     ("vegetable", "watercress",     ["cresson", "watercress"]),

    # --- root & tuber ------------------------------------------------------
    "wortel":        ("vegetable", "carrot",         ["wortelen", "worteltjes", "carotte", "carottes", "carrot", "carrots"]),
    "knolselderij":  ("vegetable", "celeriac",       ["knolselder", "céleri-rave", "celeri-rave", "celeriac"]),
    "pastinaak":     ("vegetable", "parsnip",        ["panais", "parsnip"]),
    "schorseneer":   ("vegetable", "salsify",        ["schorseneren", "salsifis", "salsify"]),
    "rode biet":     ("vegetable", "beetroot",       ["biet", "bieten", "rodebiet", "betterave", "beetroot", "beet"]),
    "raap":          ("vegetable", "turnip",         ["meiraap", "navet", "turnip"]),
    "raapsteel":     ("vegetable", "turnip greens",  ["raapstelen", "raapsteeltjes", "fanes de navet"]),
    "koolraap":      ("vegetable", "swede",          ["rutabaga", "swede"]),
    "rammenas":      ("vegetable", "black radish",   ["radis noir", "black radish", "winterradijs"]),
    "radijs":        ("vegetable", "radish",         ["radis", "radish"]),
    "aardappel":     ("vegetable", "potato",         ["patat", "pomme de terre", "pommes de terre", "potato", "potatoes"]),
    "aardpeer":      ("vegetable", "jerusalem artichoke", ["topinambour", "topinamboer", "jeruzalemartisjok", "sunchoke"]),
    "ui":            ("vegetable", "onion",          ["uien", "oignon", "oignons", "onion", "onions"]),
    "sjalot":        ("vegetable", "shallot",        ["sjalotten", "échalote", "echalote", "shallot"]),
    "knoflook":      ("vegetable", "garlic",         ["look", "ail", "garlic", "teentje knoflook"]),
    "prei":          ("vegetable", "leek",           ["poireau", "poireaux", "leek", "leeks"]),

    # --- fruiting & summer -------------------------------------------------
    "tomaat":        ("vegetable", "tomato",         ["tomaten", "kerstomaat", "vleestomaat", "vleestomaten", "tomate", "tomates", "tomato"]),
    "komkommer":     ("vegetable", "cucumber",       ["concombre", "cucumber"]),
    "courgette":     ("vegetable", "courgette",      ["zucchini"]),
    "aubergine":     ("vegetable", "aubergine",      ["eggplant"]),
    "paprika":       ("vegetable", "bell pepper",    ["poivron", "poivrons", "bell pepper"]),
    "pompoen":       ("vegetable", "pumpkin",        ["butternut", "flespompoen", "potiron", "courge", "pumpkin", "squash"]),
    "mais":          ("vegetable", "sweetcorn",      ["maïs", "maiskolf", "suikermais", "sweetcorn", "corn"]),

    # --- pods & stems ------------------------------------------------------
    "asperge":       ("vegetable", "asparagus",      ["asperges", "witte asperges", "groene asperges", "asparagus"]),
    "doperwt":       ("vegetable", "pea",            ["erwt", "erwten", "doperwten", "petits pois", "pois", "pea", "peas"]),
    "peultjes":      ("vegetable", "mangetout",      ["peul", "mangetout", "sugar snap", "sugarsnaps"]),
    "prinsessenboon": ("vegetable", "green bean",    ["sperzieboon", "sperziebonen", "prinsessenbonen", "haricot vert", "haricots verts", "green beans", "boontjes"]),
    "snijboon":      ("vegetable", "runner bean",    ["snijbonen", "runner bean"]),
    "tuinboon":      ("vegetable", "broad bean",     ["tuinbonen", "fève", "feves", "broad bean", "fava"]),
    "bleekselderij": ("vegetable", "celery",         ["bleekselder", "selder", "céleri", "celery"]),
    "groene selderij": ("vegetable", "leaf celery",  ["snijselder", "snijselderij", "bladselderij", "groene selder", "céleri à couper"]),
    "venkel":        ("vegetable", "fennel",         ["fenouil", "fennel"]),
    "artisjok":      ("vegetable", "artichoke",      ["artisjokken", "artichaut", "artichoke"]),
    "rabarber":      ("vegetable", "rhubarb",        ["rhubarbe", "rhubarb"]),

    # --- fungi -------------------------------------------------------------
    "paddenstoelen": ("vegetable", "mushroom",       ["champignon", "champignons", "paddenstoel", "champignon de paris", "mushroom", "mushrooms"]),
    "eierzwam":      ("vegetable", "chanterelle",    ["eierzwammen", "cantharel", "cantharellen", "girolle", "chanterelle"]),

    # --- fruit -------------------------------------------------------------
    "appel":         ("fruit", "apple",              ["appels", "appelen", "pomme", "pommes", "apple", "apples"]),
    "peer":          ("fruit", "pear",               ["peren", "poire", "poires", "pear", "pears"]),
    "aardbei":       ("fruit", "strawberry",         ["aardbeien", "fraise", "fraises", "strawberry", "strawberries"]),
    "kers":          ("fruit", "cherry",             ["kersen", "cerise", "cerises", "cherry", "cherries"]),
    "pruim":         ("fruit", "plum",               ["pruimen", "prune", "prunes", "plum", "plums"]),
    "abrikoos":      ("fruit", "apricot",            ["abrikozen", "abricot", "abricots", "apricot"]),
    "perzik":        ("fruit", "peach",              ["perziken", "pêche", "peche", "peach", "peaches"]),
    "nectarine":     ("fruit", "nectarine",          ["nectarines"]),
    "vijg":          ("fruit", "fig",                ["vijgen", "figue", "figues", "fig", "figs"]),
    "meloen":        ("fruit", "melon",              ["meloenen", "galiameloen", "cantaloupe", "melon"]),
    "framboos":      ("fruit", "raspberry",          ["frambozen", "framboise", "framboises", "raspberry", "raspberries"]),
    "braam":         ("fruit", "blackberry",         ["bramen", "mûre", "mures", "blackberry", "blackberries"]),
    "rode bes":      ("fruit", "redcurrant",         ["rode bessen", "aalbes", "aalbessen", "groseille", "redcurrant"]),
    "zwarte bes":    ("fruit", "blackcurrant",       ["zwarte bessen", "cassis", "blackcurrant"]),
    "kruisbes":      ("fruit", "gooseberry",         ["kruisbessen", "groseille à maquereau", "gooseberry"]),
    "blauwe bes":    ("fruit", "blueberry",          ["blauwe bessen", "bosbes", "bosbessen", "myrtille", "blueberry"]),
    "kiwibes":       ("fruit", "hardy kiwi",         ["kiwibessen", "kiwiberry", "mini-kiwi"]),
    "druif":         ("fruit", "grape",              ["druiven", "raisin", "raisins", "grape", "grapes"]),
    "kweepeer":      ("fruit", "quince",             ["kwee", "coing", "quince"]),
}

# Lexicon entries the Velt 2019 calendar does NOT list. They still match in
# recipes; they simply have no seasonality rows, and season_score treats
# "no data" as UNKNOWN (skipped), never as out-of-season.
NOT_IN_VELT = {
    "eierzwam",    # Velt has only the generic 'paddenstoelen'
    "knoflook",    # aromatic, excluded from scoring anyway
    "sjalot",      # aromatic
    "kruisbes",
    "kweepeer",
    "postelein",   # Velt lists only winterpostelein
    "rucola",
}


def rows():
    """Yield (canonical_nl, kind, name_en, [(alias, lang), ...])."""
    for nl, (kind, en, aliases) in PRODUCE.items():
        pairs = [(nl, "nl"), (en, "en")]
        for a in aliases:
            # crude language guess; good enough for lookup, and the alias table
            # is keyed on (alias, lang) so a term can exist in two languages
            lang = "fr" if any(c in a for c in "éèêàçûô") else "nl"
            pairs.append((a, lang))
        yield nl, kind, en, pairs
