"""Parser route tests. No network: fixtures only.

If you need a fixture for a real site, save one page of already-cached HTML
from `pages` -- do not fetch fresh pages to make a test pass.
"""
from pathlib import Path

import pytest

from parse import (
    parse_recipe, via_jsonld, via_nextdata, has_native_scraper, _minutes, _servings,
)

FIXTURES = Path(__file__).parent / "fixtures"


def load(name):
    return (FIXTURES / name).read_text(encoding="utf-8")


# --- JSON-LD ---------------------------------------------------------------
def test_jsonld_finds_recipe_nested_in_graph():
    out = via_jsonld(load("jsonld_recipe.html"), "https://example.be/recept/x")
    assert out is not None
    assert out["parser"] == "jsonld"
    assert out["title"] == "Stoofpotje van witloof en prei"
    assert len(out["ingredients"]) == 7
    assert out["ingredients"][0].startswith("500 g prei")


def test_jsonld_parses_iso_duration_and_yield():
    out = via_jsonld(load("jsonld_recipe.html"), "https://example.be/recept/x")
    assert out["total_min"] == 75
    assert out["servings"] == 4


# --- __NEXT_DATA__ ---------------------------------------------------------
def test_nextdata_finds_buried_ingredients():
    out = via_nextdata(load("nextdata_recipe.html"), "https://example.be/nl/recept/y")
    assert out is not None
    assert out["parser"] == "nextdata"
    assert out["title"] == "Zomerse ratatouille"
    assert len(out["ingredients"]) == 6


def test_nextdata_stringifies_structured_ingredients():
    out = via_nextdata(load("nextdata_recipe.html"), "https://example.be/nl/recept/y")
    assert out["ingredients"][0] == "2 courgettes"
    assert out["ingredients"][-1] == "4 el olijfolie"


def test_nextdata_returns_none_without_the_blob():
    assert via_nextdata("<html><body>nothing</body></html>", "https://x.be") is None


# --- orchestration ---------------------------------------------------------
def test_parse_recipe_falls_through_to_jsonld():
    out = parse_recipe(load("jsonld_recipe.html"), "https://unknown-site.example/recept/x")
    assert out is not None
    assert out["ingredients"]
    assert out.get("parser_version")


def test_parse_recipe_falls_through_to_nextdata():
    out = parse_recipe(load("nextdata_recipe.html"), "https://unknown-site.example/nl/recept/y")
    assert out is not None
    assert len(out["ingredients"]) == 6


def test_parse_recipe_returns_none_on_junk():
    assert parse_recipe("<html><body><p>geen recept</p></body></html>",
                        "https://unknown-site.example/x") is None


# --- native scraper availability ------------------------------------------
@pytest.mark.parametrize(
    "url,expected",
    [
        ("https://15gram.be/recepten/iets", True),
        ("https://dagelijksekost.vrt.be/gerechten/iets", True),
        ("https://www.marmiton.org/recettes/x", True),
        ("https://www.bbcgoodfood.com/recipes/x", True),
        ("https://www.delhaize.be/nl/recepten/x", False),
    ],
)
def test_native_scraper_presence(url, expected):
    """Delhaize is the only v1 source without one. If this flips, simplify."""
    assert has_native_scraper(url) is expected


# --- helpers ---------------------------------------------------------------
@pytest.mark.parametrize(
    "value,expected",
    [("PT1H15M", 75), ("PT30M", 30), ("PT2H", 120), (45, 45), ("45 min", 45), (None, None)],
)
def test_minutes(value, expected):
    assert _minutes(value) == expected


@pytest.mark.parametrize(
    "value,expected",
    [("4 personen", 4), ("serves 6", 6), (4, 4), (None, None), ("veel", None)],
)
def test_servings(value, expected):
    assert _servings(value) == expected
