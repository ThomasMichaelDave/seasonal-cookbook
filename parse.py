"""Parsing, in descending order of preference.

  1. recipe_scrapers with a NATIVE scraper  -- 15gram.be, dagelijksekost.vrt.be
  2. recipe_scrapers wild_mode              -- generic schema.org
  3. raw JSON-LD                            -- when wild_mode chokes
  4. Next.js __NEXT_DATA__ blob             -- Delhaize's likely route

Every result records which route worked, so the spike report tells you exactly
where you need custom code and where you don't.
"""
import json
import re

from bs4 import BeautifulSoup
from recipe_scrapers import scrape_html, SCRAPERS
from recipe_scrapers.__version__ import __version__ as RS_VERSION

ISO_DUR = re.compile(r"P(?:\d+D)?T?(?:(\d+)H)?(?:(\d+)M)?")


def _minutes(value):
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return int(value)
    m = ISO_DUR.match(str(value))
    if m and any(m.groups()):
        h, mi = m.group(1), m.group(2)
        return int(h or 0) * 60 + int(mi or 0)
    digits = re.findall(r"\d+", str(value))
    return int(digits[0]) if digits else None


def _servings(value):
    if value is None:
        return None
    digits = re.findall(r"\d+", str(value))
    return int(digits[0]) if digits else None


def _instructions_text(value):
    """Normalise instructions (str | list | HowToStep/HowToSection dicts) to text.

    recipe_scrapers already returns a newline-joined string; JSON-LD's
    recipeInstructions can be a string, a list of strings, or a list of
    {@type: HowToStep|HowToSection, text|itemListElement}. Flatten to plain text.
    """
    if not value:
        return None
    if isinstance(value, str):
        return value.strip() or None
    parts = []
    if isinstance(value, list):
        for item in value:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict):
                if isinstance(item.get("text"), str):
                    parts.append(item["text"])
                for sub in item.get("itemListElement") or []:
                    if isinstance(sub, str):
                        parts.append(sub)
                    elif isinstance(sub, dict) and isinstance(sub.get("text"), str):
                        parts.append(sub["text"])
    cleaned = [p.strip() for p in parts if p and p.strip()]
    return "\n".join(cleaned) or None


def has_native_scraper(url: str) -> bool:
    host = re.sub(r"^https?://", "", url).split("/")[0].lower()
    host = host[4:] if host.startswith("www.") else host
    return host in SCRAPERS


# --- route 1 & 2 ------------------------------------------------------------
def via_recipe_scrapers(html: str, url: str, wild: bool):
    try:
        # recipe-scrapers deprecated `wild_mode` in favour of `supported_only`.
        # Try the modern spelling, fall back for older pinned versions.
        try:
            s = scrape_html(html, org_url=url, supported_only=not wild)
        except TypeError:
            s = scrape_html(html, org_url=url, wild_mode=wild)
        ingredients = s.ingredients()
        if not ingredients:
            return None
        try:
            instructions = s.instructions()
        except Exception:
            instructions = None
        return {
            "title": s.title(),
            "ingredients": ingredients,
            "total_min": _minutes(_safe(s.total_time)),
            "servings": _servings(_safe(s.yields)),
            "instructions": instructions,
            "parser": "recipe_scrapers" if not wild else "wild",
        }
    except Exception:
        return None


def _safe(fn):
    try:
        return fn()
    except Exception:
        return None


# --- route 3 ----------------------------------------------------------------
def _walk_for_recipe(node):
    """Find any dict with @type Recipe, at any depth, including @graph."""
    if isinstance(node, dict):
        t = node.get("@type")
        types = t if isinstance(t, list) else [t]
        if any(str(x).lower() == "recipe" for x in types if x):
            return node
        for v in node.values():
            found = _walk_for_recipe(v)
            if found:
                return found
    elif isinstance(node, list):
        for v in node:
            found = _walk_for_recipe(v)
            if found:
                return found
    return None


def via_jsonld(html: str, url: str):
    soup = BeautifulSoup(html, "lxml")
    for tag in soup.find_all("script", type="application/ld+json"):
        raw = tag.string or tag.get_text() or ""
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            try:
                data = json.loads(re.sub(r",\s*([}\]])", r"\1", raw))
            except Exception:
                continue
        node = _walk_for_recipe(data)
        if not node:
            continue
        ings = node.get("recipeIngredient") or node.get("ingredients") or []
        if isinstance(ings, str):
            ings = [ings]
        if not ings:
            continue
        return {
            "title": node.get("name"),
            "ingredients": [str(i) for i in ings],
            "total_min": _minutes(node.get("totalTime") or node.get("cookTime")),
            "servings": _servings(node.get("recipeYield")),
            "instructions": node.get("recipeInstructions"),
            "parser": "jsonld",
        }
    return None


# --- route 4 ----------------------------------------------------------------
INGREDIENT_KEYS = ("ingredient", "ingredients", "recipeIngredient", "ingredienten")


def _walk_for_ingredients(node, depth=0):
    """Next.js payloads bury the recipe somewhere in props.pageProps.*"""
    if depth > 12:
        return None
    if isinstance(node, dict):
        for k, v in node.items():
            if k in INGREDIENT_KEYS and isinstance(v, list) and v:
                return node
        for v in node.values():
            found = _walk_for_ingredients(v, depth + 1)
            if found:
                return found
    elif isinstance(node, list):
        for v in node:
            found = _walk_for_ingredients(v, depth + 1)
            if found:
                return found
    return None


def _stringify_ingredient(item):
    if isinstance(item, str):
        return item
    if isinstance(item, dict):
        for key in ("text", "name", "label", "description", "title", "raw"):
            if isinstance(item.get(key), str):
                qty, unit = item.get("quantity"), item.get("unit")
                bits = [str(b) for b in (qty, unit, item[key]) if b]
                return " ".join(bits)
    return None


def via_nextdata(html: str, url: str):
    soup = BeautifulSoup(html, "lxml")
    tag = soup.find("script", id="__NEXT_DATA__")
    if not tag:
        return None
    try:
        data = json.loads(tag.string or tag.get_text())
    except Exception:
        return None

    node = _walk_for_ingredients(data)
    if not node:
        return None
    raw_list = next(
        (node[k] for k in INGREDIENT_KEYS if isinstance(node.get(k), list) and node[k]),
        [],
    )
    ings = [s for s in (_stringify_ingredient(i) for i in raw_list) if s]
    if not ings:
        return None
    return {
        "title": node.get("title") or node.get("name"),
        "ingredients": ings,
        "total_min": _minutes(node.get("totalTime") or node.get("preparationTime")),
        "servings": _servings(node.get("servings") or node.get("yield")),
        "instructions": None,
        "parser": "nextdata",
    }


# --- orchestration ----------------------------------------------------------
def parse_recipe(html: str, url: str) -> dict | None:
    """Try every route; return the first that yields ingredients."""
    routes = []
    if has_native_scraper(url):
        routes.append(lambda: via_recipe_scrapers(html, url, wild=False))
    routes += [
        lambda: via_recipe_scrapers(html, url, wild=True),
        lambda: via_jsonld(html, url),
        lambda: via_nextdata(html, url),
    ]
    for route in routes:
        out = route()
        if out and out.get("ingredients"):
            out["parser_version"] = RS_VERSION
            out["instructions"] = _instructions_text(out.get("instructions"))
            return out
    return None
