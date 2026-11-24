"""Regression tests against the actual London exporter and publisher."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import export_london
import publish_london


def test_tuesday_sized_payload_preserves_budget_and_cap():
    check = export_london.compact_size_check
    assert check({"candidate": b"x" * 26_891_167})["passed"]
    maximum = export_london.MAX_COMPACT_BUNDLE_BYTES
    assert check({"candidate": b"x" * (maximum - 1)})["passed"]
    assert not check({"candidate": b"x" * maximum})["passed"]


def test_index_links_to_existing_analysis_document():
    result = export_london.reading_index(["XAUUSD", "EURUSD"])
    assert "[EURUSD](instruments/EURUSD/analysis.md)" in result
    assert result.index("EURUSD") < result.index("XAUUSD")


def test_publisher_refuses_unrelated_preexisting_staging(monkeypatch, tmp_path):
    commands = []

    def run(cmd, **kwargs):
        commands.append(cmd)
        return "example.py.backup\0" if "diff" in cmd else ""

    monkeypatch.setattr(publish_london, "run", run)
    with pytest.raises(RuntimeError, match="fuera"):
        publish_london.push_paths(tmp_path, ["example.py"], "synthetic")
    assert not any("add" in cmd or "push" in cmd for cmd in commands)


def test_publisher_refuses_unrelated_local_commits(monkeypatch, tmp_path):
    commands = []

    def run(cmd, **kwargs):
        commands.append(cmd)
        if "rev-parse" in cmd:
            return "111\n"
        if "ls-remote" in cmd:
            return "222\trefs/heads/main\n"
        return ""

    monkeypatch.setattr(publish_london, "run", run)
    with pytest.raises(RuntimeError, match="commits ajenos"):
        publish_london.push_paths(tmp_path, ["example.py"], "synthetic")
    assert not any("add" in cmd or "push" in cmd for cmd in commands)
