"""config.py: contact address comes from the environment, not the tracked file."""
import importlib

import config


def test_contact_defaults_to_placeholder(monkeypatch):
    monkeypatch.delenv("COOKBOOK_CONTACT", raising=False)
    cfg = importlib.reload(config)
    try:
        assert cfg.CONTACT_IS_PLACEHOLDER is True
        assert cfg.CONTACT in cfg.USER_AGENT
    finally:
        importlib.reload(config)          # restore module state for other tests


def test_contact_read_from_env(monkeypatch):
    monkeypatch.setenv("COOKBOOK_CONTACT", "me@example.be")
    cfg = importlib.reload(config)
    try:
        assert cfg.CONTACT == "me@example.be"
        assert cfg.CONTACT_IS_PLACEHOLDER is False
        assert "me@example.be" in cfg.USER_AGENT
    finally:
        monkeypatch.delenv("COOKBOOK_CONTACT", raising=False)
        importlib.reload(config)
