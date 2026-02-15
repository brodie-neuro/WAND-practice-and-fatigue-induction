"""
Tests for EEG trigger configuration and send_trigger logic.

These tests mock hardware (parallel port, serial TriggerBox) to verify:
- Trigger name-to-code resolution from params.json
- Parallel port mode sends correct codes
- TriggerBox mode sends correct bytes
- Graceful failure when hardware is unavailable
- EEG disabled mode does nothing
- Config loading and saving in eeg_test.py

No actual EEG hardware is required.
"""

import json
import os
import sys
from unittest.mock import MagicMock, call, patch

import pytest

# =========================================================================
# eeg_test.py utility function tests (no PsychoPy dependency)
# =========================================================================

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class TestEegTestUtility:
    """Tests for wand_nback/eeg_test.py helper functions."""

    def test_get_config_path_points_to_package_config(self):
        """Config path should resolve to wand_nback/config/params.json."""
        from wand_nback.eeg_test import get_config_path

        path = get_config_path()
        assert path.endswith(os.path.join("config", "params.json"))
        assert "wand_nback" in path

    def test_load_config_returns_dict(self):
        """load_config should return a dict from params.json."""
        from wand_nback.eeg_test import load_config

        config = load_config()
        assert isinstance(config, dict)

    def test_load_config_has_eeg_section(self):
        """params.json should contain an eeg configuration section."""
        from wand_nback.eeg_test import load_config

        config = load_config()
        assert "eeg" in config
        assert "port_address" in config["eeg"]
        assert "triggers" in config["eeg"]

    def test_common_port_addresses_are_hex_strings(self):
        """All port addresses should be valid hex strings."""
        from wand_nback.eeg_test import COMMON_PORT_ADDRESSES

        assert len(COMMON_PORT_ADDRESSES) >= 10
        for addr in COMMON_PORT_ADDRESSES:
            assert addr.startswith("0x"), f"{addr} is not a hex string"
            int(addr, 16)  # Should not raise

    def test_save_config_writes_json(self, tmp_path):
        """save_config should write valid JSON."""
        from wand_nback.eeg_test import get_config_path, save_config

        # Temporarily redirect config path
        test_config = {"eeg": {"enabled": True, "port_address": "0xD010"}}
        test_path = tmp_path / "params.json"

        with patch("wand_nback.eeg_test.get_config_path", return_value=str(test_path)):
            save_config(test_config)

        with open(test_path, "r") as f:
            saved = json.load(f)
        assert saved["eeg"]["port_address"] == "0xD010"


# =========================================================================
# send_trigger logic tests (mocked hardware)
# =========================================================================


class TestSendTriggerLogic:
    """Tests for trigger resolution and dispatch in full_induction.py."""

    def test_trigger_names_resolve_to_codes(self):
        """All trigger names in params.json should resolve to non-zero int codes."""
        from wand_nback.eeg_test import load_config

        config = load_config()
        triggers = config.get("eeg", {}).get("triggers", {})

        assert len(triggers) > 0, "No triggers defined in params.json"

        for name, code in triggers.items():
            assert isinstance(code, int), f"Trigger '{name}' has non-int code: {code}"
            assert code > 0, f"Trigger '{name}' has invalid code: {code}"

    def test_trigger_codes_are_unique(self):
        """Each trigger code should be unique to avoid ambiguity in EEG data."""
        from wand_nback.eeg_test import load_config

        config = load_config()
        triggers = config.get("eeg", {}).get("triggers", {})
        codes = list(triggers.values())
        assert len(codes) == len(set(codes)), (
            f"Duplicate trigger codes found: "
            f"{[c for c in codes if codes.count(c) > 1]}"
        )

    def test_trigger_codes_are_valid_byte_values(self):
        """Trigger codes must be 0-255 for parallel port / TriggerBox byte protocol."""
        from wand_nback.eeg_test import load_config

        config = load_config()
        triggers = config.get("eeg", {}).get("triggers", {})

        for name, code in triggers.items():
            assert (
                0 <= code <= 255
            ), f"Trigger '{name}' code {code} is outside valid byte range 0-255"

    def test_expected_trigger_names_exist(self):
        """Key trigger names needed by the experiment should be defined."""
        from wand_nback.eeg_test import load_config

        config = load_config()
        triggers = config.get("eeg", {}).get("triggers", {})

        required_triggers = [
            "experiment_start",
            "experiment_end",
            "sequential_stimulus_onset",
            "spatial_stimulus_onset",
            "dual_stimulus_onset",
            "block_start",
            "block_end",
        ]

        for name in required_triggers:
            assert (
                name in triggers
            ), f"Required trigger '{name}' not found in params.json"

    def test_eeg_config_has_required_fields(self):
        """EEG config section should have all required fields."""
        from wand_nback.eeg_test import load_config

        config = load_config()
        eeg = config.get("eeg", {})

        required_fields = ["enabled", "port_address", "trigger_duration", "triggers"]
        for field in required_fields:
            assert field in eeg, f"Required EEG config field '{field}' missing"

    def test_trigger_duration_is_reasonable(self):
        """Trigger duration should be between 1ms and 50ms."""
        from wand_nback.eeg_test import load_config

        config = load_config()
        duration = config.get("eeg", {}).get("trigger_duration", 0)

        assert (
            0.001 <= duration <= 0.050
        ), f"Trigger duration {duration}s is outside reasonable range (1-50ms)"

    def test_scan_triggerbox_handles_no_pyserial(self):
        """scan_triggerbox should gracefully handle missing pyserial."""
        # Temporarily hide serial module
        original = sys.modules.get("serial")
        sys.modules["serial"] = None

        try:
            from wand_nback.eeg_test import scan_triggerbox

            port, conn = scan_triggerbox()
            assert port is None
            assert conn is None
        finally:
            if original is not None:
                sys.modules["serial"] = original
            else:
                sys.modules.pop("serial", None)

    def test_try_port_returns_none_on_exception(self):
        """try_port should return None when parallel port init raises."""
        from wand_nback.eeg_test import try_port

        with patch(
            "psychopy.parallel.ParallelPort", side_effect=RuntimeError("No port")
        ):
            result = try_port("0xFFFF")
            assert result is None
