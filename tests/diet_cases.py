"""Canonical diet-classification cases.

Single source of truth: imported by both `tests/test_diet.py` and the
pre-crawl smoke check in `spike.py`. Add a case here when you find a new
compound trap in the wild -- that is the main way this lexicon improves.
"""

DIET_CASES = [
    # --- plain ---------------------------------------------------------
    ("500 g prei, in ringen gesneden", "vegan"),
    ("1 kg witloof", "vegan"),
    ("4 el olijfolie", "vegan"),

    # --- SAFE_COMPOUNDS: look animal, are not -------------------------
    ("2 vleestomaten", "vegan"),            # beefsteak TOMATO
    ("200 g eierzwammen", "vegan"),         # CHANTERELLES
    ("1 krop botersla", "vegan"),           # butterhead LETTUCE
    ("250 g boterbonen", "vegan"),          # BUTTER BEANS
    ("200 ml kokosmelk", "vegan"),          # coconut milk
    ("2 el pindakaas", "vegan"),            # peanut butter
    ("1 blokje groentebouillon", "vegan"),  # explicitly vegetable
    ("150 g wilde rijst", "vegan"),         # wild RICE
    ("2 hamburgerbroodjes", "vegan"),       # bread
    ("1 el zeewier", "vegan"),
    ("1 tl zeezout", "vegan"),

    # --- dairy / egg / honey -> vegetarian ----------------------------
    ("100 g boter", "vegetarian"),
    ("2 eieren", "vegetarian"),
    ("50 g geraspte kaas", "vegetarian"),
    ("2 bollen roomijs", "vegetarian"),
    ("kaassaus", "vegetarian"),
    ("100 g melkchocolade", "vegetarian"),
    ("1 el honing", "vegetarian"),

    # --- meat / fish -> omnivore --------------------------------------
    ("300 g gehakt", "omnivore"),
    ("4 kippenbouten", "omnivore"),         # prefix hides "kip"
    ("200 g vissticks", "omnivore"),        # prefix hides "vis"
    ("100 g runderrookvlees", "omnivore"),
    ("1 el vissaus", "omnivore"),
    ("200 g gerookte zalm", "omnivore"),
    ("6 plakjes spek", "omnivore"),

    # --- from the first live crawl (15gram / dagelijksekost / delhaize) --
    ("300 g steak", "omnivore"),            # named cut, no "vlees" stem
    ("2,5 kg entrecote", "omnivore"),
    ("chateaubriand 550 g", "omnivore"),
    ("120 g sardienen in olijfolie", "omnivore"),   # NL plural of "sardine"
    ("800 g grieten", "omnivore"),          # turbot
    ("venusschelpen 2 kg", "omnivore"),
    ("halloumi 2 blokken", "vegetarian"),   # cheese, not vegan
    ("gehakte bieslook 2 el", "vegan"),     # "chopped", NOT minced meat
    ("2 el gehakte peterselie", "vegan"),

    # --- genuinely ambiguous -> uncertain ------------------------------
    ("1 blokje bouillon", "uncertain"),
    ("2 el pesto", "uncertain"),            # classic pesto has pecorino
]
