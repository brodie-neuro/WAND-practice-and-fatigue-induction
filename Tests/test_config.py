"""
Tests/test_config.py

Behavioural tests for WAND configuration integration.

This module tests that:
- GUI config values are actually USED by the scripts (not just readable)
- Timing fallbacks work correctly
- Scripts respond to config changes

Runs via: pytest Tests/test_config.py -v

Author: Brodie E. Mangan
License: MIT
"""

import json
import os
import sys
import tempfile
from unittest.mock import MagicMock, call, patch

import pytest

# Ensure we can import modules from the main folder
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Mock PsychoPy BEFORE any imports that use it
mock_psychopy = MagicMock()
mock_psychopy.__version__ = "2023.1.0"  # Fake version for logging
sys.modules["psychopy"] = mock_psychopy
sys.modules["psychopy.visual"] = MagicMock()
sys.modules["psychopy.core"] = MagicMock()
sys.modules["psychopy.event"] = MagicMock()

# --- LOGGING HELPER ---
RESULTS_DIR = os.path.join(os.path.dirname(__file__), "results")
os.makedirs(RESULTS_DIR, exist_ok=True)
LOG_FILE = os.path.join(RESULTS_DIR, "test_config_results.md")


def log_evidence(test_name, input_desc, expected, actual, status):
    """Log test evidence to Markdown file."""
    status_icon = "✅" if status == "PASS" else "❌"
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"### {status_icon} {test_name}\n\n")
        f.write(f"| Field | Value |\n")
        f.write(f"|-------|-------|\n")
        f.write(f"| **Status** | {status} |\n")
        f.write(f"| **Input** | {input_desc} |\n")
        f.write(f"| **Expected** | `{expected}` |\n")
        f.write(f"| **Actual** | `{actual}` |\n")
        f.write(f"\n---\n\n")


