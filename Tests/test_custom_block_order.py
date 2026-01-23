"""
Tests/test_custom_block_order.py

Integration test for Block Builder custom order execution.

Verifies that custom_block_order is correctly passed and processed
by the induction script.

Author: Brodie E. Mangan
License: MIT
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from wand_nback.launcher import extract_schedules


def test_extract_schedules_counts_task_blocks():
    """Test that extract_schedules correctly counts task blocks for cycle assignment."""
    # Simulate Block Builder output: SEQ, SEQ, SPA, DUAL, measures
    block_order = [
        {"type": "start", "label": "Start"},
        {"type": "seq", "label": "SEQ"},
        {"type": "seq", "label": "SEQ"},
        {"type": "spa", "label": "SPA"},
        {"type": "dual", "label": "DUAL"},
        {"type": "measures", "label": "Sub_M"},
        {"type": "end", "label": "End"},
    ]

    breaks, measures = extract_schedules(block_order)

    # Measures placed after 4 task blocks should be assigned to cycle 4
    assert measures == [4], f"Expected measures at cycle [4], got {measures}"


def test_extract_schedules_break_after_first_block():
    """Test that a break after first block is assigned to cycle 1."""
    block_order = [
        {"type": "start", "label": "Start"},
        {"type": "seq", "label": "SEQ"},
        {"type": "break", "label": "Break"},
        {"type": "spa", "label": "SPA"},
        {"type": "end", "label": "End"},
    ]

    breaks, measures = extract_schedules(block_order)

    assert breaks == [1], f"Expected break at cycle [1], got {breaks}"


def test_extract_schedules_multiple_events():
    """Test multiple breaks and measures at different positions."""
    block_order = [
        {"type": "start", "label": "Start"},
        {"type": "seq", "label": "SEQ"},
        {"type": "measures", "label": "Sub_M"},  # After 1 task block
        {"type": "seq", "label": "SEQ"},
        {"type": "break", "label": "Break"},  # After 2 task blocks
        {"type": "spa", "label": "SPA"},
        {"type": "measures", "label": "Sub_M"},  # After 3 task blocks
        {"type": "end", "label": "End"},
    ]

    breaks, measures = extract_schedules(block_order)

    assert breaks == [2], f"Expected break at cycle [2], got {breaks}"
    assert measures == [1, 3], f"Expected measures at cycles [1, 3], got {measures}"


def test_custom_block_order_structure():
    """Test that a typical Block Builder output has correct structure."""
    # Simulate a user-configured block order
    block_order = [
        {"type": "start", "label": "Start", "movable": False},
        {"type": "seq", "label": "SEQ", "movable": True},
        {"type": "seq", "label": "SEQ", "movable": True},
        {"type": "spa", "label": "SPA", "movable": True},
        {"type": "dual", "label": "DUAL", "movable": True},
        {"type": "measures", "label": "Sub_M", "movable": True},
        {"type": "end", "label": "End", "movable": False},
    ]

    # Count task blocks
    task_blocks = [b for b in block_order if b["type"] in ("seq", "spa", "dual")]
    assert len(task_blocks) == 4, f"Expected 4 task blocks, got {len(task_blocks)}"

    # Verify order
    types = [b["type"] for b in block_order if b["type"] in ("seq", "spa", "dual")]
    assert types == [
        "seq",
        "seq",
        "spa",
        "dual",
    ], f"Expected ['seq', 'seq', 'spa', 'dual'], got {types}"


# ============================================================================
# EDGE CASE TESTS
# ============================================================================


def test_empty_block_order():
    """Test with only start/end blocks (no tasks)."""
    block_order = [
        {"type": "start", "label": "Start"},
        {"type": "end", "label": "End"},
    ]

    breaks, measures = extract_schedules(block_order)

    assert breaks == [], "No breaks should be scheduled"
    assert measures == [], "No measures should be scheduled"


def test_single_seq_block_only():
    """Test with just one Sequential block."""
    block_order = [
        {"type": "start", "label": "Start"},
        {"type": "seq", "label": "SEQ"},
        {"type": "end", "label": "End"},
    ]

    breaks, measures = extract_schedules(block_order)

    assert breaks == [], "No breaks expected"
    assert measures == [], "No measures expected"


def test_all_seq_blocks():
    """Test with only Sequential blocks (no SPA/DUAL)."""
    block_order = [
        {"type": "start", "label": "Start"},
        {"type": "seq", "label": "SEQ"},
        {"type": "seq", "label": "SEQ"},
        {"type": "seq", "label": "SEQ"},
        {"type": "measures", "label": "Sub_M"},
        {"type": "end", "label": "End"},
    ]

    breaks, measures = extract_schedules(block_order)

    # Measures after 3 SEQ blocks = cycle 3
    assert measures == [3], f"Expected measures at [3], got {measures}"


def test_measures_before_any_task():
    """Test measures placed before first task block - should default to cycle 1."""
    block_order = [
        {"type": "start", "label": "Start"},
        {"type": "measures", "label": "Sub_M"},  # Before any task
        {"type": "seq", "label": "SEQ"},
        {"type": "end", "label": "End"},
    ]

    breaks, measures = extract_schedules(block_order)

    # Measures before first task defaults to cycle 1
    assert measures == [1], f"Expected measures at [1], got {measures}"


def test_break_before_any_task():
    """Test break placed before first task block - should default to cycle 1."""
    block_order = [
        {"type": "start", "label": "Start"},
        {"type": "break", "label": "Break"},  # Before any task
        {"type": "spa", "label": "SPA"},
        {"type": "end", "label": "End"},
    ]

    breaks, measures = extract_schedules(block_order)

    assert breaks == [1], f"Expected break at [1], got {breaks}"


def test_alternating_tasks_and_events():
    """Test alternating pattern: task, event, task, event."""
    block_order = [
        {"type": "start", "label": "Start"},
        {"type": "seq", "label": "SEQ"},
        {"type": "break", "label": "Break"},
        {"type": "spa", "label": "SPA"},
        {"type": "measures", "label": "Sub_M"},
        {"type": "dual", "label": "DUAL"},
        {"type": "break", "label": "Break"},
        {"type": "end", "label": "End"},
    ]

    breaks, measures = extract_schedules(block_order)

    # Break after SEQ (cycle 1), Measures after SPA (cycle 2), Break after DUAL (cycle 3)
    assert breaks == [1, 3], f"Expected breaks at [1, 3], got {breaks}"
    assert measures == [2], f"Expected measures at [2], got {measures}"


def test_multiple_events_same_position():
    """Test multiple events between same task blocks."""
    block_order = [
        {"type": "start", "label": "Start"},
        {"type": "seq", "label": "SEQ"},
        {"type": "break", "label": "Break"},  # After SEQ
        {"type": "measures", "label": "Sub_M"},  # Also after SEQ
        {"type": "spa", "label": "SPA"},
        {"type": "end", "label": "End"},
    ]

    breaks, measures = extract_schedules(block_order)

    # Both events are after 1 task block = cycle 1
    assert breaks == [1], f"Expected break at [1], got {breaks}"
    assert measures == [1], f"Expected measures at [1], got {measures}"


def test_all_dual_blocks():
    """Test with only Dual blocks (no SEQ/SPA)."""
    block_order = [
        {"type": "start", "label": "Start"},
        {"type": "dual", "label": "DUAL"},
        {"type": "dual", "label": "DUAL"},
        {"type": "measures", "label": "Sub_M"},
        {"type": "end", "label": "End"},
    ]

    breaks, measures = extract_schedules(block_order)

    assert measures == [2], f"Expected measures at [2], got {measures}"


def test_events_at_end():
    """Test events placed at the very end after all tasks."""
    block_order = [
        {"type": "start", "label": "Start"},
        {"type": "seq", "label": "SEQ"},
        {"type": "spa", "label": "SPA"},
        {"type": "dual", "label": "DUAL"},
        {"type": "break", "label": "Break"},
        {"type": "measures", "label": "Sub_M"},
        {"type": "end", "label": "End"},
    ]

    breaks, measures = extract_schedules(block_order)

    # Both events after 3 task blocks = cycle 3
    assert breaks == [3], f"Expected break at [3], got {breaks}"
    assert measures == [3], f"Expected measures at [3], got {measures}"


def test_user_screenshot_sequence():
    """Test the exact sequence from user screenshot: SEQ, SEQ, SPA, DUAL, measures."""
    block_order = [
        {"type": "start", "label": "Start"},
        {"type": "seq", "label": "SEQ"},
        {"type": "seq", "label": "SEQ"},
        {"type": "spa", "label": "SPA"},
        {"type": "dual", "label": "DUAL"},
        {"type": "measures", "label": "Sub_M"},
        {"type": "end", "label": "End"},
    ]

    breaks, measures = extract_schedules(block_order)

    # Measures after 4 task blocks (SEQ, SEQ, SPA, DUAL) = cycle 4
    assert measures == [4], f"Expected measures at [4], got {measures}"
    assert breaks == [], "No breaks in this sequence"
