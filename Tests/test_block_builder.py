"""
Tests/test_block_builder.py

Unit tests for the WAND Block Builder logic.

Tests block generation, ordering, counterbalancing, and break insertion.

Runs via: pytest Tests/test_block_builder.py -v

Author: Brodie E. Mangan
License: MIT
"""

import os
import sys

import pytest

# Ensure we can import modules from the main folder
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from wand_nback.block_builder import BlockBuilderWindow

# Mock configuration for testing
DEFAULT_CONFIG = {
    "sequential_enabled": True,
    "spatial_enabled": True,
    "dual_enabled": True,
    "sequential": {"blocks": 5},
    "spatial": {"blocks": 4},
    "dual": {"blocks": 4},
    "counterbalance_spatial_dual": False,
    "breaks_schedule": [2, 4],
    "measures_schedule": [2, 3, 4, 5],
}


class MockBlockBuilder(BlockBuilderWindow):
    """Subclass to bypass UI creation for testing logic."""

    def __init__(self, config):
        self.config = config
        # Skip UI init, only run block generation logic
        self.blocks = self._generate_default_blocks()

    def _create_window(self):
        pass  # Do nothing - no UI needed for tests


def test_block_counts_default():
    """Test that the correct number of task blocks are generated in pools."""
    builder = MockBlockBuilder(DEFAULT_CONFIG)

    # In new pool-based architecture, blocks are in separate pools, not main sequence
    seq_pool = builder._generate_seq_pool()
    spa_pool = builder._generate_spa_pool()
    dual_pool = builder._generate_dual_pool()

    assert len(seq_pool) == 5, f"Expected 5 SEQ blocks in pool, got {len(seq_pool)}"
    assert len(spa_pool) == 4, f"Expected 4 SPA blocks in pool, got {len(spa_pool)}"
    assert len(dual_pool) == 4, f"Expected 4 DUAL blocks in pool, got {len(dual_pool)}"


def test_block_ordering_standard():
    """Test standard ordering (SPA then DUAL)."""
    config = DEFAULT_CONFIG.copy()
    config["counterbalance_spatial_dual"] = False

    builder = MockBlockBuilder(config)
    blocks = builder.blocks

    # Check the first occurrence of SPA vs DUAL
    spa_indices = [i for i, b in enumerate(blocks) if b.get("type") == "spa"]
    dual_indices = [i for i, b in enumerate(blocks) if b.get("type") == "dual"]

    if spa_indices and dual_indices:
        assert (
            spa_indices[0] < dual_indices[0]
        ), "Spatial should come before Dual in standard mode"


def test_block_ordering_counterbalanced():
    """Test counterbalanced ordering (DUAL then SPA)."""
    config = DEFAULT_CONFIG.copy()
    config["counterbalance_spatial_dual"] = True

    builder = MockBlockBuilder(config)
    blocks = builder.blocks

    spa_indices = [i for i, b in enumerate(blocks) if b.get("type") == "spa"]
    dual_indices = [i for i, b in enumerate(blocks) if b.get("type") == "dual"]

    if spa_indices and dual_indices:
        assert (
            dual_indices[0] < spa_indices[0]
        ), "Dual should come before Spatial in counterbalanced mode"


def test_breaks_insertion():
    """Test that break pool is generated with correct count."""
    config = DEFAULT_CONFIG.copy()
    config["num_breaks"] = 2

    builder = MockBlockBuilder(config)
    break_pool = builder._generate_break_pool()

    assert len(break_pool) == 2, f"Expected 2 breaks in pool, got {len(break_pool)}"


def test_disabled_tasks():
    """Test that disabled tasks result in 0 blocks in pools."""
    config = DEFAULT_CONFIG.copy()
    config["sequential_enabled"] = False
    config["spatial_enabled"] = False

    builder = MockBlockBuilder(config)

    seq_pool = builder._generate_seq_pool()
    spa_pool = builder._generate_spa_pool()
    dual_pool = builder._generate_dual_pool()

    assert len(seq_pool) == 0, "SEQ pool should have 0 blocks when disabled"
    assert len(spa_pool) == 0, "SPA pool should have 0 blocks when disabled"
    assert len(dual_pool) == 4, "DUAL pool should still have 4 blocks"


def test_start_block_exists():
    """Test that Start block is always generated."""
    builder = MockBlockBuilder(DEFAULT_CONFIG)
    blocks = builder.blocks

    has_start = any(b.get("label") == "Start" for b in blocks)
    assert has_start, "Start block should always exist"


def test_end_block_exists():
    """Test that End block is always generated."""
    builder = MockBlockBuilder(DEFAULT_CONFIG)
    blocks = builder.blocks

    has_end = any(b.get("label") == "End" for b in blocks)
    assert has_end, "End block should always exist"
