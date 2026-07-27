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
    ("200 gr volkoren spaghetti", "pasta"),
    ("150 gr udon noedels", "pasta"),
    ("125 gr volkoren orzo", "pasta"),
    ("2 stuks naanbrood", "bread"),
    ("6 miniwraps", "bread"),
    ("torti'wraps (20 cm diameter) 8", "bread"),
    # traps: contain a staple stem but are not that staple
    ("200 ml rijstmelk", None),
    ("1 el paneermeel", None),
    ("25 gr panko", None),
    ("150 g rijstnoedels", "pasta"),      # rice noodles are pasta, not rice
    # non-staples
    ("1 courgette", None),
    ("zout", None),
])
def test_staple_of_text(text, base):
    assert staple_of_text(text) == base


def test_title_wins():
    ings = [{"ingredient_text": "krielaardappelen", "qty": 400, "unit": "g"}]
    # potato in the pan, but the dish declares itself pasta in the title
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
