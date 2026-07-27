"""Shared Dutch-compound matching primitive.

This problem has surfaced three times:
  1. 'vlees' inside 'vleestomaat', 'boter' inside 'boterbonen'  (diet lexicon)
  2. 'raap' -> 'rapen' vowel shortening                          (seasonal lexicon)
  3. 'ui' inside 'suiker', 'ijs' inside 'radijs'                 (courses.py)

staples.py and courses.py each re-derived token matching independently; one got
it right, one shipped apple tart for dinner. This module is the single home for
the primitive, so the coin flip stops.

Rules (load-bearing -- see docs/decisions.md):
  * A "false friend" exclusion set is stripped BEFORE any matching runs. That
    ordering is what stops 'boterbonen' reading as dairy -- do not reorder it.
  * A term shorter than MIN_PREFIX matches a WHOLE TOKEN only: never a prefix,
    never a raw substring ('ui' must not match inside 'suiker').
  * A term of MIN_PREFIX or longer may match word-initial, so 'aardappel'
    catches 'aardappelen'. Never lower MIN_PREFIX to catch one word -- add the
    word to the term set instead.

The diet classifier (classify.py + lexicon/animal.py) keeps its own, older
matching: it is the battle-tested reference this module was distilled from, and
its SAFE_COMPOUNDS-strip-then-prefix ordering is deliberately untouched here.
"""
import re
import unicodedata

MIN_PREFIX = 4

_WS = re.compile(r"\s+")
_TOKEN = re.compile(r"[a-zà-ÿ]+", re.IGNORECASE)


def norm(text: str) -> str:
    """Lowercase, collapse whitespace. Accents are KEPT (French needs them)."""
    return _WS.sub(" ", (text or "").lower().strip())


def deaccent(text: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFD", text)
        if unicodedata.category(c) != "Mn"
    )


def tokens(text: str):
    return _TOKEN.findall(norm(text))


def matches(token: str, term: str) -> bool:
    """Whole-token match, or word-initial for terms >= MIN_PREFIX. Never substring."""
    d = deaccent(term)
    return token == d or (len(d) >= MIN_PREFIX and token.startswith(d))


def hit(toks, terms) -> bool:
    """True if any token matches any term."""
    return any(matches(tok, term) for tok in toks for term in terms)


def strip_false_friends(text: str, exclusions) -> str:
    """Deaccent+normalise, then blank out exclusion phrases BEFORE matching.

    Returns a cleaned string; tokenise it with tokens(). Multi-word exclusions
    ('harissa pasta') work because the string is still spaced at this point.
    """
    flat = deaccent(norm(text))
    for bad in exclusions:
        if bad in flat:
            flat = flat.replace(bad, " ")
    return flat
