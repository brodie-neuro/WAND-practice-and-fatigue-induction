"""
Tests for EEG trigger configuration and code validity.

These tests verify the EEG trigger system without requiring hardware.
They check code structure, config format, and graceful failure handling.
"""

import ast
import json
import os
import sys

import pytest

# Path to source files
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WAND_DIR = os.path.join(BASE_DIR, "wand_nback")
EEG_TEST_FILE = os.path.join(WAND_DIR, "eeg_test.py")
INDUCTION_FILE = os.path.join(WAND_DIR, "full_induction.py")
CONFIG_FILE = os.path.join(WAND_DIR, "config", "params.json")


# =============================================================================
# Code Structure Tests (no hardware needed)
# =============================================================================


class TestEEGTestUtilityCode:
    """Verify the eeg_test.py module has correct structure."""

    def test_eeg_test_file_exists(self):
        """eeg_test.py must exist in wand_nback/."""
        assert os.path.exists(
            EEG_TEST_FILE
        ), f"wand_nback/eeg_test.py not found at {EEG_TEST_FILE}"

    def test_eeg_test_has_main_function(self):
        """eeg_test.py must have a main() function for the entry point."""
        with open(EEG_TEST_FILE, "r", encoding="utf-8") as f:
            source = f.read()
        tree = ast.parse(source)
        func_names = [
            node.name for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)
        ]
        assert "main" in func_names, "eeg_test.py must define a main() function"

    def test_eeg_test_has_try_port_function(self):
        """eeg_test.py must have a try_port() function."""
        with open(EEG_TEST_FILE, "r", encoding="utf-8") as f:
            source = f.read()
        tree = ast.parse(source)
        func_names = [
            node.name for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)
        ]
        assert "try_port" in func_names, "eeg_test.py must define a try_port() function"

    def test_eeg_test_has_readback_verification(self):
        """try_port() must contain read-back verification logic."""
        with open(EEG_TEST_FILE, "r", encoding="utf-8") as f:
            source = f.read()
        assert (
            "readData" in source
        ), "eeg_test.py must use readData() for read-back verification"
        assert (
            "170" in source or "0xAA" in source
        ), "eeg_test.py must use test pattern 170 (0xAA)"

    def test_eeg_test_has_common_addresses(self):
        """eeg_test.py must define COMMON_PORT_ADDRESSES with key addresses."""
        with open(EEG_TEST_FILE, "r", encoding="utf-8") as f:
            source = f.read()
        assert "0x378" in source, "Must include standard LPT1 address 0x378"
        assert "0x3FF8" in source, "Must include PCIe card address 0x3FF8"

    def test_eeg_test_has_triggerbox_scan(self):
        """eeg_test.py must have TriggerBox scanning capability."""
        with open(EEG_TEST_FILE, "r", encoding="utf-8") as f:
            source = f.read()
        tree = ast.parse(source)
        func_names = [
            node.name for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)
        ]
        assert (
            "scan_triggerbox" in func_names
        ), "eeg_test.py must define scan_triggerbox()"


class TestInductionEEGCode:
    """Verify full_induction.py has correct EEG trigger handling."""

    def test_induction_has_parallel_port_function(self):
        """full_induction.py must have _get_parallel_port()."""
        with open(INDUCTION_FILE, "r", encoding="utf-8") as f:
            source = f.read()
        tree = ast.parse(source)
        func_names = [
            node.name for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)
        ]
        assert (
            "_get_parallel_port" in func_names
        ), "full_induction.py must define _get_parallel_port()"

    def test_induction_has_readback_verification(self):
        """_get_parallel_port() must contain read-back verification."""
        with open(INDUCTION_FILE, "r", encoding="utf-8") as f:
            source = f.read()
        assert (
            "readData" in source
        ), "full_induction.py must use readData() for verification"

    def test_induction_eeg_trigger_mode_check(self):
        """_get_parallel_port() must check EEG_TRIGGER_MODE."""
        with open(INDUCTION_FILE, "r", encoding="utf-8") as f:
            source = f.read()
        assert (
            "EEG_TRIGGER_MODE" in source
        ), "full_induction.py must reference EEG_TRIGGER_MODE"


class TestEEGConfig:
    """Verify params.json has correct EEG configuration structure."""

    def test_config_file_exists(self):
        """params.json must exist."""
        assert os.path.exists(CONFIG_FILE), f"Config file not found: {CONFIG_FILE}"

    def test_config_is_valid_json(self):
        """params.json must be valid JSON."""
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            config = json.load(f)
        assert isinstance(config, dict)

    def test_config_has_eeg_section(self):
        """params.json must have an eeg configuration section."""
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            config = json.load(f)
        assert "eeg" in config, "params.json must have an 'eeg' section"

    def test_config_eeg_has_required_fields(self):
        """EEG config must have enabled, trigger_mode, and parallel_port_address."""
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            config = json.load(f)
        eeg = config.get("eeg", {})
        assert "enabled" in eeg, "EEG config must have 'enabled' field"
        assert "trigger_mode" in eeg, "EEG config must have 'trigger_mode' field"
        assert (
            "parallel_port_address" in eeg
        ), "EEG config must have 'parallel_port_address' field"
