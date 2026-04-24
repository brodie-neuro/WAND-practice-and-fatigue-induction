"""
Tests/test_response_keys.py

Regression tests for configurable N-back response keys.
"""

import os
import random
import string
import sys
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from wand_nback import common as wand_common


def _generate_seeded_custom_keys():
    """Generate reproducible non-default response keys for headless tests."""
    rng = random.Random(20260417)
    pool = [char for char in string.ascii_lowercase if char not in {"z", "m"}]
    return tuple(rng.sample(pool, 2))


class _FakeClock:
    """Minimal deterministic clock for collect_trial_response tests."""

    def __init__(self):
        self._times = iter([0.0, 0.01, 0.02, 0.5, 1.1])
        self._last = 1.1

    def getTime(self):
        try:
            self._last = next(self._times)
        except StopIteration:
            pass
        return self._last


def _run_headless_trial(monkeypatch, simulated_key, response_map):
    """Run one headless response-collection loop with a simulated keypress."""
    key_calls = []

    def fake_get_keys(keyList=None, *args, **kwargs):
        key_calls.append(list(keyList or []))
        return [simulated_key] if len(key_calls) == 1 else []

    monkeypatch.setattr(wand_common.event, "getKeys", fake_get_keys)
    monkeypatch.setattr(wand_common.core, "Clock", _FakeClock)
    monkeypatch.setattr(wand_common.core, "wait", lambda *_args, **_kwargs: None)

    response, rt = wand_common.collect_trial_response(
        win=MagicMock(),
        duration=1.0,
        response_map=response_map,
        stop_on_response=True,
    )

    return response, rt, key_calls


def test_get_response_map_bool_uses_defaults(monkeypatch):
    monkeypatch.setattr(wand_common, "PARAMS", {})

    assert wand_common.get_response_map("bool") == {"z": True, "m": False}


def test_get_response_map_label_uses_defaults(monkeypatch):
    monkeypatch.setattr(wand_common, "PARAMS", {})

    assert wand_common.get_response_map("label") == {
        "z": "match",
        "m": "non-match",
    }


def test_get_response_map_uses_custom_keys(monkeypatch):
    monkeypatch.setattr(
        wand_common,
        "PARAMS",
        {"response_keys": {"match": "s", "non_match": "l"}},
    )

    assert wand_common.get_response_map("bool") == {"s": True, "l": False}
    assert wand_common.get_response_map("label") == {
        "s": "match",
        "l": "non-match",
    }


def test_validate_response_keys_rejects_same_key():
    with pytest.raises(ValueError, match="must be different"):
        wand_common.validate_response_keys("s", "s")


@pytest.mark.parametrize("reserved_key", ["escape", "space", "return", "5"])
def test_validate_response_keys_rejects_reserved_keys(reserved_key):
    with pytest.raises(ValueError, match="cannot be one of"):
        wand_common.validate_response_keys(reserved_key, "m")


def test_collect_trial_response_accepts_seeded_custom_keys_headlessly(monkeypatch):
    match_key, non_match_key = _generate_seeded_custom_keys()
    monkeypatch.setattr(
        wand_common,
        "PARAMS",
        {"response_keys": {"match": match_key, "non_match": non_match_key}},
    )

    response_map = wand_common.get_response_map("bool")

    match_response, match_rt, match_calls = _run_headless_trial(
        monkeypatch, match_key, response_map
    )
    non_match_response, non_match_rt, non_match_calls = _run_headless_trial(
        monkeypatch, non_match_key, response_map
    )

    assert match_response is True
    assert non_match_response is False
    assert match_rt is not None
    assert non_match_rt is not None
    assert match_key in match_calls[0]
    assert non_match_key in match_calls[0]
    assert "z" not in match_calls[0]
    assert "m" not in match_calls[0]
    assert match_key in non_match_calls[0]
    assert non_match_key in non_match_calls[0]


def test_collect_trial_response_returns_labels_for_seeded_custom_keys(monkeypatch):
    match_key, non_match_key = _generate_seeded_custom_keys()
    monkeypatch.setattr(
        wand_common,
        "PARAMS",
        {"response_keys": {"match": match_key, "non_match": non_match_key}},
    )

    response_map = wand_common.get_response_map("label")

    match_response, _, _ = _run_headless_trial(monkeypatch, match_key, response_map)
    non_match_response, _, _ = _run_headless_trial(
        monkeypatch, non_match_key, response_map
    )

    assert match_response == "match"
    assert non_match_response == "non-match"
