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
    "tomaat":        ("vegetable", "tomato",         ["tomaten", "kerstomaat", "vleestomaat", "vleestomaten", "tomate", "tomates", "tomato", "tomatoes"]),
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

# --- v2 transliterated aliases ---------------------------------------------
# Romanised Hindi / Korean / Japanese / Mandarin-pinyin names for produce that
# ALREADY has a Belgian Velt canonical. Point of the v2 winter crawl is Punjabi
# /Korean/N-Chinese/Japanese cooking of Belgian winter crops, and those recipes
# name their vegetables in transliteration, not Dutch -- without this pass the
# match rate on the eastern corpus is poor (docs/vegan_sources.md, prereq #2).
#
# ONLY clean 1:1 mappings live here. Three deliberate exclusions:
#   * No Velt equivalent -> intentionally absent, will score `unknown` (skipped),
#     which is correct: bhindi/okra, karela (bitter gourd), methi (fenugreek
#     greens), gobo (burdock), taro, renkon (lotus root), drumstick.
#   * Approximations are NOT done silently (repo rule): daikon/mooli/mu/luobo ->
#     rammenas is a different vegetable in the same season/role, left out here.
#   * Ambiguous generic-cabbage words (Hindi `patta gobi`, and bare `kool`) are
#     left unmapped, same call the owner already made for `kool`: a head-cabbage
#     word that is white/savoy/pointed/red maybe a third of the time each.
# NB `gobi`/`phool gobi` = cauliflower (-> bloemkool); only `patta gobi` is the
# ambiguous cabbage one, so cauliflower is safe to map and IS mapped.
TRANSLITERATED = {
    "aubergine":    ["baingan", "baigan", "brinjal", "gaji", "nasu", "nasubi", "qiezi"],
    "bloemkool":    ["gobi", "gobhi", "phool gobi", "phoolgobi", "phool gobhi"],
    "aardappel":    ["aloo", "gamja", "jagaimo", "tudou", "malingshu"],
    "ui":           ["pyaz", "pyaaz", "yangpa", "tamanegi", "yangcong"],
    "knoflook":     ["lehsun", "lasan", "maneul", "ninniku", "dasuan"],
    "spinazie":     ["palak", "sigeumchi", "horenso", "bocai"],
    "doperwt":      ["matar", "mutter"],
    "wortel":       ["gajar", "gajor", "danggeun", "dangeun", "ninjin", "hu luobo"],
    "raap":         ["shalgam", "shaljam"],
    # unambiguous napa-cabbage terms only; bok-choy words stay on `paksoi`
    "chinese kool": ["baechu", "hakusai", "da baicai", "dabaicai"],
    "courgette":    ["ae hobak", "aehobak"],
    "pompoen":      ["kabocha", "danhobak", "nangua"],
    "tomaat":       ["xihongshi", "fanqie"],
}
for _canon, _extra in TRANSLITERATED.items():
    PRODUCE[_canon][2].extend(_extra)   # the alias list is the mutable 3rd slot


# --- v2 approximations (owner-reversible) ----------------------------------
# NOT facts, kept separate from TRANSLITERATED so the distinction stays loud.
# daikon / mooli (large white winter radish) has no Velt crop of its own. The
# closest is `rammenas` (black winter radish): same Jan-Mar/Oct-Dec window, same
# culinary role, different vegetable. The survey (docs/vegan_sources.md) calls
# this out as an owner decision -- taken here because it is what makes Japanese
# nimono, Korean muguk and Northern-Chinese daikon dishes score a WINTER signal
# instead of `unknown`, which is the whole point of the v2 crawl. To reverse:
# delete this block (they revert to unknown), or retarget these terms to
# `radijs` if you'd rather treat them as a summer radish.
APPROXIMATE = {
    # `luobo` is generic Chinese radish; `hu luobo` (carrot -> wortel) is a
    # LONGER alias, so longest-match-first keeps carrot from collapsing to radish.
    # Bare Korean `mu` is deliberately omitted -- a 2-char whole-word match is too
    # collision-prone; `korean radish` covers it safely.
    "rammenas": ["daikon", "daikon radish", "mooli", "muli", "luobo",
                 "bai luobo", "white radish", "korean radish", "rettich"],
}
for _canon, _extra in APPROXIMATE.items():
    PRODUCE[_canon][2].extend(_extra)


# --- processed "false friends" ---------------------------------------------
# Phrases that CONTAIN a produce word but are a processed pantry item, not fresh
# seasonal produce: a jar of ketchup is not a tomato in season. match_seasonal
# strips these BEFORE matching, the same strip-first idea SAFE_COMPOUNDS uses for
# the diet classifier. Only SPACED (mostly English / transliterated) forms need
# listing -- Dutch closed compounds already fail the \b word-boundary match
# (`appelmoes`, `tomatenpuree`, `knoflookpoeder` never matched `appel`/`tomaat`/
# `knoflook`). Curated on purpose: precision over recall. Genuinely-fresh
# compounds (kerstomaat, vleestomaat) are deliberately kept OUT so they still
# match. Extend as the corpus surfaces more.
NONFRESH_FORMS = {
    # tomato: concentrates, condiments, preserved -- not a fresh tomato
    "tomato ketchup", "tomato paste", "tomato puree", "tomato passata",
    "tomato concentrate", "sun dried tomato", "sun-dried tomato",
    "sundried tomato", "sun dried tomatoes", "sun-dried tomatoes",
    "sundried tomatoes",
    # apple: cider / vinegar / juice / sauce
    "apple cider vinegar", "apple cider", "apple juice", "apple sauce",
    # garlic & onion: pastes, powders, salts (aromatic, but wrong on a shop list)
    "garlic paste", "ginger garlic paste", "ginger-garlic paste",
    "garlic powder", "garlic granules", "garlic salt",
    "onion powder", "onion granules", "onion salt",
    # potato: starch / flour, not a fresh tuber
    "potato starch", "potato flour",
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
