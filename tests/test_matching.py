"""matching.py: the shared Dutch-compound primitive and its load-bearing rules."""
from matching import matches, hit, strip_false_friends, tokens, MIN_PREFIX


def test_short_term_is_whole_token_only():
    # 'ui' (< MIN_PREFIX) must NOT match inside 'suiker' -- the courses.py bug
    assert matches("ui", "ui") is True
    assert matches("uien", "ui") is False        # not a prefix for short terms
    assert matches("suiker", "ui") is False


def test_long_term_matches_word_initial():
    assert matches("aardappelen", "aardappel") is True   # >= MIN_PREFIX prefix
    assert matches("aardappel", "aardappel") is True
    assert matches("prei", "prei") is True
    assert MIN_PREFIX == 4


def test_long_term_is_still_word_initial_not_substring():
    # 'kaas' must not match in the MIDDLE of a token
    assert matches("kaas", "kaas") is True
    assert matches("pindakaas", "kaas") is False   # substring, not word-initial


def test_hit_scans_tokens():
    toks = tokens("300 g wortelen met prei")
    assert hit(toks, {"prei"}) is True
    assert hit(toks, {"wortel"}) is True           # wortelen word-initial
    assert hit(toks, {"tomaat"}) is False
    # NOTE: vowel-shortening plurals ('pastinaken' vs 'pastinaak') are NOT the
    # primitive's job -- that's classify._shorten_plural, on the seasonal lexicon.
    assert hit(["pastinaken"], {"pastinaak"}) is False


def test_strip_false_friends_runs_before_matching():
    # multi-word false friend removed before tokenising
    cleaned = strip_false_friends("1 el gochujang pasta", {"gochujang pasta"})
    assert "pasta" not in cleaned.split()
    # and a single-word one
    assert "melk" not in strip_false_friends("kokosmelk", {"kokosmelk"}).split()
