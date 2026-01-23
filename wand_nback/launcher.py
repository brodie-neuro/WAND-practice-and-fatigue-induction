#!/usr/bin/env python3
"""
WAND Launcher v1.1.1 - Comprehensive Study Configuration System

A professional GUI for configuring WAND experiments with:
- Study presets (save/load configurations)
- Per-task timing settings
- Task enable/disable toggles
- Time compression controls
- Counterbalancing options

Author: Brodie E. Mangan
Version: 1.1.1
License: MIT
"""

import json
import os
import sys
from collections import OrderedDict
from datetime import datetime

# Import block builder module
try:
    from wand_nback.block_builder import show_block_builder

    BLOCK_BUILDER_AVAILABLE = True
except ImportError:
    BLOCK_BUILDER_AVAILABLE = False
    print("[WARNING] block_builder.py not found - block ordering disabled")

# =============================================================================
# Import PsychoPy GUI
# =============================================================================
# Scale Qt dialogs to be 20% larger (set before importing psychopy.gui)
os.environ["QT_SCALE_FACTOR"] = "1.2"

try:
    from psychopy import gui, logging

    # Suppress cosmetic validation errors from GUI (e.g. "could not convert string to float")
    logging.console.setLevel(logging.CRITICAL)
except ImportError:
    print("ERROR: PsychoPy is not installed.")
    print("Please run: pip install -r requirements.txt")
    sys.exit(1)

# =============================================================================
# Paths and Directories
# =============================================================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_DIR = os.path.join(BASE_DIR, "config")
PRESETS_DIR = os.path.join(CONFIG_DIR, "presets")
DATA_DIR = os.path.join(BASE_DIR, "data")

# Ensure directories exist
os.makedirs(PRESETS_DIR, exist_ok=True)
os.makedirs(DATA_DIR, exist_ok=True)

# =============================================================================
# Default Configuration
# =============================================================================
DEFAULT_CONFIG = {
    # Metadata
    "study_name": "Default_Study",
    "created": None,
    "last_modified": None,
    # Task Mode
    "task_mode": "Full Induction",
    # Task Enables
    "sequential_enabled": True,
    "spatial_enabled": True,
    "dual_enabled": True,
    # Sequential N-back Settings
    "sequential": {
        "blocks": 5,
        "display_duration": 0.8,
        "isi": 1.0,
        "trials_per_block": 164,
        "distractors_enabled": True,
    },
    # Spatial N-back Settings
    "spatial": {
        "blocks": 4,
        "display_duration": 1.0,
        "isi": 1.0,
        "time_compression": True,
    },
    # Dual N-back Settings
    "dual": {
        "blocks": 4,
        "display_duration": 1.0,
        "isi": 1.2,
        "time_compression": True,
    },
    # Global Options
    "counterbalance_spatial_dual": False,
    "fullscreen": True,
    "rng_seed": None,
    "breaks_schedule": [2, 4],
    "measures_schedule": [2, 3, 4, 5],
}


# =============================================================================
# Utility Functions
# =============================================================================


