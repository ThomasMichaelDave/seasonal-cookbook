"""check_source.py: the pure assess() core, against the parser fixtures."""
from pathlib import Path

import check_source

FIXTURES = Path(__file__).parent / "fixtures"


def load(name):
    return (FIXTURES / name).read_text(encoding="utf-8")


def test_assess_jsonld_page_is_scrapable():
    a = check_source.assess("https://unknown-site.example/recept/x", load("jsonld_recipe.html"))
    assert a["ok"] is True
    assert a["n_ingredients"] == 7
    assert a["jsonld"] is True
    assert a["native"] is False
    assert a["route"] in ("wild", "jsonld")          # schema.org page


def test_assess_nextdata_page_route():
    a = check_source.assess("https://unknown-site.example/nl/recept/y", load("nextdata_recipe.html"))
    assert a["ok"] is True and a["route"] == "nextdata"
    assert a["nextdata"] is True and a["n_ingredients"] == 6


def test_assess_junk_is_not_scrapable():
    a = check_source.assess("https://x.example/x", "<html><body>geen recept</body></html>")
    assert a["ok"] is False and a["route"] is None and a["n_ingredients"] == 0


def test_assess_native_flag_from_url():
    # no HTML needed to know a host has a native scraper
    assert check_source.assess("https://15gram.be/recepten/x", "")["native"] is True
    assert check_source.assess("https://www.delhaize.be/nl/recept/x", "")["native"] is False


def test_host_of_strips_www():
    assert check_source.host_of("https://www.plantyou.com/recipe/x") == "plantyou.com"
    assert check_source.host_of("https://15gram.be/recepten/x") == "15gram.be"
