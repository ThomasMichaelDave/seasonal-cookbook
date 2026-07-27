"""robots.txt handling: a blocked *probe* must not ban a whole domain.

Regression for the bug where a 401/403 on the robots.txt fetch itself (a
Cloudflare/WAF challenge or a corporate proxy) made the stdlib RobotFileParser
mark the entire host disallow-all -- silently, because that path never raises.
A real Disallow body (HTTP 200) is still obeyed.

Pure: exercises fetch._robots_from_response directly, no network.
"""
import fetch
from config import USER_AGENT

ROBOTS_URL = "https://example.com/robots.txt"
PAGE = "https://example.com/recipe/x"


def setup_function(_):
    fetch._robots_warned.clear()


def rp_for(status, body):
    return fetch._robots_from_response(ROBOTS_URL, status, body)


def test_real_body_is_parsed_and_obeyed():
    rp = rp_for(200, "User-agent: *\nDisallow: /private/")
    assert rp.can_fetch(USER_AGENT, "https://example.com/public/x") is True
    assert rp.can_fetch(USER_AGENT, "https://example.com/private/x") is False


def test_sitewide_disallow_is_still_honored():
    # The politeness guarantee: an actual Disallow: / still blocks everything.
    rp = rp_for(200, "User-agent: *\nDisallow: /")
    assert rp.can_fetch(USER_AGENT, "https://example.com/anything") is False


def test_403_probe_does_not_ban_domain():
    # The bug: this used to disallow the whole host. It must not.
    rp = rp_for(403, None)
    assert rp.can_fetch(USER_AGENT, PAGE) is True


def test_401_probe_does_not_ban_domain():
    rp = rp_for(401, None)
    assert rp.can_fetch(USER_AGENT, PAGE) is True


def test_404_means_no_restrictions():
    rp = rp_for(404, None)
    assert rp.can_fetch(USER_AGENT, PAGE) is True


def test_unreachable_assumes_allowed():
    rp = rp_for(None, None)
    assert rp.can_fetch(USER_AGENT, PAGE) is True


def test_empty_200_body_falls_back_to_allowed():
    # 200 with an empty body (some CDNs do this) must not crash or block.
    rp = rp_for(200, "")
    assert rp.can_fetch(USER_AGENT, PAGE) is True


def test_403_warns_once_per_host(capsys):
    rp_for(403, None)
    first = capsys.readouterr().out
    assert "HTTP 403" in first and "UNRESTRICTED" in first
    rp_for(403, None)                       # same host, second time
    assert capsys.readouterr().out == ""    # warned once, then stays quiet