def format_duration(minutes):
    """Format duration as 'X min Y sec' for better resolution on short experiments."""
    if minutes >= 60:
        hours = int(minutes // 60)
        mins = int(minutes % 60)
        return f"{hours}h {mins}m"
    elif minutes >= 1:
        mins = int(minutes)
        secs = int((minutes - mins) * 60)
        if secs > 0:
            return f"{mins} min {secs} sec"
        return f"{mins} min"
    else:
        secs = int(minutes * 60)
        return f"{secs} sec"


# =============================================================================
# Preset Management
# =============================================================================


def get_available_presets():
    """
    Get list of available study presets.

    Returns
    -------
    list
        List of preset names (without .json extension)
    """
    presets = ["<Create New>"]

    if os.path.exists(PRESETS_DIR):
        for f in os.listdir(PRESETS_DIR):
            if f.endswith(".json"):
                presets.append(f[:-5])  # Remove .json

    return presets


def load_preset(preset_name):
    """
    Load a study preset from JSON.

    Parameters
    ----------
    preset_name : str
        Name of the preset (without .json)

    Returns
    -------
    dict
        Configuration dictionary, or DEFAULT_CONFIG if not found
    """
    if preset_name == "<Create New>" or not preset_name:
        return DEFAULT_CONFIG.copy()

    preset_path = os.path.join(PRESETS_DIR, f"{preset_name}.json")

    if not os.path.exists(preset_path):
        print(f"[WARNING] Preset not found: {preset_path}")
        return DEFAULT_CONFIG.copy()

    try:
        with open(preset_path, "r", encoding="utf-8") as f:
            config = json.load(f)
        print(f"[INFO] Loaded preset: {preset_name}")
        return config
    except Exception as e:
        print(f"[ERROR] Failed to load preset: {e}")
        return DEFAULT_CONFIG.copy()


def save_preset(config, preset_name):
    """
    Save a study configuration as a preset.

    Parameters
    ----------
    config : dict
        Configuration to save
    preset_name : str
        Name for the preset

    Returns
    -------
    str
        Path to saved file
    """
    config["last_modified"] = datetime.now().isoformat()
    if config.get("created") is None:
        config["created"] = config["last_modified"]

    preset_path = os.path.join(PRESETS_DIR, f"{preset_name}.json")

    with open(preset_path, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2)

    print(f"[INFO] Saved preset: {preset_path}")
    return preset_path


# =============================================================================
# Page 1: Study Setup
# =============================================================================


def show_page1_study_setup():
    """
    Page 1: Study name, load preset, task mode.

    Returns
    -------
    dict or None
        Partial config dict, or None if cancelled
    """
    presets = get_available_presets()

    # Ensure "Standard_WAND_Protocol" is always available and first after <Create New>
    if "Standard_WAND_Protocol" in presets:
        presets.remove("Standard_WAND_Protocol")
    presets.insert(0, "Standard_WAND_Protocol")  # Put Standard first
    # Move <Create New> to end of list
    if "<Create New>" in presets:
        presets.remove("<Create New>")
        presets.append("<Create New>")

    # Use OrderedDict with DlgFromDict for reliable cross-version behaviour
    fields = OrderedDict()
    fields["Load_Preset"] = presets  # Dropdown - Standard_WAND_Protocol is now first
    fields["Study_Name"] = "My_Study"
    fields[
        "Participant_ID"
    ] = ""  # Required but without asterisk to avoid PsychoPy message

    # Tooltips for Study Setup
    tips = {
        "Load_Preset": "Load a saved configuration. Standard_WAND_Protocol uses default parameters.",
        "Study_Name": "Name of your study. Used in output file names.",
        "Participant_ID": "Unique participant identifier. Used in output file names.",
    }

    dlg = gui.DlgFromDict(
        dictionary=fields,
        title="WAND - Page 1/5: Study Setup",
        sortKeys=False,
        show=False,
        tip=tips,
    )

    dlg.show()

    if not dlg.OK:
        return None

    # Validate Participant ID is not empty
    if not fields["Participant_ID"].strip():
        error_dlg = gui.Dlg(title="Validation Error")
        error_dlg.addText("Participant ID cannot be empty!")
        error_dlg.show()
        return show_page1_study_setup()  # Recurse to show again

    return {
        "load_preset": fields["Load_Preset"],
        "study_name": fields["Study_Name"],
        "participant_id": fields["Participant_ID"].strip(),
    }


# =============================================================================
# Page 2: Task Selection
# =============================================================================


def show_page2_task_selection(config):
    """
    Page 2: Which tasks enabled, block counts.

    Parameters
    ----------
    config : dict
        Current configuration (for defaults)

    Returns
    -------
    dict or None
        Updated config fields, or None if cancelled
    """
    # Use OrderedDict with DlgFromDict
    fields = OrderedDict()

    # Sequential
    fields["Sequential_Enabled"] = config.get("sequential_enabled", True)
    fields["Sequential_Blocks"] = config.get("sequential", {}).get("blocks", 5)

    # Spatial
    fields["Spatial_Enabled"] = config.get("spatial_enabled", True)
    fields["Spatial_Blocks"] = config.get("spatial", {}).get("blocks", 4)

    # Dual
    fields["Dual_Enabled"] = config.get("dual_enabled", True)
    fields["Dual_Blocks"] = config.get("dual", {}).get("blocks", 4)

    # Tooltips for Task Selection
    tips = {
        "Sequential_Enabled": "Image-based N-back. Duration varies with timing (164 trials × display + ISI).",
        "Sequential_Blocks": "Number of Sequential blocks. Each block = 164 trials.",
        "Spatial_Enabled": "Grid-based spatial N-back. Fixed 270 seconds per block.",
        "Spatial_Blocks": "Number of Spatial blocks. Each block = 270 seconds.",
        "Dual_Enabled": "Combined image + grid N-back. Fixed 270 seconds per block.",
        "Dual_Blocks": "Number of Dual blocks. Each block = 270 seconds.",
    }

    dlg = gui.DlgFromDict(
        dictionary=fields,
        title="WAND - Page 2/5: Task Selection",
        sortKeys=False,
        tip=tips,
    )

    if not dlg.OK:
        return None

    # Validate: at least one task must be enabled
    seq_enabled = fields["Sequential_Enabled"]
    spa_enabled = fields["Spatial_Enabled"]
    dual_enabled = fields["Dual_Enabled"]

    if not any([seq_enabled, spa_enabled, dual_enabled]):
        error_dlg = gui.Dlg(title="Validation Error")
        error_dlg.addText("At least one task must be enabled!")
        error_dlg.show()
        return show_page2_task_selection(config)  # Recurse to show again

    return {
        "sequential_enabled": seq_enabled,
        "sequential_blocks": int(fields["Sequential_Blocks"])
        if str(fields["Sequential_Blocks"]).strip()
        else 0,
        "spatial_enabled": spa_enabled,
        "spatial_blocks": int(fields["Spatial_Blocks"])
        if str(fields["Spatial_Blocks"]).strip()
        else 0,
        "dual_enabled": dual_enabled,
        "dual_blocks": int(fields["Dual_Blocks"])
        if str(fields["Dual_Blocks"]).strip()
        else 0,
    }


# =============================================================================
# Page 3: Task Timings
# =============================================================================


def show_page3_task_timings(config):
    """
    Page 3: Per-task timing settings - ONLY for enabled tasks.

    Parameters
    ----------
    config : dict
        Current configuration

    Returns
    -------
    dict or None
        Updated timing fields, or None if cancelled
    """
    seq = config.get("sequential", {})
    spa = config.get("spatial", {})
    dual = config.get("dual", {})

    seq_enabled = config.get("sequential_enabled", True)
    spa_enabled = config.get("spatial_enabled", True)
    dual_enabled = config.get("dual_enabled", True)

    # Only add fields for enabled tasks (using spaces for clean labels)
    fields = OrderedDict()

    if seq_enabled:
        fields["SEQ Display (sec)"] = seq.get("display_duration", 0.8)
        fields["SEQ ISI (sec)"] = seq.get("isi", 1.0)
        fields["SEQ Distractors"] = seq.get("distractors_enabled", True)

    if spa_enabled:
        fields["SPA Display (sec)"] = spa.get("display_duration", 1.0)
        fields["SPA ISI (sec)"] = spa.get("isi", 1.0)
        fields["SPA Time Compression"] = spa.get("time_compression", True)

    if dual_enabled:
        fields["DUAL Display (sec)"] = dual.get("display_duration", 1.0)
        fields["DUAL ISI (sec)"] = dual.get("isi", 1.2)
        fields["DUAL Time Compression"] = dual.get("time_compression", True)

    # If no tasks enabled, skip this page
    if not fields:
        return {
            "seq_display": 0.8,
            "seq_isi": 1.0,
            "seq_distractors": True,
            "spa_display": 1.0,
            "spa_isi": 1.0,
            "spa_compression": True,
            "dual_display": 1.0,
            "dual_isi": 1.2,
            "dual_compression": True,
        }

    # Tooltips explaining timing behavior
    tips = {}
    if seq_enabled:
        tips["SEQ Display (sec)"] = (
            "How long each letter is shown. Block duration = 164 trials × (display + ISI). "
            "Changing timing affects total block duration."
        )
        tips["SEQ ISI (sec)"] = (
            "Inter-stimulus interval between letters. "
            "Block duration = 164 trials × (display + ISI)."
        )
        tips[
            "SEQ Distractors"
        ] = "Show 200ms white square flashes during ISI to probe vigilance."

    if spa_enabled:
        tips["SPA Display (sec)"] = (
            "How long each grid is shown. NOTE: Block duration is FIXED at 270 seconds. "
            "Changing timing affects trial pacing, not total block duration."
        )
        tips["SPA ISI (sec)"] = (
            "Inter-stimulus interval between grids. "
            "Block duration remains 270 seconds regardless of this setting."
        )
        tips["SPA Time Compression"] = (
            "Reduce BOTH display and ISI times slightly in blocks 2+ to maintain cognitive demand. "
            "Block 1 always uses standard timing."
        )

    if dual_enabled:
        tips["DUAL Display (sec)"] = (
            "How long each stimulus is shown. NOTE: Block duration is FIXED at 270 seconds. "
            "Changing timing affects trial pacing, not total block duration."
        )
        tips["DUAL ISI (sec)"] = (
            "Inter-stimulus interval. "
            "Block duration remains 270 seconds regardless of this setting."
        )
        tips["DUAL Time Compression"] = (
            "Reduce BOTH display and ISI times slightly in blocks 2+ to maintain cognitive demand. "
            "Block 1 always uses standard timing."
        )

    dlg = gui.DlgFromDict(
        dictionary=fields,
        title="WAND - Page 3/5: Task Timings",
        sortKeys=False,
        tip=tips,
    )

    if not dlg.OK:
        return None

    # Build result with defaults for disabled tasks
    result = {
        "seq_display": 0.8,
        "seq_isi": 1.0,
        "seq_distractors": True,
        "spa_display": 1.0,
        "spa_isi": 1.0,
        "spa_compression": True,
        "dual_display": 1.0,
        "dual_isi": 1.2,
        "dual_compression": True,
    }

    if seq_enabled:
        s_disp = str(fields["SEQ Display (sec)"]).strip()
        s_isi = str(fields["SEQ ISI (sec)"]).strip()
        result["seq_display"] = float(s_disp) if s_disp else 0.8
        result["seq_isi"] = float(s_isi) if s_isi else 1.0
        result["seq_distractors"] = bool(fields["SEQ Distractors"])

    if spa_enabled:
        sp_disp = str(fields["SPA Display (sec)"]).strip()
        sp_isi = str(fields["SPA ISI (sec)"]).strip()
        result["spa_display"] = float(sp_disp) if sp_disp else 1.0
        result["spa_isi"] = float(sp_isi) if sp_isi else 1.0
        result["spa_compression"] = bool(fields["SPA Time Compression"])

    if dual_enabled:
        d_disp = str(fields["DUAL Display (sec)"]).strip()
        d_isi = str(fields["DUAL ISI (sec)"]).strip()
        result["dual_display"] = float(d_disp) if d_disp else 1.0
        result["dual_isi"] = float(d_isi) if d_isi else 1.2
        result["dual_compression"] = bool(fields["DUAL Time Compression"])

    return result


# =============================================================================
# Page 4: Global Options
# =============================================================================


def show_page4_options(config):
    """
    Page 4: Global options - N-back level, counterbalancing, etc.
    Only show counterbalancing if BOTH Spatial and Dual are enabled.

    Parameters
    ----------
    config : dict
        Current configuration

    Returns
    -------
    dict or None
        Updated options, or None if cancelled
    """
    spa_enabled = config.get("spatial_enabled", True)
    dual_enabled = config.get("dual_enabled", True)
    both_spa_dual = spa_enabled and dual_enabled

    # Use OrderedDict with space-containing keys for clean labels
    fields = OrderedDict()

    # fields["N-back Level"] = ["2", "3"]  # REMOVED - Prompts at runtime
    fields["Fullscreen"] = config.get("fullscreen", True)
    fields["RNG Seed (blank = random)"] = str(config.get("rng_seed", "") or "")

    # Breaks and measures configuration - now using COUNTS, not positions
    # Positions will be configured in the Block Builder
    def_num_breaks = len(config.get("breaks_schedule", [2, 4]))
    def_num_measures = len(config.get("measures_schedule", [2, 3, 4, 5]))

    fields["Number of Breaks"] = def_num_breaks
    fields["Break Duration (sec)"] = config.get("break_duration", 20)
    fields["Subjective Measures"] = def_num_measures
    fields["Save as Preset"] = True

    # Tooltips for Options
    tips = {
        "Fullscreen": "Run experiment in fullscreen mode. Recommended for data collection.",
        "RNG Seed (blank = random)": "Fixed seed for reproducible stimulus sequences. Leave blank for true randomisation.",
        "Number of Breaks": "Short rest periods. Position in Block Builder.",
        "Break Duration (sec)": "Duration of each break in seconds.",
        "Subjective Measures": "Questionnaire insertions (e.g., fatigue ratings). Position in Block Builder.",
        "Save as Preset": "Save this configuration for future use.",
    }

    dlg = gui.DlgFromDict(
        dictionary=fields,
        title="WAND - Page 4/5: Options",
        sortKeys=False,
        tip=tips,
    )

    if not dlg.OK:
        return None

    # Parse RNG seed
    seed_str = str(fields["RNG Seed (blank = random)"]).strip()
    rng_seed = int(seed_str) if seed_str else None

    # Clamp counts to 0-8 (handle empty strings gracefully)
    breaks_str = str(fields["Number of Breaks"]).strip()
    num_breaks = max(0, min(8, int(breaks_str) if breaks_str else 0))

    measures_str = str(fields["Subjective Measures"]).strip()
    num_measures = max(0, min(8, int(measures_str) if measures_str else 0))

    result = {
        # "n_back_level": int(fields["N-back Level"]),  # REMOVED
        "fullscreen": bool(fields["Fullscreen"]),
        "rng_seed": rng_seed,
        "num_breaks": num_breaks,
        "break_duration": int(fields["Break Duration (sec)"])
        if str(fields["Break Duration (sec)"]).strip()
        else 0,
        "num_measures": num_measures,
        "save_preset": bool(fields["Save as Preset"]),
        "counterbalance": False,  # Legacy field, forced False
    }

    return result


# =============================================================================
# Page 5: Flowchart & Confirmation
# =============================================================================


def generate_flowchart(config):
    """
    Generate a text-based flowchart matching the actual WAND task order.
    Dynamically generates the flow for any number of blocks.
    Uses custom_block_order from Block Builder if present.
    """
    # Check for custom block order from Block Builder
    custom_order = config.get("custom_block_order")
    if custom_order and config.get("task_mode") != "Practice Only":
        return generate_flowchart_from_custom_order(custom_order, config)

    seq_enabled = config.get("sequential_enabled", True)
    spa_enabled = config.get("spatial_enabled", True)
    dual_enabled = config.get("dual_enabled", True)
    counterbalance = config.get("counterbalance_spatial_dual", False)

    seq_blocks = config.get("sequential", {}).get("blocks", 5)
    spa_blocks = config.get("spatial", {}).get("blocks", 4)
    dual_blocks = config.get("dual", {}).get("blocks", 4)

    spa_comp = config.get("spatial", {}).get("time_compression", True)
    dual_comp = config.get("dual", {}).get("time_compression", True)

    breaks = config.get("breaks_schedule", [2, 4])
    measures = config.get("measures_schedule", [2, 3, 4, 5])

    def get_event_str(cycle):
        """Format event string (Measure/Break) for a given cycle."""
        parts = []
        if cycle in measures:
            parts.append("Subjective Measures")
        if cycle in breaks:
            parts.append("Break")
        if parts:
            return f"      ── {' + '.join(parts)} ──"
        return None

    lines = []
    lines.append("TASK ORDER:")
    lines.append("─" * 50)

    if config.get("task_mode") == "Practice Only":
        if spa_enabled:
            lines.append("  → Spatial Demo & Practice")
        if dual_enabled:
            lines.append("  → Dual Demo & Practice")
        if seq_enabled:
            lines.append("  → Sequential Demo & Calibration")
        lines.append("─" * 50)
        lines.append("  Estimated duration: ~20-60 minutes")
        lines.append("  (varies based on participant calibration)")
        return "\n".join(lines)

    # Full Induction - match actual WAND script order
    # Full Induction - match actual WAND script order
    # Force Standard Order: A=SPA, B=DUAL (Counterbalance removed)
    task_A_name, task_B_name = "SPA", "DUAL"
    task_A_enabled, task_B_enabled = spa_enabled, dual_enabled
    task_A_blocks, task_B_blocks = spa_blocks, dual_blocks
    task_A_comp, task_B_comp = spa_comp, dual_comp

    step = 1

    # Add initial measures
    if seq_enabled:
        lines.append(f"      ── Practice/Familiarisation ──")

    # Determine max loops
    max_loops = 0
    if seq_enabled:
        max_loops = max(max_loops, seq_blocks)
    if spa_enabled:
        max_loops = max(max_loops, spa_blocks)
    if dual_enabled:
        max_loops = max(max_loops, dual_blocks)

    for cycle_num in range(1, max_loops + 1):
        # 1. SEQUENTIAL
        if seq_enabled and cycle_num <= seq_blocks:
            lines.append(f"  {step}. SEQ Block {cycle_num}")
            step += 1

        # 2. EVENTS (After Seq)
        evt = get_event_str(cycle_num)
        if evt:
            lines.append(evt)

        # 3. GROUP (A/B vs B/A)
        # Odd: A then B
        # Even: B then A
        if cycle_num % 2 != 0:
            current_order = [
                (task_A_name, task_A_enabled, task_A_blocks, task_A_comp),
                (task_B_name, task_B_enabled, task_B_blocks, task_B_comp),
            ]
        else:
            current_order = [
                (task_B_name, task_B_enabled, task_B_blocks, task_B_comp),
                (task_A_name, task_A_enabled, task_A_blocks, task_A_comp),
            ]

        for name, enabled, blocks, comp_flag in current_order:
            if enabled and cycle_num <= blocks:
                # Map name back to correct display string (SPA/DUAL)
                # name is "SPA" or "DUAL"
                c_mark = "⟳" if comp_flag else ""
                lines.append(f"  {step}. {name} Block {cycle_num} {c_mark}")
                step += 1

    lines.append("─" * 50)
    lines.append(f"  ⟳ = Time compression enabled")

    # Estimate duration using actual timing values
    seq_config = config.get("sequential", {})
    seq_display = seq_config.get("display_duration", 0.8)
    seq_isi = seq_config.get("isi", 1.0)
    seq_block_min = (seq_display + seq_isi) * 164 / 60

    seq_time = seq_blocks * seq_block_min if seq_enabled else 0
    spa_time = spa_blocks * 4.5 if spa_enabled else 0  # Fixed 270s
    dual_time = dual_blocks * 4.5 if dual_enabled else 0  # Fixed 270s
    # Add time for breaks (20s) and measures
    # Approx 1 min per measure, 0.5 min per break
    n_meas = len([m for m in measures if m <= max_loops])
    n_breaks = len([b for b in breaks if b <= max_loops])
    total_time = seq_time + spa_time + dual_time + (n_meas * 1.5) + (n_breaks * 0.5)

    lines.append(f"  Estimated duration: approx. {format_duration(total_time)}")

    return "\n".join(lines)


def generate_flowchart_from_custom_order(block_order, config):
    """
    Generate flowchart from custom block order created by Block Builder.

    Parameters
    ----------
    block_order : list
        List of block dictionaries from Block Builder
    config : dict
        Full configuration

    Returns
    -------
    str
        Formatted flowchart text
    """
    spa_comp = config.get("spatial", {}).get("time_compression", True)
    dual_comp = config.get("dual", {}).get("time_compression", True)

    lines = []
    lines.append("TASK ORDER:")
    lines.append("─" * 50)
    lines.append("      ── Practice/Familiarisation ──")

    step = 1
    seq_count = spa_count = dual_count = 0
    total_time = 0

    for block in block_order:
        block_type = block.get("type", "")

        # Skip start/end blocks
        if block_type in ("start", "end"):
            continue

        if block_type == "seq":
            seq_count += 1
            lines.append(f"  {step}. SEQ Block {seq_count}")
            step += 1
            total_time += 5
        elif block_type == "spa":
            spa_count += 1
            c_mark = "⟳" if spa_comp else ""
            lines.append(f"  {step}. SPA Block {spa_count} {c_mark}")
            step += 1
            total_time += 4.5
        elif block_type == "dual":
            dual_count += 1
            c_mark = "⟳" if dual_comp else ""
            lines.append(f"  {step}. DUAL Block {dual_count} {c_mark}")
            step += 1
            total_time += 4.5
        elif block_type == "break":
            lines.append("      ── Break ──")
            total_time += 0.5
        elif block_type == "measures":
            lines.append("      ── Subjective Measures ──")
            total_time += 1.5

    lines.append("─" * 50)
    lines.append("  ⟳ = Time compression enabled")
    lines.append(f"  Estimated duration: approx. {format_duration(total_time)}")

    return "\n".join(lines)


def show_page5_mode_selection(config):
    """
    Page 5: Select run mode (Practice or Full Induction).

    Parameters
    ----------
    config : dict
        Complete configuration

    Returns
    -------
    str or None
        "Full Induction", "Practice Only", or None if cancelled
    """
    # Calculate duration for Full Induction
    # Check for custom block order from Block Builder
    custom_order = config.get("custom_block_order")

    if custom_order:
        # Calculate from actual Block Builder selection with timing values
        seq_config = config.get("sequential", {})
        seq_display = seq_config.get("display_duration", 0.8)
        seq_isi = seq_config.get("isi", 1.0)
        seq_trials = 164  # Fixed trials per SEQ block
        seq_block_min = (seq_display + seq_isi) * seq_trials / 60  # minutes per block

        seq_time = spa_time = dual_time = 0
        n_breaks = n_meas = 0

        for block in custom_order:
            block_type = block.get("type", "")
            if block_type == "seq":
                seq_time += seq_block_min
            elif block_type == "spa":
                spa_time += 4.5  # Fixed 270s
            elif block_type == "dual":
                dual_time += 4.5  # Fixed 270s
            elif block_type == "break":
                n_breaks += 1
            elif block_type == "measures":
                n_meas += 1

        full_duration = int(
            seq_time + spa_time + dual_time + (n_meas * 1.5) + (n_breaks * 0.5)
        )
    else:
        # Fallback to config counts with timing values
        seq_enabled = config.get("sequential_enabled", True)
        spa_enabled = config.get("spatial_enabled", True)
        dual_enabled = config.get("dual_enabled", True)

        seq_blocks = config.get("sequential", {}).get("blocks", 5) if seq_enabled else 0
        spa_blocks = config.get("spatial", {}).get("blocks", 4) if spa_enabled else 0
        dual_blocks = config.get("dual", {}).get("blocks", 4) if dual_enabled else 0

        # Calculate SEQ time using actual timing values
        seq_config = config.get("sequential", {})
        seq_display = seq_config.get("display_duration", 0.8)
        seq_isi = seq_config.get("isi", 1.0)
        seq_trials = 164
        seq_block_min = (seq_display + seq_isi) * seq_trials / 60

        seq_time = seq_blocks * seq_block_min if seq_enabled else 0
        spa_time = spa_blocks * 4.5 if spa_enabled else 0  # Fixed 270s
        dual_time = dual_blocks * 4.5 if dual_enabled else 0  # Fixed 270s

        # Use counts instead of schedules
        n_meas = config.get("num_measures", 4)
        n_breaks = config.get("num_breaks", 2)

        full_duration = int(
            seq_time + spa_time + dual_time + (n_meas * 1.5) + (n_breaks * 0.5)
        )

    fields = OrderedDict()
    fields["Select_Mode"] = [
        "Practice Only (~20-60 min)",
        f"Full Induction (~{format_duration(seq_time + spa_time + dual_time + (n_meas * 1.5) + (n_breaks * 0.5))})",
    ]

    dlg = gui.DlgFromDict(
        dictionary=fields,
        title="WAND - Page 5/6: Select Run Mode",
        sortKeys=False,
    )

    if not dlg.OK:
        return None

    selected = fields["Select_Mode"]

    if "Full Induction" in selected:
        return "Full Induction"
    elif "Practice" in selected:
        return "Practice Only"
    else:
        return "Practice Only"


def show_page6_confirmation(config):
    """
    Page 6: Show task order for selected mode and confirm launch.

    Parameters
    ----------
    config : dict
        Complete configuration with task_mode set

    Returns
    -------
    bool
        True if confirmed, False if cancelled
    """
    flowchart = generate_flowchart(config)
    seed_display = str(config.get("rng_seed")) if config.get("rng_seed") else "Random"
    mode = config.get("task_mode", "Practice Only")

    summary = f"""
══════════════════════════════════════════════════════
  {mode.upper()} - TASK ORDER
══════════════════════════════════════════════════════

  Study:          {config.get('study_name', 'Unnamed')}
  Participant:    {config.get('participant_id', 'Unknown')}
  RNG Seed:       {seed_display}

──────────────────────────────────────────────────────
{flowchart}
══════════════════════════════════════════════════════

  Click OK to LAUNCH the experiment
  Click Cancel to go back
"""

    dlg = gui.Dlg(title=f"WAND - Page 6/6: Confirm & Launch ({mode})")
    dlg.addText(summary)
    dlg.show()

    return dlg.OK


# =============================================================================
# Build Final Configuration
# =============================================================================


def build_final_config(page1, page2, page3, page4):
    """
    Combine all page data into final configuration.

    Parameters
    ----------
    page1 : dict
        Study setup data
    page2 : dict
        Task selection data
    page3 : dict
        Timing data
    page4 : dict
        Options data

    Returns
    -------
    dict
        Complete configuration
    """
    config = {
        # Metadata
        "study_name": page1["study_name"],
        "participant_id": page1["participant_id"],
        "created": datetime.now().isoformat(),
        "last_modified": datetime.now().isoformat(),
        # Task enables
        "sequential_enabled": page2["sequential_enabled"],
        "spatial_enabled": page2["spatial_enabled"],
        "dual_enabled": page2["dual_enabled"],
        # Sequential settings
        "sequential": {
            "blocks": page2["sequential_blocks"],
            "display_duration": page3.get("seq_display", 0.8),
            "isi": page3.get("seq_isi", 1.0),
            "trials_per_block": 164,
            "distractors_enabled": page3.get("seq_distractors", True),
        },
        # Spatial settings
        "spatial": {
            "blocks": page2["spatial_blocks"],
            "display_duration": page3.get("spa_display", 1.0),
            "isi": page3.get("spa_isi", 1.0),
            "time_compression": page3.get("spa_compression", True),
        },
        # Dual settings
        "dual": {
            "blocks": page2["dual_blocks"],
            "display_duration": page3.get("dual_display", 1.0),
            "isi": page3.get("dual_isi", 1.2),
            "time_compression": page3.get("dual_compression", True),
        },
        # Global options
        # "n_back_level": page4["n_back_level"],  # REMOVED
        "fullscreen": page4["fullscreen"],
        "rng_seed": page4["rng_seed"],
        "counterbalance_spatial_dual": page4["counterbalance"],
        "num_breaks": page4.get("num_breaks", 2),
        "break_duration": page4.get("break_duration", 20),
        "num_measures": page4.get("num_measures", 4),
        # Note: breaks_schedule and measures_schedule will be populated
        # from custom_block_order after Block Builder step
    }

    return config


def extract_schedules(block_order):
    """
    Extract breaks_schedule and measures_schedule from the visual block order.

    Logic:
    - Scans blocks linearly.
    - Counts task blocks (SEQ/SPA/DUAL) to determine current cycle.
    - If a Break/Measure is found, it is assigned to the current cycle.

    Note: Block builder generates labels like "SEQ", "SPA" without numbers,
    so we count task blocks seen to determine the cycle.
    """
    breaks = set()
    measures = set()
    task_block_count = 0  # Count of task blocks seen so far

    for block in block_order:
        block_type = block.get("type", "")

        # Count task blocks to determine cycle
        if block_type in ("seq", "spa", "dual"):
            task_block_count += 1

        # Assign breaks/measures to current cycle (count of task blocks seen)
        # Use max(1, count) so events before first task go to cycle 1
        current_cycle = max(1, task_block_count)

        if block_type == "break":
            breaks.add(current_cycle)
        elif block_type == "measures":
            measures.add(current_cycle)

    return sorted(list(breaks)), sorted(list(measures))


def generate_default_schedules(num_breaks, num_measures, total_cycles):
    """Generate default distributed schedules if Block Builder is skipped."""
    breaks = []
    if num_breaks > 0:
        if num_breaks == 1:
            breaks = [max(1, total_cycles // 2)]
        else:
            # Spread evenly, e.g. 2 breaks in 5 cycles -> [2, 4]
            # Use simple step logic
            # intervals = num_breaks + 1
            # step = total / intervals
            step = total_cycles / (num_breaks + 1)
            breaks = [int(step * (i + 1)) for i in range(num_breaks)]

    measures = []
    if num_measures > 0:
        if num_measures >= total_cycles:
            measures = list(range(1, total_cycles + 1))
        else:
            step = total_cycles / (num_measures + 1)
            measures = [int(step * (i + 1)) + 1 for i in range(num_measures)]

    # Ensure unique, valid, and sorted
    breaks = sorted(list(set([max(1, min(total_cycles, b)) for b in breaks])))
    measures = sorted(list(set([max(1, min(total_cycles, m)) for m in measures])))

    return breaks, measures


# =============================================================================
# Save Runtime Config (for main scripts)
# =============================================================================


def save_runtime_config(config):
    """
    Save configuration for main scripts to read.

    Sets WAND_GUI_CONFIG environment variable.
    """
    config_filename = f"gui_config_{config['participant_id']}.json"
    config_path = os.path.join(DATA_DIR, config_filename)

    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2)

    os.environ["WAND_GUI_CONFIG"] = config_path
    print(f"[GUI] Runtime config saved: {config_path}")

    return config_path


# =============================================================================
# Launch Experiment
# =============================================================================


def launch_experiment(config):
    """
    Launch the appropriate WAND script.
    """
    task_mode = config["task_mode"]

    print("\n" + "=" * 60)
    print("WAND Launcher - Starting Experiment")
    print("=" * 60)
    print(f"  Study:        {config['study_name']}")
    print(f"  Participant:  {config['participant_id']}")
    print(f"  Task Mode:    {task_mode}")
    # print(f"  N-back:       {config['n_back_level']}-back") # REMOVED
    print("=" * 60 + "\n")

    # --- Apply fullscreen setting to params.json BEFORE importing scripts ---
    # Scripts read fullscreen from params.json at import time, so we must
    # update it before the import statement runs.
    try:
        params_path = os.path.join(CONFIG_DIR, "params.json")
        with open(params_path, "r", encoding="utf-8") as f:
            params = json.load(f)

        # Update window settings
        if "window" not in params:
            params["window"] = {}
        params["window"]["fullscreen"] = config.get("fullscreen", False)

        with open(params_path, "w", encoding="utf-8") as f:
            json.dump(params, f, indent=2)

        print(f"[GUI] Fullscreen mode: {config.get('fullscreen', False)}")
    except Exception as e:
        print(f"[GUI] Warning: Could not update params.json: {e}")
    # --- End fullscreen fix ---

    if task_mode == "Practice Only":
        print("[GUI] Launching Practice Protocol...")
        from wand_nback import practice_plateau as WAND_practice_plateau

        # Patch the participant ID prompt to return GUI value
        def patched_prompt_participant_id(win):
            """Return GUI participant ID instead of showing dialog."""
            print("[GUI] Using pre-configured participant ID from launcher")
            return config["participant_id"]

        # Patch get_practice_options to return GUI values
        def patched_get_practice_options(win):
            """Return GUI config values instead of showing dialog."""
            print("[GUI] Using pre-configured practice options from launcher")
            return {
                "Seed": config.get("rng_seed"),
                "Distractors": config.get("sequential", {}).get(
                    "distractors_enabled", True
                ),
            }

        # Apply patches
        WAND_practice_plateau._prompt_participant_id = patched_prompt_participant_id
        WAND_practice_plateau.get_practice_options = patched_get_practice_options

        # Try to bring window to front
        try:
            WAND_practice_plateau.win.winHandle.activate()
        except:
            pass

        WAND_practice_plateau.main()

    else:  # Full Induction
        print("[GUI] Launching Full Induction Protocol...")
        print("[GUI] Please wait - experiment window will appear shortly...")

        from wand_nback import full_induction as WAND_full_induction

        # Patch removed: WAND_full_induction.py now handles config loading and N-back prompting internally.
        # Try to bring window to front
        try:
            WAND_full_induction.win.winHandle.activate()
            print("[GUI] Window activated")
        except Exception as e:
            print(f"[GUI] Note: Could not activate window: {e}")

        WAND_full_induction.main_task_flow()


# =============================================================================
# Main Entry Point
# =============================================================================


def show_splash_screen(duration_ms=3000):
    """
    Display a professional splash screen with the WAND logo and shimmer effect.

    Parameters
    ----------
    duration_ms : int
        How long to display the splash screen in milliseconds.
    """
    try:
        import tkinter as tk

        from PIL import Image, ImageTk
    except ImportError:
        print("[GUI] Splash screen skipped (PIL not available)")
        return

    logo_path = os.path.join(BASE_DIR, "logo", "WAND.png")
    if not os.path.exists(logo_path):
        print("[GUI] Splash screen skipped (logo not found)")
        return

    # Create borderless window
    splash = tk.Tk()
    splash.overrideredirect(True)  # Remove window decorations
    splash.configure(bg="#0a0a0a")  # Dark background

    # Get screen dimensions and center the splash
    screen_width = splash.winfo_screenwidth()
    screen_height = splash.winfo_screenheight()
    splash_width = 500
    splash_height = 400
    x = (screen_width - splash_width) // 2
    y = (screen_height - splash_height) // 2
    splash.geometry(f"{splash_width}x{splash_height}+{x}+{y}")

    # Keep splash on top
    splash.attributes("-topmost", True)

    # Create main frame
    main_frame = tk.Frame(splash, bg="#0a0a0a")
    main_frame.pack(fill=tk.BOTH, expand=True)

    # Load and display logo
    logo_label = None
    try:
        img = Image.open(logo_path)
        # Resize while maintaining aspect ratio
        img.thumbnail((200, 200), Image.Resampling.LANCZOS)
        logo_img = ImageTk.PhotoImage(img)

        logo_label = tk.Label(main_frame, image=logo_img, bg="#0a0a0a")
        logo_label.image = logo_img  # Keep reference
        logo_label.pack(pady=(50, 20))
    except Exception as e:
        print(f"[GUI] Could not load logo: {e}")

    # Title text
    title_label = tk.Label(
        main_frame,
        text="WAND Protocol",
        font=("Segoe UI", 24, "bold"),
        fg="#00d4ff",  # Cyan to match logo
        bg="#0a0a0a",
    )
    title_label.pack(pady=(0, 5))

    # Subtitle
    subtitle_label = tk.Label(
        main_frame,
        text="Working-memory Adaptive-fatigue with N-back Difficulty",
        font=("Segoe UI", 11),
        fg="#888888",
        bg="#0a0a0a",
    )
    subtitle_label.pack(pady=(0, 20))

    # Version and author
    info_label = tk.Label(
        main_frame,
        text="v1.1.1  •  Brodie E. Mangan",
        font=("Segoe UI", 9),
        fg="#555555",
        bg="#0a0a0a",
    )
    info_label.pack(pady=(0, 10))

    # Loading indicator
    loading_label = tk.Label(
        main_frame,
        text="Loading...",
        font=("Segoe UI", 9, "italic"),
        fg="#444444",
        bg="#0a0a0a",
    )
    loading_label.pack(side=tk.BOTTOM, pady=20)

    # Elegant fade-in animation
    splash.attributes("-alpha", 0.0)
    fade_step = [0]

    def fade_in():
        """Smoothly fade in the splash screen."""
        alpha = fade_step[0] / 20.0  # 20 steps to full opacity
        splash.attributes("-alpha", min(alpha, 1.0))
        fade_step[0] += 1
        if fade_step[0] <= 20:
            splash.after(40, fade_in)  # ~0.8 second total fade

    # Animated loading dots
    dot_count = [0]
    animation_id = [None]  # Track callback ID for cleanup

    def animate_loading():
        """Animate the loading text with moving dots."""
        dots = "." * (dot_count[0] % 4)
        loading_label.config(text=f"Loading{dots}")
        dot_count[0] += 1
        animation_id[0] = splash.after(400, animate_loading)

    def cleanup_and_destroy():
        """Cancel pending callbacks and destroy window."""
        if animation_id[0]:
            try:
                splash.after_cancel(animation_id[0])
            except Exception:
                pass
        splash.destroy()

    # Start animations
    splash.after(50, fade_in)
    splash.after(100, animate_loading)

    # Auto-close after duration (with proper cleanup)
    splash.after(duration_ms, cleanup_and_destroy)

    # Run the splash
    splash.mainloop()


def main():
    """Main entry point - multi-page configuration wizard."""

    # Show splash screen first
    show_splash_screen()

    print("\n" + "=" * 60)
    print("WAND - Working-memory Adaptive-fatigue with N-back Difficulty")
    print("GUI Launcher v1.1.1")
    print("=" * 60 + "\n")

    step = 1
    base_config = {}
    pages = {}  # Store results from each page

    while step > 0:
        # ─────────────────────────────────────────────────────────────────────────
        # Page 1: Study Setup
        # ─────────────────────────────────────────────────────────────────────────
        if step == 1:
            page1 = show_page1_study_setup()
            if page1 is None:
                # Show exit confirmation
                confirm_dlg = gui.Dlg(title="Exit WAND?")
                confirm_dlg.addText("Are you sure you want to exit the launcher?")
                confirm_dlg.show()
                if confirm_dlg.OK:
                    print("[GUI] User confirmed exit. Goodbye!")
                    sys.exit(0)
                else:
                    continue  # Stay on Page 1

            pages["page1"] = page1

            # Preset Logic
            if page1["load_preset"] != "<Create New>":
                print(f"[GUI] Using preset '{page1['load_preset']}'")
                loaded = load_preset(page1["load_preset"])
                # Preserve identity from Page 1
                loaded["participant_id"] = page1["participant_id"]
                loaded["study_name"] = page1["study_name"]
                base_config = loaded
                # Skip to Confirmation
                step = 5

            else:
                # Create New -> setup defaults
                base_config = DEFAULT_CONFIG.copy()
                base_config["participant_id"] = page1["participant_id"]
                base_config["study_name"] = page1["study_name"]
                step = 2

        # ─────────────────────────────────────────────────────────────────────────
        # Page 2: Task Selection
        # ─────────────────────────────────────────────────────────────────────────
        elif step == 2:
            page2 = show_page2_task_selection(base_config)
            if page2 is None:
                # Back to Page 1
                step = 1
                continue

            pages["page2"] = page2
            # Update base_config so Page 3/4 show correct defaults
            base_config["sequential_enabled"] = page2["sequential_enabled"]
            base_config["spatial_enabled"] = page2["spatial_enabled"]
            base_config["dual_enabled"] = page2["dual_enabled"]
            base_config["sequential"]["blocks"] = page2["sequential_blocks"]
            base_config["spatial"]["blocks"] = page2["spatial_blocks"]
            base_config["dual"]["blocks"] = page2["dual_blocks"]
            step = 3

        # ─────────────────────────────────────────────────────────────────────────
        # Page 3: Task Timings
        # ─────────────────────────────────────────────────────────────────────────
        elif step == 3:
            page3 = show_page3_task_timings(base_config)
            if page3 is None:
                # Back to Page 2
                step = 2
                continue

            pages["page3"] = page3
            step = 4

        # ─────────────────────────────────────────────────────────────────────────
        # Page 4: Options
        # ─────────────────────────────────────────────────────────────────────────
        elif step == 4:
            page4 = show_page4_options(base_config)
            if page4 is None:
                # Back to Page 3
                step = 3
                continue

            pages["page4"] = page4
            step = 5

        # ─────────────────────────────────────────────────────────────────────────
        # Page 5: Block Builder (Visual Block Ordering)
        # ─────────────────────────────────────────────────────────────────────────
        elif step == 5:
            # Build config for block builder
            if "page2" in pages:
                # Full wizard path
                temp_config = build_final_config(
                    pages["page1"], pages["page2"], pages["page3"], pages["page4"]
                )
            else:
                # Preset path
                temp_config = base_config

            # Show block builder if available
            if BLOCK_BUILDER_AVAILABLE:
                print("[GUI] Opening Block Builder...")
                block_order = show_block_builder(temp_config)

                if block_order is None:
                    # User cancelled -> Back to Page 4
                    if "page2" in pages:
                        step = 4
                    else:
                        step = 1  # Back to Study Setup for preset path
                    continue

                pages["block_order"] = block_order
                print(f"[GUI] Block order configured: {len(block_order)} blocks")
            else:
                print("[GUI] Block builder not available, using default order")
                pages["block_order"] = None

            step = 6

        # ─────────────────────────────────────────────────────────────────────────
        # Page 6: Mode Selection (Practice or Full Induction)
        # ─────────────────────────────────────────────────────────────────────────
        elif step == 6:
            # Build Final Config first
            if "page2" in pages:
                # Full wizard path
                final_config = build_final_config(
                    pages["page1"], pages["page2"], pages["page3"], pages["page4"]
                )
            else:
                # Preset path
                final_config = base_config

            # Calculate max cycles for default schedules
            seq_b = (
                final_config["sequential"]["blocks"]
                if final_config["sequential_enabled"]
                else 0
            )
            spa_b = (
                final_config["spatial"]["blocks"]
                if final_config["spatial_enabled"]
                else 0
            )
            dual_b = (
                final_config["dual"]["blocks"] if final_config["dual_enabled"] else 0
            )
            total_cycles = max(seq_b, spa_b, dual_b)

            # Attach custom block order if configured AND extract compatible schedules
            if pages.get("block_order"):
                final_config["custom_block_order"] = pages["block_order"]
                print("[GUI] Custom block order attached to config")

                # Extract schedules for standard loop compatibility
                b_sched, m_sched = extract_schedules(pages["block_order"])
                final_config["breaks_schedule"] = b_sched
                final_config["measures_schedule"] = m_sched
                print(
                    f"[GUI] Extracted schedules from Block Builder: Breaks={b_sched}, Measures={m_sched}"
                )

            else:
                # No Block Builder used - generate defaults from Page 4 counts
                n_br = final_config.get("num_breaks", 0)
                n_meas = final_config.get("num_measures", 0)

                b_sched, m_sched = generate_default_schedules(
                    n_br, n_meas, total_cycles
                )
                final_config["breaks_schedule"] = b_sched
                final_config["measures_schedule"] = m_sched
                print(
                    f"[GUI] Generated default schedules from counts: Breaks={b_sched}, Measures={m_sched}"
                )

            # MODE SELECTION
            selected_mode = show_page5_mode_selection(final_config)

            if selected_mode is None:
                # User cancelled -> Back to Block Builder
                step = 5
                continue

            final_config["task_mode"] = selected_mode

            # WARN: Full Induction without Sequential won't collect behavioural metrics
            if selected_mode == "Full Induction" and not final_config.get(
                "sequential_enabled", True
            ):
                print(
                    "[GUI] WARNING: Sequential task disabled - no behavioural metrics will be collected"
                )

                # Show user-visible warning dialog
                from psychopy import gui as psychopy_gui

                warn_dlg = psychopy_gui.Dlg(title="Warning: No Behavioural Metrics")
                warn_dlg.addText(
                    "Sequential N-back is DISABLED.\n\n"
                    "No behavioural metrics (d', criterion, RT) will be collected.\n\n"
                    "Click OK to continue anyway."
                )
                warn_dlg.show()

            pages["final_config"] = final_config
            print(f"[GUI] Selected mode: {selected_mode}")
            step = 7

        # ─────────────────────────────────────────────────────────────────────────
        # Page 7: Confirmation with Task Order
        # ─────────────────────────────────────────────────────────────────────────
        elif step == 7:
            final_config = pages["final_config"]

            confirmed = show_page6_confirmation(final_config)

            if not confirmed:
                # User cancelled -> Back to mode selection
                step = 6
                continue

            # --- LAUNCH ---

            # Save preset if requested (only in full wizard mode)
            if "page4" in pages and pages["page4"].get("save_preset", False):
                save_preset(final_config, final_config["study_name"])

            save_runtime_config(final_config)

            try:
                launch_experiment(final_config)
            except Exception as e:
                print(f"\n[GUI] ERROR: {e}")
                from psychopy import gui as gui_err

                dlg = gui_err.Dlg(title="Error")
                dlg.addText(f"Experiment error:\n\n{str(e)}")
                dlg.show()
                raise

            # Exit loop after launch
            break


if __name__ == "__main__":
    main()
