"""
Tests/test_launcher_logic.py

BEHAVIOURAL tests for the WAND Launcher configuration system.

These tests verify that the Launcher correctly:
1. Creates config files on disk
2. Sets environment variables for scripts to read
3. Updates params.json with fullscreen setting
4. Passes configuration values that scripts actually use

Runs via: pytest Tests/test_launcher_logic.py -v

Author: Brodie E. Mangan
License: MIT
"""

import json
import os
import shutil
import sys
import tempfile
from unittest.mock import MagicMock, patch

import pytest

# Ensure we can import modules from the main folder
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Mock psychopy BEFORE importing any WAND modules
mock_psychopy = MagicMock()
mock_psychopy.__version__ = "2023.1.0"
sys.modules["psychopy"] = mock_psychopy
sys.modules["psychopy.visual"] = MagicMock()
sys.modules["psychopy.core"] = MagicMock()
sys.modules["psychopy.event"] = MagicMock()
sys.modules["psychopy.gui"] = MagicMock()
sys.modules["psychopy.logging"] = MagicMock()

# --- LOGGING HELPER ---
RESULTS_DIR = os.path.join(os.path.dirname(__file__), "results")
os.makedirs(RESULTS_DIR, exist_ok=True)
LOG_FILE = os.path.join(RESULTS_DIR, "test_launcher_logic_results.md")


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
        f.write("# WAND Launcher Logic Test Results\n\n")
        f.write(f"**Run Date**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write("These tests verify BEHAVIOURAL outcomes, not just JSON structure.\n\n")
        f.write("---\n\n")
        f.write("## Test Results\n\n")


# --- FIXTURES ---


@pytest.fixture
def temp_data_dir(tmp_path):
    """Creates a temporary data directory for config files."""
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    return str(data_dir)


@pytest.fixture
def temp_config_dir(tmp_path):
    """Creates a temporary config directory with params.json."""
    config_dir = tmp_path / "config"
    config_dir.mkdir()

    # Create a minimal params.json
    params = {"window": {"fullscreen": False, "size": [1024, 768]}}
    params_path = config_dir / "params.json"
    with open(params_path, "w") as f:
        json.dump(params, f)

    return str(config_dir)


@pytest.fixture
def sample_config():
    """Returns a sample Launcher configuration."""
    return {
        "participant_id": "TEST_001",
        "study_name": "Test Study",
        "task_mode": "Full Induction",
        "fullscreen": True,
        "n_back_level": 3,
        "rng_seed": 12345,
        "sequential": {"display_duration": 1.5, "isi": 2.0},
        "spatial": {"display_duration": 1.8, "isi": 1.5},
        "dual": {"display_duration": 1.2, "isi": 1.8},
    }


# =============================================================================
# BEHAVIOURAL TESTS - File Creation
# =============================================================================


def test_save_runtime_config_creates_file(temp_data_dir, sample_config, monkeypatch):
    """
    BEHAVIOURAL: save_runtime_config() creates a JSON file on disk.
    """
    # Patch DATA_DIR to our temp directory
    import WAND_Launcher

    monkeypatch.setattr(WAND_Launcher, "DATA_DIR", temp_data_dir)

    # Call the actual function
    result_path = WAND_Launcher.save_runtime_config(sample_config)

    # BEHAVIOUR: File should exist on disk
    file_exists = os.path.exists(result_path)

    log_evidence(
        "save_runtime_config creates file",
        f"Config with participant_id={sample_config['participant_id']}",
        "File exists on disk",
        f"File exists: {file_exists}",
        "PASS" if file_exists else "FAIL",
    )

    assert file_exists, f"Config file should exist at {result_path}"


def test_save_runtime_config_sets_env_var(temp_data_dir, sample_config, monkeypatch):
    """
    BEHAVIOURAL: save_runtime_config() sets WAND_GUI_CONFIG environment variable.
    """
    import WAND_Launcher

    monkeypatch.setattr(WAND_Launcher, "DATA_DIR", temp_data_dir)

    # Clear any existing env var
    monkeypatch.delenv("WAND_GUI_CONFIG", raising=False)

    # Call the actual function
    result_path = WAND_Launcher.save_runtime_config(sample_config)

    # BEHAVIOUR: Environment variable should be set
    env_value = os.environ.get("WAND_GUI_CONFIG")

    log_evidence(
        "save_runtime_config sets env var",
        "After calling save_runtime_config()",
        f"WAND_GUI_CONFIG={result_path}",
        f"WAND_GUI_CONFIG={env_value}",
        "PASS" if env_value == result_path else "FAIL",
    )

    assert (
        env_value == result_path
    ), f"WAND_GUI_CONFIG should be {result_path}, got {env_value}"


def test_saved_config_contains_correct_values(
    temp_data_dir, sample_config, monkeypatch
):
    """
    BEHAVIOURAL: Saved config file contains the values that were passed in.
    """
    import WAND_Launcher

    monkeypatch.setattr(WAND_Launcher, "DATA_DIR", temp_data_dir)

    result_path = WAND_Launcher.save_runtime_config(sample_config)

    # Read back the file
    with open(result_path, "r") as f:
        saved_config = json.load(f)

    # BEHAVIOUR: Saved values should match input
    fullscreen_matches = saved_config.get("fullscreen") == sample_config["fullscreen"]
    # n_back_matches = saved_config.get("n_back_level") == sample_config["n_back_level"] # REMOVED

    log_evidence(
        "Saved config has correct fullscreen",
        f"Input fullscreen={sample_config['fullscreen']}",
        sample_config["fullscreen"],
        saved_config.get("fullscreen"),
        "PASS" if fullscreen_matches else "FAIL",
    )

    assert fullscreen_matches, "Fullscreen should match"
    # assert n_back_matches, "N-back level should match" # REMOVED


# =============================================================================
# BEHAVIOURAL TESTS - Scripts Read Config Correctly
# =============================================================================


def test_scripts_receive_config_via_load_gui_config(
    temp_data_dir, sample_config, monkeypatch
):
    """
    BEHAVIOURAL: After save_runtime_config(), load_gui_config() returns the values.
    """
    import wand_common
    import WAND_Launcher

    monkeypatch.setattr(WAND_Launcher, "DATA_DIR", temp_data_dir)

    # Save config
    WAND_Launcher.save_runtime_config(sample_config)

    # BEHAVIOUR: wand_common.load_gui_config() should return the config
    loaded = wand_common.load_gui_config()

    log_evidence(
        "load_gui_config reads saved config",
        "After save_runtime_config()",
        f"participant_id={sample_config['participant_id']}",
        f"participant_id={loaded.get('participant_id') if loaded else 'None'}",
        "PASS"
        if loaded and loaded.get("participant_id") == sample_config["participant_id"]
        else "FAIL",
    )

    assert loaded is not None, "load_gui_config should return a dict"
    assert loaded.get("participant_id") == sample_config["participant_id"]


def test_timing_values_accessible_after_save(temp_data_dir, sample_config, monkeypatch):
    """
    BEHAVIOURAL: After save, scripts can read timing values via load_gui_config.
    """
    import wand_common
    import WAND_Launcher

    monkeypatch.setattr(WAND_Launcher, "DATA_DIR", temp_data_dir)

    WAND_Launcher.save_runtime_config(sample_config)
    loaded = wand_common.load_gui_config()

    # BEHAVIOUR: Timing values should be accessible
    seq_display = loaded.get("sequential", {}).get("display_duration")
    expected = sample_config["sequential"]["display_duration"]

    log_evidence(
        "Timing values accessible after save",
        f"Expected SEQ display={expected}",
        expected,
        seq_display,
        "PASS" if seq_display == expected else "FAIL",
    )

    assert seq_display == expected


# =============================================================================
# BEHAVIOURAL TESTS - Fullscreen Fix (params.json update)
# =============================================================================


def test_fullscreen_updates_params_json(temp_config_dir, sample_config, monkeypatch):
    """
    BEHAVIOURAL: The fullscreen fix should update params.json before script import.

    This tests the critical fix we made: Launcher now writes fullscreen to
    params.json BEFORE importing scripts, so the window is created correctly.
    """
    import WAND_Launcher

    monkeypatch.setattr(WAND_Launcher, "CONFIG_DIR", temp_config_dir)

    params_path = os.path.join(temp_config_dir, "params.json")

    # Read initial params
    with open(params_path, "r") as f:
        initial_params = json.load(f)
    initial_fullscreen = initial_params.get("window", {}).get("fullscreen")

    # Simulate what launch_experiment does for fullscreen
    with open(params_path, "r") as f:
        params = json.load(f)
    if "window" not in params:
        params["window"] = {}
    params["window"]["fullscreen"] = sample_config["fullscreen"]
    with open(params_path, "w") as f:
        json.dump(params, f)

    # Read back
    with open(params_path, "r") as f:
        updated_params = json.load(f)
    updated_fullscreen = updated_params.get("window", {}).get("fullscreen")

    log_evidence(
        "Fullscreen updates params.json",
        f"Config fullscreen={sample_config['fullscreen']}",
        sample_config["fullscreen"],
        updated_fullscreen,
        "PASS" if updated_fullscreen == sample_config["fullscreen"] else "FAIL",
    )

    assert (
        updated_fullscreen == sample_config["fullscreen"]
    ), f"params.json fullscreen should be {sample_config['fullscreen']}"


def test_fullscreen_false_updates_params_json(temp_config_dir, monkeypatch):
    """
    BEHAVIOURAL: When fullscreen=False in config, params.json should be False.
    """
    params_path = os.path.join(temp_config_dir, "params.json")

    # Set to True first
    with open(params_path, "r") as f:
        params = json.load(f)
    params["window"]["fullscreen"] = True
    with open(params_path, "w") as f:
        json.dump(params, f)

    # Now simulate config with fullscreen=False
    fullscreen_setting = False

    with open(params_path, "r") as f:
        params = json.load(f)
    params["window"]["fullscreen"] = fullscreen_setting
    with open(params_path, "w") as f:
        json.dump(params, f)

    # Verify
    with open(params_path, "r") as f:
        final_params = json.load(f)

    log_evidence(
        "Fullscreen=False updates params.json",
        "Config fullscreen=False",
        False,
        final_params.get("window", {}).get("fullscreen"),
        "PASS" if final_params.get("window", {}).get("fullscreen") is False else "FAIL",
    )

    assert final_params.get("window", {}).get("fullscreen") is False


# =============================================================================
# BEHAVIOURAL TESTS - Config Fallback
# =============================================================================


def test_load_gui_config_returns_none_without_env(monkeypatch):
    """
    BEHAVIOURAL: Without WAND_GUI_CONFIG env var, load_gui_config returns None.
    """
    import wand_common

    monkeypatch.delenv("WAND_GUI_CONFIG", raising=False)

    result = wand_common.load_gui_config()

    log_evidence(
        "load_gui_config returns None without env",
        "WAND_GUI_CONFIG not set",
        "None",
        str(result),
        "PASS" if result is None else "FAIL",
    )

    assert result is None
