#!/usr/bin/env python3
"""
Helpers for resolving WAND block-order modes and the standard protocol order.
"""

import math

BLOCK_ORDER_MODE_DEFAULT = "standard"
BLOCK_ORDER_MODE_CUSTOM = "create_your_own"

BLOCK_ORDER_MODE_LABELS = {
    BLOCK_ORDER_MODE_DEFAULT: "Standard",
    BLOCK_ORDER_MODE_CUSTOM: "Create Your Own",
}

VALID_BLOCK_ORDER_MODES = set(BLOCK_ORDER_MODE_LABELS)
TASK_BLOCK_TYPES = ("seq", "spa", "dual")

LEGACY_BLOCK_ORDER_MODES = {
    "default_locked": BLOCK_ORDER_MODE_DEFAULT,
    "standard_locked": BLOCK_ORDER_MODE_DEFAULT,
    "standard (locked)": BLOCK_ORDER_MODE_DEFAULT,
    "custom_builder": BLOCK_ORDER_MODE_CUSTOM,
    "create your own (block builder)": BLOCK_ORDER_MODE_CUSTOM,
}


def normalize_block_order_mode(value):
    """Normalize legacy labels/values to a supported block-order mode."""
    if isinstance(value, list):
        value = value[0] if value else ""

    mode = str(value or "").strip().lower()
    if not mode:
        return BLOCK_ORDER_MODE_DEFAULT
    if mode in VALID_BLOCK_ORDER_MODES:
        return mode
    if mode in LEGACY_BLOCK_ORDER_MODES:
        return LEGACY_BLOCK_ORDER_MODES[mode]
    if "create your own" in mode or "custom" in mode or "block builder" in mode:
        return BLOCK_ORDER_MODE_CUSTOM
    return BLOCK_ORDER_MODE_DEFAULT


def get_block_order_mode(config):
    """Return a supported block-order mode from config."""
    return normalize_block_order_mode(
        config.get("block_order_mode", BLOCK_ORDER_MODE_DEFAULT)
    )


def block_order_mode_label(mode):
    """Return the UI label for a block-order mode."""
    return BLOCK_ORDER_MODE_LABELS.get(
        normalize_block_order_mode(mode),
        BLOCK_ORDER_MODE_LABELS[BLOCK_ORDER_MODE_DEFAULT],
    )


def block_order_mode_from_label(label):
    """Parse a UI label back into an internal block-order mode."""
    return normalize_block_order_mode(label)


def total_cycles_from_config(config):
    """Return the number of standard induction cycles for the current config."""
    seq_blocks = (
        config.get("sequential", {}).get("blocks", 5)
        if config.get("sequential_enabled", True)
        else 0
    )
    spa_blocks = (
        config.get("spatial", {}).get("blocks", 4)
        if config.get("spatial_enabled", True)
        else 0
    )
    dual_blocks = (
        config.get("dual", {}).get("blocks", 4)
        if config.get("dual_enabled", True)
        else 0
    )
    return max(seq_blocks, spa_blocks, dual_blocks)


def _clamp_schedule(values, total_cycles):
    if total_cycles <= 0:
        return []
    cleaned = [max(1, min(total_cycles, int(v))) for v in values]
    return sorted(set(cleaned))


def generate_default_schedules(num_breaks, num_measures, total_cycles):
    """
    Generate default break and measure schedules for the standard protocol.

    Breaks are distributed before the final cycle when possible. Measures are
    distributed after the first cycle when possible, matching the canonical
    default schedule of Breaks=[2, 4] and Measures=[2, 3, 4, 5] for 5 cycles.
    """
    if total_cycles <= 0:
        return [], []

    breaks = []
    if num_breaks > 0:
        if total_cycles == 1:
            breaks = [1]
        elif num_breaks == 1:
            breaks = [max(1, min(total_cycles - 1, math.ceil(total_cycles / 2)))]
        else:
            step = total_cycles / (num_breaks + 1)
            max_break_cycle = max(1, total_cycles - 1)
            breaks = [
                max(1, min(max_break_cycle, math.ceil(step * (i + 1))))
                for i in range(num_breaks)
            ]

    measures = []
    if num_measures > 0:
        if num_measures >= total_cycles:
            measures = list(range(1, total_cycles + 1))
        else:
            step = total_cycles / (num_measures + 1)
            measures = [int(step * (i + 1)) + 1 for i in range(num_measures)]

    return _clamp_schedule(breaks, total_cycles), _clamp_schedule(
        measures, total_cycles
    )


def resolve_schedules(config):
    """Resolve schedules from config, generating defaults when only counts exist."""
    total_cycles = total_cycles_from_config(config)
    raw_breaks = config.get("breaks_schedule")
    raw_measures = config.get("measures_schedule")

    breaks = raw_breaks if isinstance(raw_breaks, list) else None
    measures = raw_measures if isinstance(raw_measures, list) else None

    if breaks is None or measures is None:
        generated_breaks, generated_measures = generate_default_schedules(
            config.get("num_breaks", 0),
            config.get("num_measures", 0),
            total_cycles,
        )
        if breaks is None:
            breaks = generated_breaks
        if measures is None:
            measures = generated_measures

    return _clamp_schedule(breaks or [], total_cycles), _clamp_schedule(
        measures or [], total_cycles
    )


def _make_block(label, block_type, movable=True):
    return {"label": label, "type": block_type, "movable": movable}


def build_standard_block_order(config):
    """Return the canonical default full-induction order as block-builder blocks."""
    seq_enabled = config.get("sequential_enabled", True)
    spa_enabled = config.get("spatial_enabled", True)
    dual_enabled = config.get("dual_enabled", True)

    seq_blocks = config.get("sequential", {}).get("blocks", 5) if seq_enabled else 0
    spa_blocks = config.get("spatial", {}).get("blocks", 4) if spa_enabled else 0
    dual_blocks = config.get("dual", {}).get("blocks", 4) if dual_enabled else 0

    breaks, measures = resolve_schedules(config)
    max_loops = total_cycles_from_config(config)

    order = [_make_block("Start", "start", movable=False)]

    for cycle_num in range(1, max_loops + 1):
        if seq_enabled and cycle_num <= seq_blocks:
            order.append(_make_block("SEQ", "seq"))

        if cycle_num in measures:
            order.append(_make_block("Sub_M", "measures"))
        if cycle_num in breaks:
            order.append(_make_block("Break", "break"))

        if cycle_num % 2 != 0:
            current_order = (
                ("SPA", spa_enabled, spa_blocks),
                ("DUAL", dual_enabled, dual_blocks),
            )
        else:
            current_order = (
                ("DUAL", dual_enabled, dual_blocks),
                ("SPA", spa_enabled, spa_blocks),
            )

        for label, enabled, block_count in current_order:
            if enabled and cycle_num <= block_count:
                order.append(_make_block(label, label.lower()))

    order.append(_make_block("End", "end", movable=False))
    return order
