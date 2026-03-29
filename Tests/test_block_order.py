"""
Tests/test_block_order.py

Pure unit tests for standard/default block-order helpers.
"""

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from wand_nback.block_order import (
    BLOCK_ORDER_MODE_CUSTOM,
    block_order_mode_from_label,
    build_standard_block_order,
    generate_default_schedules,
)

DEFAULT_CONFIG = {
    "sequential_enabled": True,
    "spatial_enabled": True,
    "dual_enabled": True,
    "sequential": {"blocks": 5},
    "spatial": {"blocks": 4, "time_compression": True},
    "dual": {"blocks": 4, "time_compression": True},
    "breaks_schedule": [2, 4],
    "measures_schedule": [2, 3, 4, 5],
}


def test_generate_default_schedules_matches_standard_protocol():
    """Default counts should resolve to the canonical WAND schedules."""
    breaks, measures = generate_default_schedules(2, 4, 5)

    assert breaks == [2, 4], f"Expected default breaks [2, 4], got {breaks}"
    assert measures == [
        2,
        3,
        4,
        5,
    ], f"Expected default measures [2, 3, 4, 5], got {measures}"


def test_build_standard_block_order_matches_expected_default_sequence():
    """The locked standard order should match the canonical full induction flow."""
    order = build_standard_block_order(DEFAULT_CONFIG)
    block_types = [block["type"] for block in order]

    assert block_types == [
        "start",
        "seq",
        "spa",
        "dual",
        "seq",
        "measures",
        "break",
        "dual",
        "spa",
        "seq",
        "measures",
        "spa",
        "dual",
        "seq",
        "measures",
        "break",
        "dual",
        "spa",
        "seq",
        "measures",
        "end",
    ]


def test_create_your_own_label_maps_to_custom_mode():
    """The UI label should resolve to the create-your-own mode."""
    mode = block_order_mode_from_label("Create Your Own")
    assert mode == BLOCK_ORDER_MODE_CUSTOM
