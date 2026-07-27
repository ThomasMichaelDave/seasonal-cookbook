import pytest

from classify import classify_ingredient, classify_recipe, diet_allows
from tests.diet_cases import DIET_CASES


@pytest.mark.parametrize("text,expected", DIET_CASES)
def test_classify_ingredient(text, expected):
    got, evidence = classify_ingredient(text)
    assert got == expected, f"{text!r} -> {got} (evidence: {sorted(evidence)})"


def test_recipe_takes_worst_ingredient():
    verdict, evidence = classify_recipe(["500 g prei", "100 g boter", "300 g gehakt"])
    assert verdict == "omnivore"
    assert evidence


def test_uncertain_outranks_vegetarian():
    """An unidentified bouillon cube is a worse failure than known butter."""
    verdict, _ = classify_recipe(["100 g boter", "1 blokje bouillon"])
    assert verdict == "uncertain"


def test_all_vegan_recipe():
    verdict, _ = classify_recipe(["500 g prei", "2 vleestomaten", "4 el olijfolie"])
    assert verdict == "vegan"


@pytest.mark.parametrize(
    "recipe_diet,wanted,allow_uncertain,expected",
    [
        ("vegan", "vegan", False, True),
        ("vegetarian", "vegan", False, False),
        ("vegetarian", "vegetarian", False, True),
        ("vegan", "vegetarian", False, True),
        ("omnivore", "vegetarian", False, False),
        ("omnivore", "any", False, True),
        ("uncertain", "vegetarian", False, False),
        ("uncertain", "vegetarian", True, True),
        ("uncertain", "any", False, True),
    ],
)
def test_diet_allows(recipe_diet, wanted, allow_uncertain, expected):
    assert diet_allows(recipe_diet, wanted, allow_uncertain) is expected


def test_diet_allows_rejects_unknown_filter():
    with pytest.raises(ValueError):
        diet_allows("vegan", "pescatarian")
