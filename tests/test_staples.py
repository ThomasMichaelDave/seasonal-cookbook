"""staples.py: staple-base detection against real strings from the crawl."""
import pytest

from staples import staple_of_text, classify_staple


@pytest.mark.parametrize("text,base", [
    ("400 gr vastkokende aardappelen", "potato"),
    ("400 gr krielaardappelen", "potato"),
    ("400 g zoete aardappel", "potato"),
    ("125 gr witte basmati rijst", "rice"),
    ("125 g volkoren rijst", "rice"),
    ("125 gr couscous", "grain"),
    ("150 g parelcouscous", "grain"),           # pearl couscous, was missed
    ("100 g bulgur", "grain"),
    ("200 gr volkoren spaghetti", "pasta"),
    ("150 gr udon noedels", "pasta"),
    ("125 gr volkoren orzo", "pasta"),
    ("200 g orecchiette", "pasta"),             # newly added shapes
    ("200 g spirelli", "pasta"),
    ("200 g casarecce", "pasta"),
    ("2 stuks naanbrood", "bread"),
    ("6 miniwraps", "bread"),
    ("torti'wraps (20 cm diameter) 8", "bread"),
    # traps: contain a staple stem but are not that staple
    ("200 ml rijstmelk", None),
    ("1 el paneermeel", None),
    ("25 gr panko", None),
    ("150 g rijstnoedels", "pasta"),            # rice noodles are pasta, not rice
    ("1 el gochujang pasta", None),             # a CONDIMENT, not noodles
    ("2 el miso pasta", None),
    ("1 el harissa pasta", None),
    ("2 kl spaghettikruiden", None),            # a spice mix, not pasta
    # non-staples
    ("1 courgette", None),
    ("zout", None),
])
def test_staple_of_text(text, base):
    assert staple_of_text(text) == base


def test_title_wins():
    ings = [{"ingredient_text": "krielaardappelen", "qty": 400, "unit": "g"}]
    assert classify_staple("Pasta arrabiata met kip", ings) == "pasta"


def test_bulk_decides_without_title_staple():
    ings = [
        {"ingredient_text": "krielaardappelen", "qty": 400, "unit": "g"},
        {"ingredient_text": "naanbrood", "qty": 1, "unit": "piece"},
    ]
    assert classify_staple("Griekse traybake met kip", ings) == "potato"


def test_no_staple_is_none():
    ings = [{"ingredient_text": "zoete uien", "qty": 550, "unit": "g"},
            {"ingredient_text": "sinaasappel", "qty": 4, "unit": None}]
    assert classify_staple("Slaatje van zoete uien", ings) is None


# --- fixes driven by the first staples.txt dump ----------------------------
def test_burger_title_is_bread():
    # a meat burger has no bun ingredient -- the title carries the base
    assert classify_staple("Rundsburger campagnard met spekjes en ui", []) == "bread"
    assert classify_staple("Chicken burger met kimchi mayo", []) == "bread"


def test_pizza_title_is_bread():
    assert classify_staple("Pompoenpizza met gehakt en boerenkool", []) == "bread"
    assert classify_staple("Pizza met gele courgette en ricotta", []) == "bread"


def test_side_bread_is_not_the_base():
    # a bread roll served with a stew/salad is a side, not the base
    stew = [{"ingredient_text": "panini broodjes", "qty": 2, "unit": "piece"}]
    assert classify_staple("Gentse waterzooi met kip en lookbroodjes", stew) is None
    salad = [{"ingredient_text": "panini broodjes", "qty": 2, "unit": "piece"}]
    assert classify_staple("Salade niçoise met tonijn en croutons", salad) is None
    # 'brood' AFTER 'met' in the title is a side, not the dish
    soup = [{"ingredient_text": "stokbroodjes", "qty": 2, "unit": "piece"}]
    assert classify_staple("Gentse waterzooi met vis en knapperig brood", soup) is None


def test_broodje_sandwich_title_is_bread():
    ings = [{"ingredient_text": "panini broodjes", "qty": 1, "unit": "piece"}]
    assert classify_staple("Broodje kip met tomaat", ings) == "bread"


def test_vleesbroodje_with_potato_is_potato_not_bread():
    # 'vleesbroodje' is meatloaf, not a sandwich; the krieltjes are the base
    ings = [{"ingredient_text": "krieltjes", "qty": 300, "unit": "g"}]
    assert classify_staple("Vleesbroodje met crushed krieltjes", ings) == "potato"


def test_parelcouscous_title_is_grain():
    ings = [{"ingredient_text": "parelcouscous", "qty": 100, "unit": "g"}]
    assert classify_staple("Parelcouscous met chorizo en tzatziki", ings) == "grain"


def test_sandwich_is_bread_but_sushi_sandwich_is_rice():
    assert classify_staple("Pork sandwich met uiensaus en witte kool", []) == "bread"
    assert classify_staple("Komkommersandwich met geitenkaas", []) == "bread"
    # 'sushi' resolves to rice before 'sandwich' is considered
    ings = [{"ingredient_text": "gekookte sushirijst", "qty": 150, "unit": "g"}]
    assert classify_staple("Sushi sandwich", ings) == "rice"
