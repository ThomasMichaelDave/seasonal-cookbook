"""Tee logging: everything printed also goes to a timestamped file in logs/.

Both spike.py and crawl.py route their output through log() so a long-running
crawl leaves a durable record -- the summary block, the diet breakdown, and any
sitemap failures -- instead of only scrolling past in the terminal. A run with
no file started (e.g. an import, or a unit test) just prints, exactly as before.
"""
from datetime import datetime

from config import LOG_DIR

_fh = None
_path = None


def start(prefix: str):
    """Open logs/<prefix>_<localtime>.log and tee into it. Returns the path."""
    global _fh, _path
    LOG_DIR.mkdir(exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    _path = LOG_DIR / f"{prefix}_{stamp}.log"
    _fh = open(_path, "w", encoding="utf-8")
    return _path


def log(msg=""):
    print(msg, flush=True)
    if _fh is not None:
        _fh.write(f"{msg}\n")
        _fh.flush()          # flush per line so a killed crawl still has its log


def stop():
    global _fh
    if _fh is not None:
        _fh.close()
        _fh = None


def path():
    return _path
