import pytest

from classify import parse_ingredient


@pytest.mark.parametrize(
    "raw,qty,unit,ingredient",
    [
        ("500 g prei, in ringen gesneden", 500.0, "g", "prei"),
        ("1 kg witloof", 1.0, "kg", "witloof"),
        ("1,5 kg aardappelen", 1.5, "kg", "aardappelen"),
        ("200 ml kokosmelk", 200.0, "ml", "kokosmelk"),
        ("3 teentjes knoflook", 3.0, "clove", "knoflook"),
        ("4 el olijfolie", 4.0, "tbsp", "olijfolie"),
        ("2 tl komijnpoeder", 2.0, "tsp", "komijnpoeder"),
        ("½ knolselder", 0.5, None, "knolselder"),
        ("2 uien, gesnipperd", 2.0, None, "uien"),
        # Belgian koffielepel abbreviation and spelled-out deciliter
        ("2 kl kruidenmix", 2.0, "tsp", "kruidenmix"),
        ("3 deciliter melk", 3.0, "dl", "melk"),
        # trailing quantity (Delhaize 'wild' route): amount AFTER the name
        ("bloem 25 g", 25.0, "g", "bloem"),
        ("citroen 1", 1.0, None, "citroen"),
        ("droge witte wijn 20 cl", 20.0, "cl", "droge witte wijn"),
        ("komkommer 0,3", 0.3, None, "komkommer"),   # was corrupted to "komkommer 0"
    ],
)
def test_parse_quantities(raw, qty, unit, ingredient):
    p = parse_ingredient(raw)
    assert p["qty"] == pytest.approx(qty)
    assert p["unit"] == unit
    assert p["ingredient_text"] == ingredient


def test_trailing_qty_only_when_no_leading():
    # a trailing non-unit word must not be mistaken for a quantity
    p = parse_ingredient("halloumi 2 blokken")
    assert p["qty"] is None
    assert p["ingredient_text"] == "halloumi 2 blokken"


def test_prep_note_split_on_comma():
    p = parse_ingredient("500 g prei, in ringen gesneden")
    assert p["prep_note"] == "in ringen gesneden"


def test_no_quantity_is_tolerated():
    p = parse_ingredient("snuf zout")
    assert p["qty"] is None
    assert "zout" in p["ingredient_text"]


def test_range_takes_lower_bound():
    p = parse_ingredient("2-3 el azijn")
    assert p["qty"] == pytest.approx(2.0)
    assert p["unit"] == "tbsp"


def test_empty_string_does_not_crash():
    p = parse_ingredient("")
    assert p["qty"] is None
    assert p["ingredient_text"] == ""
