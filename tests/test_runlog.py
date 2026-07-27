"""runlog.py: tee logging writes a file and still prints; no-op when unstarted."""
import runlog


def test_log_without_start_only_prints(capsys):
    runlog.stop()                      # ensure no file is open
    runlog.log("hello")
    assert "hello" in capsys.readouterr().out
    assert runlog._fh is None


def test_start_writes_file_and_prints(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(runlog, "LOG_DIR", tmp_path)
    p = runlog.start("crawl")
    try:
        runlog.log("SUMMARY line")
        runlog.log("recipes=500")
    finally:
        runlog.stop()

    assert p.parent == tmp_path
    assert p.name.startswith("crawl_") and p.name.endswith(".log")
    body = p.read_text(encoding="utf-8")
    assert "SUMMARY line" in body and "recipes=500" in body
    assert "SUMMARY line" in capsys.readouterr().out   # still tees to stdout


def test_stop_is_idempotent():
    runlog.stop()
    runlog.stop()          # must not raise
    assert runlog._fh is None
