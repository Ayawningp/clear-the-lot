"""Smoke test: run app.py top to bottom against a stand-in for streamlit.

Catches errors in the data plumbing (loading, summaries, receipts, memo payload) without a browser.
It does NOT check layout; run `streamlit run app.py` for that.
"""
import os
import runpy
import sys
import types
from contextlib import contextmanager
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class Recorder:
    def __init__(self):
        self.calls = []

    def __getattr__(self, name):
        def call(*args, **kwargs):
            self.calls.append((name, args, kwargs))
            if name in ("number_input",):
                return kwargs["value"]
            if name == "checkbox":
                return kwargs.get("value", False)
            if name == "selectbox":
                return args[1][kwargs.get("index", 0)]
            if name == "button":
                return False
            if name == "tabs":
                return [_ctx() for _ in args[0]]
            if name == "columns":
                return [_ctx() for _ in range(args[0])]
            return None
        return call


@contextmanager
def _ctx():
    yield


def fake_streamlit():
    rec = Recorder()
    module = types.ModuleType("streamlit")
    module.__getattr__ = rec.__getattr__
    module.sidebar = Recorder()
    module.cache_data = lambda f: f
    module._rec = rec
    return module


def test_app_runs_on_mock_data():
    st = fake_streamlit()
    sys.modules["streamlit"] = st
    cwd = os.getcwd()
    os.chdir(ROOT)
    try:
        assert not (ROOT / "data/processed/durations.csv").exists(), "smoke test expects mock mode"
        namespace = runpy.run_path(str(ROOT / "app.py"))
    finally:
        os.chdir(cwd)
        del sys.modules["streamlit"]

    assert namespace["is_mock"] is True
    payload = namespace["payload"]
    assert payload["data_is_mock"] is True
    assert set(payload["cities"]) == {"City A (MOCK)", "City B (MOCK)"}
    written = " ".join(str(args[0]) for name, args, _ in st._rec.calls if name in ("write", "success") and args)
    assert "ASSUMPTION" in written
    errors = [args[0] for name, args, _ in st._rec.calls if name == "error"]
    assert any("MOCK DATA" in e for e in errors)