@pytest.hookimpl(tryfirst=True)
def pytest_sessionstart(session):
    from datetime import datetime

    with open(LOG_FILE, "w", encoding="utf-8") as f:
        f.write("# WAND Config Test Results\n\n")
        f.write(f"**Run Date**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write("---\n\n")
        f.write("## Test Results\n\n")


# --- TEST CONFIG (non-default values to prove config is used) ---
TEST_CONFIG = {
    "sequential": {
        "display_duration": 1.5,  # Default is 0.8
        "isi": 2.5,  # Default is 1.0
    },
    "spatial": {
        "display_duration": 1.8,  # Default is 1.0
        "isi": 2.0,  # Default is 1.0
    },
    "dual": {
        "display_duration": 1.2,  # Default is 1.0
        "isi": 1.8,  # Default is 1.2
    },
    "n_back_level": 3,
    "distractors_enabled": False,
    "participant_id": "test_config",
    "rng_seed": 12345,
}


# --- FIXTURES ---


@pytest.fixture
def mock_config_file():
    """Create a temporary config file and set environment variable."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(TEST_CONFIG, f)
        config_path = f.name

    os.environ["WAND_GUI_CONFIG"] = config_path
    yield config_path

    os.unlink(config_path)
    if "WAND_GUI_CONFIG" in os.environ:
        del os.environ["WAND_GUI_CONFIG"]


@pytest.fixture
def no_config():
    """Ensure no GUI config is set."""
    if "WAND_GUI_CONFIG" in os.environ:
        del os.environ["WAND_GUI_CONFIG"]
    yield
    if "WAND_GUI_CONFIG" in os.environ:
        del os.environ["WAND_GUI_CONFIG"]


# =============================================================================
# BEHAVIOURAL TESTS - Practice Script
# =============================================================================


def test_practice_get_gui_timing_returns_config_value(mock_config_file):
    """
    BEHAVIOURAL: Verify get_gui_timing returns the CONFIG value, not default.

    This tests that when a config file exists with display_duration=1.5,
    get_gui_timing actually returns 1.5, not the default 0.8.
    """
    # Import after setting up config
    from wand_nback import common as wand_common

    # Force reload of GUI config
    from wand_nback import practice_plateau as practice

    practice._GUI_CONFIG = None
    practice._GUI_CONFIG_LOADED = False

    # Call the actual function
    result = practice.get_gui_timing("sequential", "display_duration", 0.8)
    expected = TEST_CONFIG["sequential"]["display_duration"]

    log_evidence(
        "Practice: get_gui_timing uses config",
        f"Config has sequential.display_duration={expected}",
        expected,
        result,
        "PASS" if result == expected else "FAIL",
    )

    assert (
        result == expected
    ), f"get_gui_timing should return {expected} from config, got {result}"


def test_practice_get_gui_timing_falls_back_to_default(no_config):
    """
    BEHAVIOURAL: Verify get_gui_timing returns DEFAULT when no config exists.
    """
    from wand_nback import practice_plateau as practice

    # Force no config
    practice._GUI_CONFIG = None
    practice._GUI_CONFIG_LOADED = False

    default_value = 0.8
    result = practice.get_gui_timing("sequential", "display_duration", default_value)

    log_evidence(
        "Practice: get_gui_timing fallback",
        "No config file exists",
        default_value,
        result,
        "PASS" if result == default_value else "FAIL",
    )

    assert (
        result == default_value
    ), f"get_gui_timing should return default {default_value}, got {result}"


def test_practice_spatial_timing_uses_config(mock_config_file):
    """
    BEHAVIOURAL: Verify spatial task uses config timing values.
    """
    from wand_nback import practice_plateau as practice

    practice._GUI_CONFIG = None
    practice._GUI_CONFIG_LOADED = False

    result = practice.get_gui_timing("spatial", "display_duration", 1.0)
    expected = TEST_CONFIG["spatial"]["display_duration"]

    log_evidence(
        "Practice: Spatial timing uses config",
        f"Config has spatial.display_duration={expected}",
        expected,
        result,
        "PASS" if result == expected else "FAIL",
    )

    assert result == expected


def test_practice_dual_timing_uses_config(mock_config_file):
    """
    BEHAVIOURAL: Verify dual task uses config timing values.
    """
    from wand_nback import practice_plateau as practice

    practice._GUI_CONFIG = None
    practice._GUI_CONFIG_LOADED = False

    result = practice.get_gui_timing("dual", "isi", 1.2)
    expected = TEST_CONFIG["dual"]["isi"]

    log_evidence(
        "Practice: Dual ISI uses config",
        f"Config has dual.isi={expected}",
        expected,
        result,
        "PASS" if result == expected else "FAIL",
    )

    assert result == expected


# =============================================================================
# BEHAVIOURAL TESTS - Full Induction Script
# Note: We cannot directly import WAND_full_induction because it creates
# a window at import time. Instead, we test the timing retrieval via wand_common.
# =============================================================================


def test_induction_timing_via_load_gui_config(mock_config_file):
    """
    BEHAVIOURAL: Verify Full Induction can read timing values from config.

    This tests the path that WAND_full_induction.get_progressive_timings() uses
    to read config values, without importing the full module.
    """
    from wand_nback.common import load_gui_config

    config = load_gui_config()

    # Full Induction reads timings like this:
    # gui_config["spatial"].get("display_duration", 1.0)
    spatial_display = config["spatial"]["display_duration"]
    expected = TEST_CONFIG["spatial"]["display_duration"]

    log_evidence(
        "Induction: load_gui_config returns spatial timing",
        f"Config has spatial.display_duration={expected}",
        expected,
        spatial_display,
        "PASS" if spatial_display == expected else "FAIL",
    )

    assert spatial_display == expected, f"Expected {expected}, got {spatial_display}"


def test_induction_sequential_timing_via_load_gui_config(mock_config_file):
    """
    BEHAVIOURAL: Verify Sequential timing is accessible via load_gui_config.
    """
    from wand_nback.common import load_gui_config

    config = load_gui_config()

    seq_display = config["sequential"]["display_duration"]
    seq_isi = config["sequential"]["isi"]

    expected_display = TEST_CONFIG["sequential"]["display_duration"]
    expected_isi = TEST_CONFIG["sequential"]["isi"]

    log_evidence(
        "Induction: Sequential timing via config",
        f"Config has SEQ display={expected_display}, isi={expected_isi}",
        f"({expected_display}, {expected_isi})",
        f"({seq_display}, {seq_isi})",
        "PASS" if seq_display == expected_display else "FAIL",
    )

    assert seq_display == expected_display
    assert seq_isi == expected_isi


def test_induction_dual_timing_via_load_gui_config(mock_config_file):
    """
    BEHAVIOURAL: Verify Dual timing is accessible via load_gui_config.
    """
    from wand_nback.common import load_gui_config

    config = load_gui_config()

    dual_display = config["dual"]["display_duration"]
    dual_isi = config["dual"]["isi"]

    expected_display = TEST_CONFIG["dual"]["display_duration"]
    expected_isi = TEST_CONFIG["dual"]["isi"]

    log_evidence(
        "Induction: Dual timing via config",
        f"Config has DUAL display={expected_display}, isi={expected_isi}",
        f"({expected_display}, {expected_isi})",
        f"({dual_display}, {dual_isi})",
        "PASS" if dual_display == expected_display else "FAIL",
    )

    assert dual_display == expected_display
    assert dual_isi == expected_isi


# =============================================================================
# BEHAVIOURAL TESTS - Config Fallback
# =============================================================================


def test_load_gui_config_returns_none_without_env(no_config):
    """
    BEHAVIOURAL: Without WAND_GUI_CONFIG, load_gui_config returns None.
    """
    from wand_nback.common import load_gui_config

    config = load_gui_config()

    log_evidence(
        "Config: Returns None without env var",
        "WAND_GUI_CONFIG not set",
        "None",
        str(config),
        "PASS" if config is None else "FAIL",
    )

    assert config is None


def test_practice_fallback_to_default_timing(no_config):
    """
    BEHAVIOURAL: Without config, Practice uses default timings.
    """
    from wand_nback import practice_plateau as practice

    practice._GUI_CONFIG = None
    practice._GUI_CONFIG_LOADED = False

    # Sequential default is 0.8
    result = practice.get_gui_timing("sequential", "display_duration", 0.8)

    log_evidence(
        "Practice: Falls back to default",
        "No config",
        0.8,
        result,
        "PASS" if result == 0.8 else "FAIL",
    )

    assert result == 0.8
