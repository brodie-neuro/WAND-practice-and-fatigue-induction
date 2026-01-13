#!/usr/bin/env python3
"""
WAND — Practice (Plateau Calibration)

Practice session protocol for calibrating working-memory performance prior to
cognitive-fatigue induction using the WAND model (Working-memory Adaptive-fatigue
with N-back Difficulty).

Participants complete Spatial, Dual, and Sequential N-back tasks with guided
demos and brief feedback until performance stabilises.

Author
------
Brodie E. Mangan

Version
-------
1.1.0

Environment
-----------
Tested on Windows, Python 3.8. See requirements.txt for exact pins.

Configuration
-------------
See wand_common.py and the config/ folder for core experiment parameters,
text strings, and window settings.

License
-------
MIT (see LICENSE).
"""
# =============================================================================
#  SECTION 1: IMPORTS & SETUP
# =============================================================================
import argparse
import csv
import datetime
import logging
import math
import os
import random
import sys
import time
import traceback
from typing import List, Tuple

from psychopy import core, event, visual

from wand_common import (
    collect_trial_response,
    create_grid,
    create_grid_lines,
    display_dual_stimulus,
    display_grid,
    draw_grid,
    emergency_quit,
    generate_dual_nback_sequence,
    generate_positions_with_matches,
    generate_sequential_image_sequence,
    get_level_color,
    get_param,
    get_text,
    install_error_hook,
    load_config,
    load_gui_config,
    prompt_choice,
    prompt_text_input,
    set_grid_lines,
    show_text_screen,
)

if getattr(sys, "frozen", False):
    # if you’ve bundled into an executable
    base_dir = sys._MEIPASS
else:
    base_dir = os.path.dirname(os.path.abspath(__file__))

data_dir = os.path.join(base_dir, "data")
os.makedirs(data_dir, exist_ok=True)

CONFIG_DIR = os.path.join(base_dir, "config")
load_config(lang="en", config_dir=CONFIG_DIR)

# Window configuration
WIN_FULLSCR = bool(get_param("window.fullscreen", False))
WIN_SIZE = tuple(get_param("window.size", [1650, 1000]))
WIN_MONITOR = str(get_param("window.monitor", "testMonitor"))
WIN_BG = get_param("window.background_color", [-1, -1, -1])
WIN_COLORSP = get_param("window.color_space", "rgb")
WIN_USEFBO = bool(get_param("window.use_fbo", True))

# =============================================================================
#  SECTION 2: LOGGING & DATA MANAGEMENT
# =============================================================================
def _prompt_participant_id(win) -> str:
    """
    Prompt the experimenter for a participant ID via an on-screen textbox.

    Returns
    -------
    str
        The participant ID entered by the experimenter. If Escape is
        pressed, returns an empty string.
    """
    text_style = dict(height=24, color="white", wrapWidth=900)

    pid = prompt_text_input(
        win,
        get_text("get_pid"),
        initial_text="",
        allow_empty=False,
        restrict_digits=False,
        text_style=text_style,
    )
    return pid


def init_seq_logger(win):
    """
    Initialise the Sequential-N-back CSV logger **once** per session.

    The function performs four steps:

    1. Calls :func:`_prompt_participant_id` to obtain an identifier.
    2. Ensures a ``data/`` sub-directory exists next to the script or
       bundled executable.
    3. Constructs an absolute path of the form
       ``./data/seq_<PID>.csv`` and stores it in the global ``CSV_PATH``.
    4. Resets the private section tracker ``_last_logged_level`` so the
       very first call to :func:`log_seq_block` starts a fresh section.

    Parameters
    ----------
    win : psychopy.visual.Window
        The active PsychoPy window (needed for the ID prompt).

    Returns
    -------
    tuple(str, str)
        ``(PARTICIPANT_ID, CSV_PATH)`` – both are also placed in
        globals of the same names for downstream helpers.
    """
    global PARTICIPANT_ID, CSV_PATH, _last_logged_level

    PARTICIPANT_ID = _prompt_participant_id(win)

    data_dir = os.path.join(base_dir, "data")
    os.makedirs(data_dir, exist_ok=True)

    CSV_PATH = os.path.join(data_dir, f"seq_{PARTICIPANT_ID}.csv")
    _last_logged_level = None  # reset section tracker

    return PARTICIPANT_ID, CSV_PATH


def log_seq_block(
    level: int, block_no: int, accuracy: float, errors: int, lapses: int
) -> None:
    """
    Append a one-line summary of a Sequential-N-back block to
    ``seq_<PID>.csv``.

    Parameters
    ----------
    level : int
        The N-back level of the block (2 or 3).
    block_no : int
        Sequential counter of *normal-speed* blocks (starts at 1).
    accuracy : float
        Block accuracy **in percent** (e.g. 78.34).
    errors : int
        Number of incorrect key presses.
    lapses : int
        Number of missed responses (no key press before deadline).

    Notes
    -----
    * A new blank-line-separated *section* – complete with a header row –
      is started whenever the N-back level changes. This keeps 2-back and
      3-back data visually distinct.
    * On the very first invocation the function also writes a provenance
      header with a timestamp and participant ID.
    """
    global _last_logged_level

    new_section = (_last_logged_level is None) or (_last_logged_level != level)
    _last_logged_level = level

    file_exists = os.path.isfile(CSV_PATH)
    with open(CSV_PATH, "a", newline="") as f:
        w = csv.writer(f)

        # very first write → provenance header
        if not file_exists:
            w.writerow(
                [
                    f"Created {datetime.datetime.now():%Y-%m-%d %H:%M}",
                    "Participant",
                    PARTICIPANT_ID,
                ]
            )
            w.writerow(["level", "block", "accuracy_pct", "errors", "lapses"])

        # start a new section if the N-back level just changed
        if new_section and file_exists:
            w.writerow([])  # visual gap
            w.writerow(["level", "block", "accuracy_pct", "errors", "lapses"])

        w.writerow([level, block_no, f"{accuracy:.2f}", errors, lapses])


# =============================================================================
#  SECTION 3: GLOBAL UTILITIES & CONFIGURATION
# =============================================================================
# CLI Argument Parsing
parser = argparse.ArgumentParser(add_help=False)
parser.add_argument(
    "--seed", type=int, help="Fix RNG. If omitted, the wizard will ask for one."
)
parser.add_argument(
    "--distractors",
    choices=["on", "off"],
    help="Toggle 200-ms distractor flashes. If omitted, the wizard will ask.",
)

args, _ = parser.parse_known_args()
GLOBAL_SEED = args.seed
DISTRACTORS_ENABLED = None if args.distractors is None else (args.distractors != "off")

skip_to_next_stage = False
grid_lines = []


def _apply_seed(seed_val):
    """
    Seed Python and (optionally) NumPy RNGs once.

    Parameters
    ----------
    seed_val : Optional[int]
        Seed to apply. If None, no action is taken.

    Returns
    -------
    None
    """
    if seed_val is None:
        return
    random.seed(seed_val)
    try:
        import numpy as np

        np.random.seed(seed_val)
    except ModuleNotFoundError:
        pass


def set_skip_flag():
    """Mark that the user has requested to skip the remainder of the current phase.

    When bound to a global key ('5'), this lets any running practice/demo block
    check `skip_to_next_stage` and exit early.

    Side effects:
        Sets the module‐level boolean `skip_to_next_stage` to True.

    Returns:
        None
    """
    global skip_to_next_stage
    skip_to_next_stage = True


event.globalKeys.add(key="5", func=set_skip_flag)


def _set_speed(profile: str):
    """Update the global timing profile.

    Sets the two module-level globals that control timing:

    * ``SPEED_PROFILE`` – literal string ``"normal"`` or ``"slow"``
    * ``SPEED_MULT``     – scalar multiplier (read from config)

    Args:
        profile: Desired speed profile – must be ``"normal"`` or ``"slow"``.
    """
    global SPEED_PROFILE, SPEED_MULT
    SPEED_PROFILE = profile
    SPEED_MULT = float(get_param(f"practice.speed_multiplier.{profile}", 1.0))
    logging.info(f"Speed profile set to: {profile.upper()} (multiplier={SPEED_MULT})")


# Defaults pulled from config (with safe fallbacks)
SPEED_PROFILE = get_param("practice.speed_default", "normal")
SPEED_MULT = float(get_param(f"practice.speed_multiplier.{SPEED_PROFILE}", 1.0))


def T(sec: float) -> float:
    """
    Scale a base duration by the current speed multiplier.

    Parameters
    ----------
    sec : float
        Base duration in seconds (at normal speed).

    Returns
    -------
    float
        Scaled duration in seconds (`sec * SPEED_MULT`).
    """
    return sec * SPEED_MULT


# GUI Configuration cache (loaded once at startup if available)
_GUI_CONFIG = None
_GUI_CONFIG_LOADED = False


def _get_gui_config():
    """Get cached GUI config, loading it once if available."""
    global _GUI_CONFIG, _GUI_CONFIG_LOADED
    if not _GUI_CONFIG_LOADED:
        try:
            _GUI_CONFIG = load_gui_config()
            if _GUI_CONFIG:
                print("[PRACTICE] Using timing config from launcher")
        except Exception:
            _GUI_CONFIG = None
        _GUI_CONFIG_LOADED = True
    return _GUI_CONFIG


def get_gui_timing(task_type, param_name, default):
    """
    Get timing parameter from launcher GUI config, falling back to default.

    The value returned is the BASE timing before speed multiplier is applied.
    This allows slow mode to work on top of GUI-configured timings.

    Parameters
    ----------
    task_type : str
        One of "sequential", "spatial", "dual"
    param_name : str
        One of "display_duration", "isi"
    default : float
        Fallback value if GUI config not available.

    Returns
    -------
    float
        The timing value in seconds.
    """
    gui_config = _get_gui_config()
    if gui_config and task_type in gui_config:
        return float(gui_config[task_type].get(param_name, default))
    return default


# Stimulus setup
image_dir = os.path.join(base_dir, "Abstract Stimuli", "apophysis")
image_files = [f for f in os.listdir(image_dir) if f.endswith(".png")]

if len(image_files) < 24:
    print("Not enough images found in directory")
    sys.exit(1)

# =============================================================================
#  SECTION 4: USER INTERACTION & MENUS
# =============================================================================
def prompt_starting_level():
    """
    Prompt for the starting N-back level for sequential practice.
    Returns either 2 or 3, or calls core.quit() if Escape pressed.
    """
    instructions = get_text("practice_seq_start_level")
    txt = dict(height=24, color="white", wrapWidth=800)

    level = prompt_choice(
        win,
        instructions,
        key_map={"2": 2, "3": 3},
        allow_escape_quit=True,
        text_style=txt,
    )
    return int(level)


def get_practice_options(win):
    """
    Prompt for practice runtime options that were not provided via CLI.

    Returns
    -------
    dict
        Keys:
          - "Seed": Optional[int]
          - "Distractors": bool
    """
    win.mouseVisible = False
    txt = dict(height=24, color="white", wrapWidth=900)

    # Seed: only prompt if not supplied via CLI / params
    seed_val = get_param("runtime.seed", None)
    if seed_val is None:
        seed_str = prompt_text_input(
            win,
            get_text("get_seed"),
            initial_text="",
            allow_empty=True,
            restrict_digits=True,
            text_style=txt,
        )
        seed_val = int(seed_str) if seed_str else None

    # Distractors toggle: only prompt if not supplied via CLI / params
    distractors = get_param("runtime.distractors", None)
    if distractors is None:
        distractors = prompt_choice(
            win,
            get_text("get_distractors"),
            key_map={"y": True, "n": False},
            allow_escape_quit=False,
            text_style=txt,
        )

    win.flip()
    return {"Seed": seed_val, "Distractors": distractors}


def choose_practice_speed(win, current_profile):
    """
    Prompt user to choose practice speed profile.

    Returns
    -------
    str
        "normal" or "slow"
    """
    txt = dict(height=24, color="white", wrapWidth=900)
    msg = get_text("practice_speed_selection", current=current_profile.upper())

    result = prompt_choice(
        win,
        msg,
        key_map={"n": "normal", "s": "slow"},
        allow_escape_quit=True,
        text_style=txt,
    )
    return result


# =============================================================================
#  SECTION 5: VISUAL HELPERS & INSTRUCTIONS
# =============================================================================


def show_task_instructions(win, task_name, n_back_level=None):
    """
    Display task-specific instructions and wait for Space.

    Parameters
    ----------
    win : psychopy.visual.Window
        The PsychoPy window to draw instructions on.
    task_name : str
        One of {"spatial", "dual", "sequential"} (case-insensitive).
    n_back_level : int, optional
        N-back level text for sequential instructions (2 or 3).
    """
    welcome_text = get_text("practice_instructions_intro", task_name=task_name)

    if task_name.lower() == "sequential":
        nb = n_back_level if n_back_level in [2, 3] else 2
        welcome_text += get_text("practice_instructions_seq", nb=nb)
    elif task_name.lower() == "spatial":
        welcome_text += get_text("practice_instructions_spa")
    elif task_name.lower() == "dual":
        welcome_text += get_text("practice_instructions_dual")
    else:
        welcome_text += "(No specific instructions available for this task.)\n\n"

    show_text_screen(win, welcome_text, keys=["space"])


def show_practice_entry_screen(
    win, spa_enabled=True, dual_enabled=True, seq_enabled=True
):
    """
    Display the initial practice welcome screen with dynamic task list.

    Parameters
    ----------
    win : psychopy.visual.Window
        The PsychoPy window.
    spa_enabled : bool
        Whether Spatial N-back is enabled.
    dual_enabled : bool
        Whether Dual N-back is enabled.
    seq_enabled : bool
        Whether Sequential N-back is enabled (always True for practice).
    """
    # Build dynamic task list
    tasks = []
    if spa_enabled:
        tasks.append("A Spatial N-back task")
    if dual_enabled:
        tasks.append("A Dual N-back task")
    if seq_enabled:
        tasks.append("A Sequential N-back task")

    task_count = len(tasks)
    if task_count == 0:
        task_count = 1
        tasks = ["A Sequential N-back task"]  # Fallback

    # Build numbered list
    task_list = "\n".join([f"{i+1}. {t}" for i, t in enumerate(tasks)])

    # Generate welcome text
    if task_count == 1:
        type_word = "one type of task"
    elif task_count == 2:
        type_word = "two types of tasks"
    else:
        type_word = "three types of tasks"

    welcome_text = f"""Welcome to the N-back Practice Session

You will complete {type_word}:

{task_list}

Press 'space' to begin."""

    show_text_screen(win, welcome_text, keys=["space"])


def show_countdown():
    """
    Display a 3-2-1 countdown with 1-second steps.

    Returns
    -------
    None
    """
    for i in [3, 2, 1]:
        countdown_message = visual.TextStim(win, text=str(i), color="white", height=72)
        countdown_message.draw()
        win.flip()
        core.wait(1)


def display_feedback(win, correct, pos=(0, 400)):
    """
    Draw a ✓ (green) or ✗ (red) at a given position.

    Parameters
    ----------
    win : psychopy.visual.Window
        PsychoPy window.
    correct : bool
        True → ✓ (green), False → ✗ (red).
    pos : Tuple[int, int], optional
        Centre position (x, y) in pixels. Default (0, 400).

    Returns
    -------
    None
    """
    feedback_symbol = "✓" if correct else "✗"
    feedback_color = "green" if correct else "red"
    feedback_stim = visual.TextStim(
        win, text=feedback_symbol, color=feedback_color, height=48, pos=pos
    )
    feedback_stim.draw()


def display_block_results(win, task_name, accuracy, *_):
    """
    Display a summary screen after a practice block with tiered, neutral feedback.

    Selects a feedback message based on performance stability to encourage
    focus without inducing competitive compensation strategies.

    Parameters
    ----------
    win : psychopy.visual.Window
        The active PsychoPy window.
    task_name : str
        The name of the task (e.g., 'Spatial').
    accuracy : float
        The accuracy percentage used to select the appropriate feedback tier.
    *_ : Any
        Additional arguments (ignored).
    """
    # Neutral phrases for high stability (>= 82%)
    high_stability_phrases = [
        "Performance is consistent. Maintain this focus.",
        "Responses are stable. Continue as you are.",
        "Tracking well. Keep this rhythm going.",
    ]

    # Neutral phrases for adequate stability (65-82%)
    medium_stability_phrases = [
        "Steady progress. Settling into the task.",
        "Good focus. Let's continue to the next block.",
        "Rhythm is establishing. Keep going.",
        "Consistent effort. Ready for the next round.",
    ]

    # Neutral phrases for lower stability (< 65%)
    low_stability_phrases = [
        "Take a brief moment to reset before continuing.",
        "Focus on the rhythm of the next block.",
        "Reset and prepare for the next round.",
    ]

    # Select message based on performance tier
    if accuracy >= 82:
        feedback_message = random.choice(high_stability_phrases)
    elif accuracy >= 65:
        feedback_message = random.choice(medium_stability_phrases)
    else:
        feedback_message = random.choice(low_stability_phrases)

    results_text = (
        f"{task_name} Practice Block Complete.\n\n"
        f"{feedback_message}\n\n"
        "Press 'space' to continue."
    )

    visual.TextStim(
        win, text=results_text, color="white", height=24, wrapWidth=800
    ).draw()
    win.flip()
    event.waitKeys(keyList=["space"])


# =============================================================================
#  SECTION 6: STIMULUS GENERATION & HELPERS
# =============================================================================


def compute_positions_ref(num_items, ref_index, spacing=110, center_x=0, y=0):
    """
    Compute evenly-spaced x positions so a reference index is centred.

    Parameters
    ----------
    num_items : int
        Number of items to place horizontally.
    ref_index : int
        Index to position at `center_x`.
    spacing : int, optional
        Pixel spacing between items. Default 110.
    center_x : int, optional
        X-coordinate of the reference position. Default 0.
    y : int, optional
        Y-coordinate used for all items. Default 0.

    Returns
    -------
    List[Tuple[int, int]]
        List of (x, y) positions.
    """
    positions = []
    for i in range(num_items):
        x = center_x + (i - ref_index) * spacing
        positions.append((x, y))
    return positions


def draw_sequence(win, seq_images, positions, size=(100, 100), current_idx=None):
    """
    Draw a sequence of images at fixed positions.

    Parameters
    ----------
    win : psychopy.visual.Window
        PsychoPy window.
    seq_images : List[str]
        Image file names.
    positions : List[Tuple[int, int]]
        (x, y) positions for each image.
    size : Tuple[int, int], optional
        (width, height) in pixels. Default (100, 100).
    current_idx : Optional[int], optional
        Index intended for highlighting (not used in current implementation).

    Returns
    -------
    None
    """
    for i, (img_file, pos) in enumerate(zip(seq_images, positions)):
        stim = visual.ImageStim(
            win, image=os.path.join(image_dir, img_file), pos=pos, size=size
        )
        stim.draw()


def draw_center_frame(win, current_pos, size):
    """
    Draw a white rectangular frame around a stimulus.

    Parameters
    ----------
    win : psychopy.visual.Window
        PsychoPy window.
    current_pos : Tuple[int, int]
        (x, y) centre of the stimulus.
    size : Tuple[int, int]
        (width, height) of the stimulus.

    Returns
    -------
    None
    """
    frame = visual.Rect(
        win,
        width=size[0] + 20,
        height=size[1] + 20,
        pos=current_pos,
        lineColor="white",
        fillColor=None,
        lineWidth=2,
    )
    frame.draw()


def draw_n_back_box(win, pos, size, is_match):
    """
    Draw a coloured box around the n-back reference position.

    Parameters
    ----------
    win : psychopy.visual.Window
        PsychoPy window.
    pos : Tuple[int, int]
        (x, y) centre of the n-back stimulus.
    size : Tuple[int, int]
        (width, height) of the n-back stimulus.
    is_match : bool
        True → green border, False → red border.

    Returns
    -------
    None
    """
    border_color = "green" if is_match else "red"
    border = visual.Rect(
        win,
        width=size[0] + 10,
        height=size[1] + 10,
        pos=pos,
        lineColor=border_color,
        lineWidth=4,
        fillColor=None,
    )
    border.draw()


# =============================================================================
#  SECTION 7: TASK DEMONSTRATIONS
# =============================================================================


def prompt_demo_choice(win, task_name):
    """
    Prompt participant to optionally view the demonstration.

    Parameters
    ----------
    win : visual.Window
        PsychoPy window.
    task_name : str
        Name of the task (e.g., "Spatial", "Dual", "Sequential").

    Returns
    -------
    bool
        True if participant wants to watch demo, False to skip.
    """
    prompt_text = (
        f"Would you like to watch a brief demonstration\n"
        f"of the {task_name} task?\n\n"
        f"Press 'D' to watch demonstration\n"
        f"Press SPACE to skip and begin practice"
    )

    text_stim = visual.TextStim(
        win,
        text=prompt_text,
        color="white",
        height=28,
        wrapWidth=800,
    )
    text_stim.draw()
    win.flip()

    keys = event.waitKeys(keyList=["d", "space", "escape"])

    if keys and keys[0] == "d":
        return True
    return False


def show_spatial_demo(win, n=2, num_demo_trials=6, display_duration=1.0, isi=1.0):
    """
    Run a two-pass Spatial N-back demo (normal, then explanatory).

    Parameters
    ----------
    win : psychopy.visual.Window
        PsychoPy window.
    n : int, optional
        N-back level. Default 2.
    num_demo_trials : int, optional
        Number of demo trials. Default 6.
    display_duration : float, optional
        On-screen time (s) per stimulus. Default 1.0.
    isi : float, optional
        Inter-stimulus interval (s). Default 1.0.

    Returns
    -------
    None

    Notes
    -----
    - Pass 1 shows brief feedback from trial > n.
    - Pass 2 keeps the current stimulus visible and overlays explanatory feedback.
    - Press '5' or Escape at any prompt to skip/exit the demo.
    """
    # Generate a 6-trial sequence (using ~50% targets)
    demo_positions = generate_positions_with_matches(
        num_demo_trials, n, target_percentage=0.5
    )

    intro_text = get_text(
        "demo_intro", task_name="Spatial", n=n, num_demo_trials=num_demo_trials
    )
    intro_stim = visual.TextStim(
        win, text=intro_text, color="white", height=24, wrapWidth=800
    )
    intro_stim.draw()
    win.flip()
    keys = event.waitKeys(keyList=["space", "escape", "5"])
    if "escape" in keys:
        emergency_quit(win, "User pressed Escape - exiting experiment.")
    if "5" in keys:
        return

    n_plus_one = n + 1
    pass1_text = get_text(
        "demo_pass1_intro", num_demo_trials=num_demo_trials, n=n, n_plus_one=n_plus_one
    )
    pass1_stim = visual.TextStim(
        win, text=pass1_text, color="white", height=24, wrapWidth=800
    )
    pass1_stim.draw()
    win.flip()
    keys = event.waitKeys(keyList=["space", "escape", "5"])
    if "escape" in keys:
        emergency_quit(win, "User pressed Escape - exiting experiment.")
    if "5" in keys:
        return

    nback_queue = []
    for i, current_pos in enumerate(demo_positions):
        trial_num = i + 1

        # Highlight current position
        display_grid(win, highlight_pos=current_pos, highlight=True, n_level=n)
        win.flip()
        core.wait(display_duration)

        # Remove highlight
        display_grid(win, highlight_pos=None, highlight=False, n_level=n)
        win.flip()
        core.wait(0.2)

        # Feedback from trial 3 onward (brief)
        if trial_num > n:
            old_pos = nback_queue[-n]
            is_target = current_pos == old_pos
            display_grid(win, highlight_pos=None, highlight=False, n_level=n)
            display_feedback(win, is_target, pos=(0, 400))
            win.flip()
            core.wait(0.5)
        else:
            core.wait(0.5)

        core.wait(isi)
        nback_queue.append(current_pos)
        if len(nback_queue) > n:
            nback_queue.pop(0)

    # End of PASS 1
    draw_grid()
    pass1_end_text = get_text("demo_pass1_end")
    pass1_end_stim = visual.TextStim(
        win, text=pass1_end_text, color="white", height=24, wrapWidth=800
    )
    pass1_end_stim.draw()
    win.flip()
    keys = event.waitKeys(keyList=["space", "escape", "5"])
    if "escape" in keys:
        emergency_quit(win, "User pressed Escape - exiting experiment.")
    if "5" in keys:
        return

    pass2_text = get_text("demo_pass2_intro_spa", num_demo_trials=num_demo_trials)
    pass2_stim = visual.TextStim(
        win, text=pass2_text, color="white", height=24, wrapWidth=800
    )
    pass2_stim.draw()
    win.flip()
    keys = event.waitKeys(keyList=["space", "escape", "5"])
    if "escape" in keys:
        emergency_quit(win, "User pressed Escape - exiting experiment.")
    if "5" in keys:
        return

    # Reset queue for PASS 2
    nback_queue = []
    for i, current_pos in enumerate(demo_positions):
        trial_num = i + 1

        # Calculate positions on the circle for drawing mismatch squares
        radius = 150
        angles = [idx * (360 / 12) for idx in range(12)]

        # Display grid with highlighted current position
        display_grid(win, highlight_pos=current_pos, highlight=True, n_level=n)
        win.flip()

        # Wait display duration but DO NOT clear the stimulus
        core.wait(display_duration)

        # Extended feedback for trial > n (with stimulus still visible)
        if trial_num > n:
            old_pos = nback_queue[-n]
            is_target = current_pos == old_pos

            # Redraw the grid with the current position still highlighted
            display_grid(win, highlight_pos=current_pos, highlight=True, n_level=n)

            # If mismatch, also draw old square in orange
            if not is_target:
                old_x = radius * math.cos(math.radians(angles[old_pos]))
                old_y = radius * math.sin(math.radians(angles[old_pos]))
                mismatch_rect = visual.Rect(
                    win, width=50, height=50, pos=(old_x, old_y), fillColor="orange"
                )
                mismatch_rect.draw()

            if is_target:
                fb_text = get_text("demo_feedback_match_spa", n=n)
            else:
                fb_text = get_text("demo_feedback_mismatch_spa", n=n)

            feedback_stim = visual.TextStim(
                win,
                text=fb_text,
                color="white",
                height=24,
                pos=(0, -250),
                wrapWidth=800,
            )
            feedback_stim.draw()
            display_feedback(win, is_target, pos=(0, 400))

            # Add the prompt for the next step
            if trial_num == num_demo_trials:
                proceed_text = get_text("demo_proceed_final")
            else:
                proceed_text = get_text("demo_proceed_next")

            proceed_stim = visual.TextStim(
                win,
                text=proceed_text,
                color="white",
                height=24,
                wrapWidth=800,
                pos=(0, -280),
            )
            proceed_stim.draw()
            win.flip()

            keys = event.waitKeys(keyList=["space", "escape", "5"])
            if "escape" in keys or "5" in keys:
                return
        else:
            # For trials <= n, add a prompt but keep the stimulus visible
            display_grid(win, highlight_pos=current_pos, highlight=True, n_level=n)

            if trial_num == num_demo_trials:
                proceed_text = get_text("demo_proceed_final")
            else:
                proceed_text = get_text("demo_proceed_next")

            proceed_stim = visual.TextStim(
                win,
                text=proceed_text,
                color="white",
                height=24,
                wrapWidth=800,
                pos=(0, -280),
            )
            proceed_stim.draw()
            win.flip()

            keys = event.waitKeys(keyList=["space", "escape", "5"])
            if "escape" in keys or "5" in keys:
                return

        nback_queue.append(current_pos)
        if len(nback_queue) > n:
            nback_queue.pop(0)

    # End of PASS 2
    draw_grid()
    pass2_end_text = get_text("demo_pass2_end")
    pass2_end_stim = visual.TextStim(
        win, text=pass2_end_text, color="white", height=24, wrapWidth=800
    )
    pass2_end_stim.draw()
    win.flip()
    keys = event.waitKeys(keyList=["space", "escape", "5"])
    if "escape" in keys:
        emergency_quit(win, "User pressed Escape - exiting experiment.")
    if "5" in keys:
        return


def show_dual_demo(win, n=2, num_demo_trials=6, display_duration=1.0, isi=1.2):
    """
    Run a two-pass Dual N-back demo on a 3×3 grid.

    Parameters
    ----------
    win : psychopy.visual.Window
        PsychoPy window.
    n : int, optional
        N-back level. Default 2.
    num_demo_trials : int, optional
        Number of demo trials. Default 6.
    display_duration : float, optional
        On-screen time (s) per stimulus. Default 1.0.
    isi : float, optional
        Inter-stimulus interval (s). Default 1.2.

    Returns
    -------
    None

    Notes
    -----
    Pass 1: normal speed with brief feedback (trial > n).
    Pass 2: keeps current stimulus on screen; shows extended feedback (including
    showing the (n-back) reference with orange border on mismatches).
    Press '5' or Escape at any prompt to skip/exit the demo.
    """
    # Generate a 6-trial demo sequence using your dual task generator.
    grid_size = 3
    demo_rate = float(get_param("dual.target_rate", 0.5))
    demo_positions, demo_images = generate_dual_nback_sequence(
        num_demo_trials, grid_size, n, image_files, target_rate=demo_rate
    )

    intro_text = get_text(
        "demo_intro", task_name="Dual", n=n, num_demo_trials=num_demo_trials
    )
    intro_stim = visual.TextStim(
        win, text=intro_text, color="white", height=24, wrapWidth=800
    )
    intro_stim.draw()
    win.flip()
    keys = event.waitKeys(keyList=["space", "escape", "5"])
    if "escape" in keys:
        emergency_quit(win, "User pressed Escape - exiting experiment.")
    if "5" in keys:
        return

    n_plus_one = n + 1
    pass1_text = get_text(
        "demo_pass1_intro", num_demo_trials=num_demo_trials, n=n, n_plus_one=n_plus_one
    )
    pass1_stim = visual.TextStim(
        win, text=pass1_text, color="white", height=24, wrapWidth=800
    )
    pass1_stim.draw()
    win.flip()
    keys = event.waitKeys(keyList=["space", "escape", "5"])
    if "escape" in keys:
        emergency_quit(win, "User pressed Escape - exiting experiment.")
    if "5" in keys:
        return

    nback_queue = []
    for i, (pos, img) in enumerate(zip(demo_positions, demo_images)):
        trial_num = i + 1

        # Present the dual stimulus.
        dual_stim = display_dual_stimulus(
            win, pos, img, grid_size, n_level=n, return_stim=True
        )
        grid, outline = create_grid(win, grid_size)
        level_text = visual.TextStim(
            win,
            text=get_text("level_label", n=n),
            color="white",
            height=24,
            pos=(-450, 350),
        )

        def draw_current_state():
            draw_grid()
            for rect in grid:
                rect.lineColor = get_level_color(n)
                rect.draw()
            outline.lineColor = get_level_color(n)
            outline.draw()
            if dual_stim:
                dual_stim.draw()
            level_text.draw()

        draw_current_state()
        win.flip()
        core.wait(display_duration)

        # Clear the stimulus and wait a full ISI delay.
        dual_stim = None
        draw_current_state()
        win.flip()
        core.wait(isi)

        # For trials > n, show brief feedback.
        if trial_num > n:
            old_pos, old_img = nback_queue[-n]
            is_target = pos == old_pos and img == old_img
            draw_current_state()
            display_feedback(win, is_target, pos=(0, 400))
            win.flip()
            core.wait(0.5)
        else:
            core.wait(0.5)

        core.wait(0.2)
        nback_queue.append((pos, img))
        if len(nback_queue) > n:
            nback_queue.pop(0)

    draw_grid()
    pass1_end_text = get_text("demo_pass1_end")
    pass1_end_stim = visual.TextStim(
        win, text=pass1_end_text, color="white", height=24, wrapWidth=800
    )
    pass1_end_stim.draw()
    win.flip()
    keys = event.waitKeys(keyList=["space", "escape", "5"])
    if "escape" in keys:
        emergency_quit(win, "User pressed Escape - exiting experiment.")
    if "5" in keys:
        return

    pass2_text = get_text("demo_pass2_intro_dual", num_demo_trials=num_demo_trials)
    pass2_stim = visual.TextStim(
        win, text=pass2_text, color="white", height=24, wrapWidth=800
    )
    pass2_stim.draw()
    win.flip()
    keys = event.waitKeys(keyList=["space", "escape", "5"])
    if "escape" in keys:
        emergency_quit(win, "User pressed Escape - exiting experiment.")
    if "5" in keys:
        return

    # Reset queue for PASS 2.
    nback_queue = []
    for i, (pos, img) in enumerate(zip(demo_positions, demo_images)):
        trial_num = i + 1

        # Present the dual stimulus and don't clear it
        dual_stim = display_dual_stimulus(
            win, pos, img, grid_size, n_level=n, return_stim=True
        )
        grid, outline = create_grid(win, grid_size)
        level_text = visual.TextStim(
            win,
            text=get_text("level_label", n=n),
            color="white",
            height=24,
            pos=(-450, 350),
        )

        def draw_current_state(with_dual_stim=True):
            draw_grid()
            for rect in grid:
                rect.lineColor = get_level_color(n)
                rect.draw()
            outline.lineColor = get_level_color(n)
            outline.draw()
            if with_dual_stim and dual_stim:
                dual_stim.draw()
            level_text.draw()

        # Draw the current stimulus and keep it visible
        draw_current_state(True)
        win.flip()

        # For trials > n, show extended feedback without clearing stimulus
        if trial_num > n:
            core.wait(
                display_duration
            )  # Wait the display duration but keep stimulus visible

            old_pos, old_img = nback_queue[-n]
            is_target = pos == old_pos and img == old_img

            # Redraw everything including current stimulus
            draw_current_state(True)

            # If mismatch, also draw the old stimulus with an orange border
            if not is_target:
                old_stim = display_dual_stimulus(
                    win, old_pos, old_img, grid_size, n_level=n, return_stim=True
                )
                old_border = visual.Rect(
                    win,
                    width=old_stim.size[0] + 10,
                    height=old_stim.size[1] + 10,
                    pos=old_stim.pos,
                    lineColor="orange",
                    lineWidth=4,
                )
                old_border.draw()
                old_stim.draw()

            if is_target:
                fb_text = get_text("demo_feedback_match_dual", n=n)
            else:
                fb_text = get_text("demo_feedback_mismatch_dual", n=n)
            feedback_stim = visual.TextStim(
                win,
                text=fb_text,
                color="white",
                height=24,
                pos=(0, -250),
                wrapWidth=800,
            )
            feedback_stim.draw()
            display_feedback(win, is_target, pos=(0, 400))

            if trial_num == num_demo_trials:
                proceed_text = get_text("demo_proceed_final")
            else:
                proceed_text = get_text("demo_proceed_next")

            proceed_stim = visual.TextStim(
                win,
                text=proceed_text,
                color="white",
                height=24,
                wrapWidth=800,
                pos=(0, -280),
            )
            proceed_stim.draw()
            win.flip()

            keys = event.waitKeys(keyList=["space", "escape", "5"])
            if "escape" in keys or "5" in keys:
                return
        else:
            # For trials <= n, still wait display_duration but keep stimulus visible
            core.wait(display_duration)

            # Draw the current state with stimulus and add a proceed prompt
            draw_current_state(True)

            if trial_num == num_demo_trials:
                proceed_text = get_text("demo_proceed_final")
            else:
                proceed_text = get_text("demo_proceed_next")

            proceed_stim = visual.TextStim(
                win,
                text=proceed_text,
                color="white",
                height=24,
                wrapWidth=800,
                pos=(0, -280),
            )
            proceed_stim.draw()
            win.flip()

            keys = event.waitKeys(keyList=["space", "escape", "5"])
            if "escape" in keys or "5" in keys:
                return

        nback_queue.append((pos, img))
        if len(nback_queue) > n:
            nback_queue.pop(0)

    draw_grid()
    pass2_end_text = get_text("demo_pass2_end")
    pass2_end_stim = visual.TextStim(
        win, text=pass2_end_text, color="white", height=24, wrapWidth=800
    )
    pass2_end_stim.draw()
    win.flip()
    keys = event.waitKeys(keyList=["space", "escape", "5"])
    if "escape" in keys:
        emergency_quit(win, "User pressed Escape - exiting experiment.")
    if "5" in keys:
        return


def show_sequential_demo(win, n=2, num_demo_trials=6, display_duration=0.8, isi=1.0):
    """
    Run a two-pass Sequential N-back demo (normal, then moving-window explanatory).

    Parameters
    ----------
    win : psychopy.visual.Window
        PsychoPy window.
    n : int, optional
        N-back level. Default 2.
    num_demo_trials : int, optional
        Number of demo trials. Default 6.
    display_duration : float, optional
        On-screen time (s) per stimulus. Default 0.8.
    isi : float, optional
        Inter-stimulus interval (s). Default 1.0.

    Returns
    -------
    None

    Notes
    -----
    - Pass 1: normal single-stimulus trials with brief feedback (trial > n).
    - Pass 2: shows the full row of images, centres the current trial, frames the
      current stimulus, and marks the n-back item (green/red) with concise text.
    - Press '5' or Escape to skip/exit the demo.
    """
    demo_sequence, _ = generate_sequential_image_sequence(
        num_demo_trials,
        n,
        target_percentage=0.5,
        image_files=image_files,
    )

    n_plus_one = n + 1
    intro_text = get_text(
        "demo_pass1_intro", num_demo_trials=num_demo_trials, n=n, n_plus_one=n_plus_one
    )
    intro_stim = visual.TextStim(
        win, text=intro_text, color="white", height=24, wrapWidth=800
    )
    intro_stim.draw()
    win.flip()
    keys = event.waitKeys(keyList=["space", "escape", "5"])
    if "escape" in keys:
        emergency_quit(win, "User pressed Escape - exiting experiment.")
    if "5" in keys:
        return

    # Use the same size for stimuli in both passes
    stim_size = (300, 300)

    for i in range(num_demo_trials):
        trial_num = i + 1
        # Present the current image centered.
        img = demo_sequence[i]
        stim = visual.ImageStim(
            win, image=os.path.join(image_dir, img), pos=(0, 0), size=stim_size
        )
        stim.draw()
        win.flip()
        core.wait(display_duration)
        # Clear the stimulus (blank screen) and wait full ISI.
        win.flip()
        core.wait(isi)
        # For trials > n, show brief feedback.
        if trial_num > n:
            ref_img = demo_sequence[i - n]
            is_target = img == ref_img
            if is_target:
                fb = visual.TextStim(
                    win, text="✓", color="green", height=48, pos=(0, 150)
                )
            else:
                fb = visual.TextStim(
                    win, text="✗", color="red", height=48, pos=(0, 150)
                )
            fb.draw()
            win.flip()
            core.wait(0.5)
        else:
            core.wait(0.5)
        core.wait(0.2)

    end_pass1 = visual.TextStim(
        win,
        text=get_text("demo_pass1_end"),
        # ...
    )
    end_pass1.draw()
    win.flip()
    keys = event.waitKeys(keyList=["space", "escape", "5"])
    if "escape" in keys:
        emergency_quit(win, "User pressed Escape - exiting experiment.")
    if "5" in keys:
        return

    # -------------- PASS 2: EXPLANATORY (MOVING WINDOW) --------------
    pass2_text = get_text("demo_pass2_intro_seq")
    pass2_stim = visual.TextStim(
        win, text=pass2_text, color="white", height=24, wrapWidth=800
    )
    pass2_stim.draw()
    win.flip()
    keys = event.waitKeys(keyList=["space", "escape", "5"])
    if "escape" in keys:
        emergency_quit(win, "User pressed Escape - exiting experiment.")
    if "5" in keys:
        return

    # Adjust spacing to match the larger stimuli size
    spacing = 330  # Increased spacing to accommodate larger images

    # Set size for the pass 2 stimuli to be 10% smaller than pass 1
    pass2_stim_size = (270, 270)  # 10% smaller than 300x300

    # Compute initial positions so that the stimulus at index n-1 is centered.
    positions0 = compute_positions_ref(
        num_demo_trials, ref_index=0, spacing=spacing, center_x=0, y=0
    )

    for i in range(num_demo_trials):
        trial_num = i + 1
        # Compute shifted positions so that the current trial is centered
        shifted_positions = [(x - i * spacing, y) for (x, y) in positions0]

        # Draw level indicator
        level_stim = visual.TextStim(
            win,
            text=get_text("level_label", n=n),
            color="white",
            height=24,
            pos=(-450, 350),
        )
        level_stim.draw()

        # Calculate current position (stimulus i in the sequence)
        current_idx = i
        current_pos = shifted_positions[current_idx]

        # Draw the sequence (all stimuli)
        draw_sequence(win, demo_sequence, shifted_positions, size=pass2_stim_size)

        # Draw frame only around the current stimulus
        draw_center_frame(win, current_pos, pass2_stim_size)

        # For trials ≥ n, draw the n-back box at the correct position
        if trial_num > n:
            # Calculate the n-back reference position
            n_back_idx = current_idx - n
            n_back_pos = shifted_positions[n_back_idx]

            is_match = demo_sequence[i] == demo_sequence[i - n]
            draw_n_back_box(win, n_back_pos, pass2_stim_size, is_match)

            # Show tick or cross
            if is_match:
                tick = visual.TextStim(
                    win, text="✓", color="green", height=48, pos=(0, 150)
                )
                fb_text = get_text("demo_feedback_match_seq")
            else:
                tick = visual.TextStim(
                    win, text="✗", color="red", height=48, pos=(0, 150)
                )
                fb_text = get_text("demo_feedback_mismatch_seq")
            tick.draw()

            # Show concise feedback text
            feedback_stim = visual.TextStim(
                win, text=fb_text, color="white", height=24, pos=(0, -250)
            )
            feedback_stim.draw()
        else:
            # For trials before or equal to n, explain why there's no reference yet
            if trial_num < n:
                fb_text = get_text("demo_seq_building", trial_num=trial_num, n=n)
            else:  # trial_num == n
                n_plus_one = n + 1
                fb_text = get_text("demo_seq_wait", n=n, n_plus_one=n_plus_one)
            feedback_stim = visual.TextStim(
                win, text=fb_text, color="white", height=24, pos=(0, -250)
            )
            feedback_stim.draw()

        # Show prompt for all trials
        if trial_num == num_demo_trials:
            prompt_text = get_text("demo_proceed_final")
        else:
            prompt_text = get_text("demo_proceed_next")
        prompt_stim = visual.TextStim(
            win, text=prompt_text, color="white", height=24, pos=(0, -300)
        )
        prompt_stim.draw()

        # Display everything at once
        win.flip()

        # Wait for user input to proceed (all trials in Pass 2 require spacebar)
        keys = event.waitKeys(keyList=["space", "escape", "5"])
        if "escape" in keys or "5" in keys:
            return

    # Final message after the demo
    end_pass2 = visual.TextStim(
        win,
        text=get_text("demo_pass2_end"),
        color="white",
        height=24,
        wrapWidth=800,
    )
    end_pass2.draw()
    win.flip()
    keys = event.waitKeys(keyList=["space", "escape", "5"])
    if "escape" in keys:
        emergency_quit(win, "User pressed Escape - exiting experiment.")
    if "5" in keys:
        return


# =============================================================================
#  SECTION 8: ACTIVE PRACTICE BLOCKS
# =============================================================================


def run_spatial_nback_practice(n, num_trials=50, display_duration=None, isi=None):
    """
    Run one block of Spatial N-back practice.

    This function handles the stimulus presentation and response collection for
    the spatial task. It uses a fixed timing structure: responses trigger immediate
    visual feedback (overlaying the grid), but the trial waits for the full ISI
    to complete before moving to the next stimulus.

    Parameters
    ----------
    n : int
        N-back level (e.g., 2 or 3).
    num_trials : int, optional
        Number of trials to present. Default 50.
    display_duration : float, optional
        On-screen time (s) per stimulus (scaled by `T`). Uses GUI config or 1.0.
    isi : float, optional
        Inter-stimulus interval (s) (scaled by `T`). Uses GUI config or 1.0.

    Returns
    -------
    Tuple[float, int, int, int]
        (accuracy_pct, correct_responses, incorrect_responses, lapses)
    """
    # Get timing from GUI config if not explicitly provided
    if display_duration is None:
        display_duration = get_gui_timing("spatial", "display_duration", 1.0)
    if isi is None:
        isi = get_gui_timing("spatial", "isi", 1.0)

    display_duration = T(display_duration)
    isi = T(isi)
    global skip_to_next_stage
    positions = generate_positions_with_matches(num_trials, n)
    nback_queue = []
    correct_responses = 0
    incorrect_responses = 0
    lapses = 0
    reaction_times = []

    last_lapse = False

    initial_feedback = get_text("no_response_needed", n=n)
    display_grid(
        win,
        highlight_pos=None,
        highlight=False,
        n_level=n,
        feedback_text=initial_feedback,
    )
    win.flip()
    core.wait(2)

    def on_skip():
        global skip_to_next_stage
        skip_to_next_stage = True

    for i, pos in enumerate(positions):
        if last_lapse:
            lapse_feedback = get_text("lapse_feedback")
            last_lapse = False
        else:
            lapse_feedback = None

        if skip_to_next_stage:
            break

        is_target = len(nback_queue) >= n and pos == nback_queue[-n]

        # 1. Presentation Phase
        display_grid(
            win,
            highlight_pos=pos,
            highlight=True,
            n_level=n,
            lapse_feedback=lapse_feedback,
        )
        win.flip()
        core.wait(display_duration)

        # 2. Response Phase (ISI)
        display_grid(win, highlight_pos=None, highlight=False, n_level=n)
        win.flip()

        # Define the feedback behaviour: Draw result, wait brief moment, then clear
        def feedback_action(user_resp):
            # Draw green/red feedback
            display_grid(win, highlight_pos=None, highlight=False, n_level=n)
            display_feedback(win, user_resp == is_target)
            win.flip()
            core.wait(0.2)
            # Clear feedback (restore neutral grid)
            display_grid(win, highlight_pos=None, highlight=False, n_level=n)
            win.flip()

        response, reaction_time = collect_trial_response(
            win,
            duration=isi,
            response_map={"z": True, "m": False},
            is_valid_trial=(i >= n),
            stop_on_response=False,  # Keep looping after feedback to fill ISI
            post_response_callback=feedback_action,
            special_keys={"5": on_skip},
        )

        if skip_to_next_stage:
            break

        if response is not None:
            if response == is_target:
                correct_responses += 1
            else:
                incorrect_responses += 1
            reaction_times.append(reaction_time)
        elif i >= n:
            lapses += 1
            last_lapse = True

        nback_queue.append(pos)
        if len(nback_queue) > n:
            nback_queue.pop(0)

        event.clearEvents()

    total_responses = correct_responses + incorrect_responses + lapses
    accuracy = (correct_responses / total_responses) * 100 if total_responses > 0 else 0

    return accuracy, correct_responses, incorrect_responses, lapses


def run_dual_nback_practice(n, num_trials=50, display_duration=None, isi=None):
    """
    Run one block of Dual N-back practice on a 3×3 grid.

    This function coordinates the simultaneous presentation of visual and spatial
    stimuli. It uses a callback mechanism to provide immediate visual feedback
    upon response without interrupting the fixed trial timing.

    Parameters
    ----------
    n : int
        N-back level.
    num_trials : int, optional
        Number of trials to present. Default 50.
    display_duration : float, optional
        On-screen time (s) per stimulus (scaled by `T`). Uses GUI config or 1.0.
    isi : float, optional
        Inter-stimulus interval (s) (scaled by `T`). Uses GUI config or 1.2.

    Returns
    -------
    Tuple[float, int, int, int]
        (accuracy_pct, correct_responses, incorrect_responses, lapses)
    """
    # Get timing from GUI config if not explicitly provided
    if display_duration is None:
        display_duration = get_gui_timing("dual", "display_duration", 1.0)
    if isi is None:
        isi = get_gui_timing("dual", "isi", 1.2)

    display_duration = T(display_duration)
    isi = T(isi)
    global skip_to_next_stage
    grid_size = 3
    positions, images = generate_dual_nback_sequence(num_trials, 3, n, image_files)
    nback_queue = []
    correct_responses = 0
    incorrect_responses = 0
    lapses = 0
    reaction_times = []

    grid, outline = create_grid(win, grid_size)
    level_color = get_level_color(n)
    level_text = visual.TextStim(
        win,
        text=get_text("level_label", n=n),
        color="white",
        height=24,
        pos=(-450, 350),
    )

    draw_grid()
    visual.TextStim(
        win, text=get_text("no_response_needed", n=n), color=level_color, pos=(0, 0)
    ).draw()
    win.flip()
    core.wait(2)

    last_lapse = False

    def on_skip():
        global skip_to_next_stage
        skip_to_next_stage = True

    for i, (pos, img) in enumerate(zip(positions, images)):
        if last_lapse:
            lapse_feedback = get_text("lapse_feedback")
            last_lapse = False
        else:
            lapse_feedback = None

        if skip_to_next_stage:
            break

        is_target = (
            len(nback_queue) >= n
            and pos == nback_queue[-n][0]
            and img == nback_queue[-n][1]
        )

        # Prepare stimulus object
        image_stim = display_dual_stimulus(
            win, pos, img, grid_size, n_level=n, return_stim=True
        )

        def draw_state():
            """Helper to draw the current grid state."""
            draw_grid()
            for r in grid:
                r.lineColor = level_color
                r.draw()
            outline.lineColor = level_color
            outline.draw()
            if image_stim:
                image_stim.draw()
            if lapse_feedback:
                visual.TextStim(
                    win, text=lapse_feedback, color="orange", pos=(0, -350)
                ).draw()
            level_text.draw()

        # 1. Presentation
        draw_state()
        win.flip()
        core.wait(display_duration)

        # 2. ISI
        image_stim = None  # Clear stimulus
        draw_state()
        win.flip()

        # Define feedback callback: Draw feedback on top of grid, wait, then restore
        def feedback_action(user_resp):
            draw_state()
            display_feedback(win, user_resp == is_target, pos=(0, 300))
            win.flip()
            core.wait(0.3)
            draw_state()
            win.flip()

        response, reaction_time = collect_trial_response(
            win,
            duration=isi,
            response_map={"z": True, "m": False},
            is_valid_trial=(i >= n),
            stop_on_response=False,  # Wait out the clock
            post_response_callback=feedback_action,
            special_keys={"5": on_skip},
        )

        if skip_to_next_stage:
            break

        if response is not None:
            if response == is_target:
                correct_responses += 1
            else:
                incorrect_responses += 1
            reaction_times.append(reaction_time)
        elif i >= n:
            lapses += 1
            last_lapse = True

        nback_queue.append((pos, img))
        if len(nback_queue) > n:
            nback_queue.pop(0)

        event.clearEvents()

    total_responses = correct_responses + incorrect_responses + lapses
    accuracy = (correct_responses / total_responses) * 100 if total_responses > 0 else 0
    return accuracy, correct_responses, incorrect_responses, lapses


def run_sequential_nback_practice(
    n, num_trials=90, target_percentage=0.5, display_duration=None, isi=None
):
    """
    Run one block of Sequential N-back practice (with optional 200 ms distractors).

    This function presents images sequentially. It includes logic for distractors
    during the ISI. Feedback is provided via a callback that overlays the tick/cross
    on the fixation cross immediately upon response, without altering the trial duration.

    Parameters
    ----------
    n : int
        The current N-back level (2 or 3).
    num_trials : int, default 90
        Total trials in this block.
    target_percentage : float, default 0.5
        Proportion of target trials (matches).
    display_duration : float, optional
        Seconds each stimulus is shown. Uses GUI config or 0.8.
    isi : float, optional
        Inter-stimulus interval *before* speed multiplier. Uses GUI config or 1.0.

    Returns
    -------
    tuple
        (accuracy_pct, incorrect_responses, lapses, avg_reaction_time)
    """
    # Get timing from GUI config if not explicitly provided
    if display_duration is None:
        display_duration = get_gui_timing("sequential", "display_duration", 0.8)
    if isi is None:
        isi = get_gui_timing("sequential", "isi", 1.0)

    display_duration = T(display_duration)
    isi = T(isi)
    global skip_to_next_stage

    # FIX: Pass 'image_files' as a keyword argument
    images, yes_positions = generate_sequential_image_sequence(
        num_trials, n, target_percentage, image_files=image_files
    )

    nback_queue = []
    correct_responses = 0
    incorrect_responses = 0
    lapses = 0
    reaction_times = []
    last_lapse = False

    fixation = visual.TextStim(win, text="+", color="white", height=32)
    level_text = visual.TextStim(
        win,
        text=get_text("level_label", n=n),
        color="white",
        height=24,
        pos=(-450, 350),
    )

    draw_grid()
    level_text.draw()
    visual.TextStim(win, text=get_text("no_response_needed", n=n), color="white").draw()
    win.flip()
    core.wait(2)

    def on_skip():
        global skip_to_next_stage
        skip_to_next_stage = True

    for i, img in enumerate(images):
        if skip_to_next_stage:
            break

        prompt = get_text("lapse_feedback") if (last_lapse and i >= n) else None
        last_lapse = False

        image_path = os.path.join(image_dir, img)
        image_stim = visual.ImageStim(win, image=image_path, size=(350, 350))

        # 1. Presentation
        draw_grid()
        level_text.draw()
        image_stim.draw()
        if prompt:
            visual.TextStim(win, text=prompt, color="orange", pos=(0, 200)).draw()
        win.flip()
        core.wait(display_duration)

        # 2. ISI
        draw_grid()
        level_text.draw()
        fixation.draw()
        win.flip()

        show_dist = DISTRACTORS_ENABLED and (i > 0) and (i % 12 == 0)
        dist_ctx = {"shown": False}

        def distractor_tick(t):
            if show_dist and not dist_ctx["shown"] and t >= isi / 2:
                draw_grid()
                level_text.draw()
                visual.Rect(win, width=100, height=100, fillColor="white").draw()
                win.flip()
                core.wait(0.2)
                draw_grid()
                level_text.draw()
                fixation.draw()
                win.flip()
                dist_ctx["shown"] = True

        def feedback_action(user_resp):
            is_target = (len(nback_queue) >= n) and (img == nback_queue[-n])
            # Draw existing state + feedback
            draw_grid()
            level_text.draw()
            fixation.draw()
            display_feedback(win, user_resp == is_target)
            win.flip()
            # For Sequential, we leave the feedback on screen; common loop handles the timing

        response, reaction_time = collect_trial_response(
            win,
            duration=isi,
            response_map={"z": True, "m": False},
            is_valid_trial=(i >= n),
            stop_on_response=False,  # Wait out the clock
            tick_callback=distractor_tick,
            post_response_callback=feedback_action,
            special_keys={"5": on_skip},
        )

        if skip_to_next_stage:
            break

        if response is not None:
            is_target = (len(nback_queue) >= n) and (img == nback_queue[-n])
            if response == is_target:
                correct_responses += 1
            else:
                incorrect_responses += 1
            reaction_times.append(reaction_time)
        elif i >= n:
            lapses += 1
            last_lapse = True

        nback_queue.append(img)
        if len(nback_queue) > n:
            nback_queue.pop(0)

        event.clearEvents()

    total_responses = correct_responses + incorrect_responses + lapses
    accuracy = (correct_responses / total_responses) * 100 if total_responses > 0 else 0
    avg_rt = (sum(reaction_times) / len(reaction_times)) if reaction_times else 0
    return accuracy, incorrect_responses, lapses, avg_rt


# =============================================================================
#  SECTION 9: ADAPTIVE LOGIC (PROMOTION & PLATEAU)
# =============================================================================


def check_level_change(block_results, current_level, window_size=2):
    """
    Decide whether to change N-back level based on recent accuracy.

    Parameters
    ----------
    block_results : List[Tuple[int, int, float, float]]
        History of (block_count, n_level, accuracy, avg_rt).
    current_level : int
        Current N-back level (2 or 3).
    window_size : int, optional
        Number of most recent blocks for the rolling average. Default 2.

    Returns
    -------
    int
        New level (2 or 3); unchanged if criteria are not met.

    Notes
    -----
    Promote 2→3 if rolling accuracy ≥ 82%. Demote 3→2 if rolling accuracy < 70%.
    """
    if len(block_results) < window_size:
        return current_level

    recent_accuracies = [block[2] for block in block_results[-window_size:]]
    rolling_avg = sum(recent_accuracies) / window_size

    if rolling_avg >= 82 and current_level == 2:
        return 3
    elif rolling_avg < 70 and current_level == 3:
        return 2
    return current_level


def check_plateau(block_results, variance_threshold=7):
    """
    Check whether performance has plateaued using recent accuracy variance.

    Parameters
    ----------
    block_results : List[Tuple[int, int, float, float]]
        Recent tuples (block_count, n_level, accuracy, avg_rt).
    variance_threshold : float, optional
        Maximum absolute deviation from the recent mean to count as stable (in %).
        Default 7.

    Returns
    -------
    bool
        True if at least three recent same-level blocks are within the threshold.
    """
    if len(block_results) < 3:
        return False

    # Check if there was a level change in the last three blocks
    last_three_levels = [block[1] for block in block_results[-3:]]
    if len(set(last_three_levels)) > 1:
        return False  # Levels changed, so performance hasn't stabilised

    current_level = block_results[-1][1]
    current_level_blocks = [
        block for block in block_results[-3:] if block[1] == current_level
    ]

    recent_accuracies = [block[2] for block in current_level_blocks]
    avg_accuracy = sum(recent_accuracies) / len(recent_accuracies)
    deviations = [abs(acc - avg_accuracy) for acc in recent_accuracies]
    stable_blocks = sum(1 for dev in deviations if dev <= variance_threshold)
    return stable_blocks >= 3


def run_sequential_nback_until_plateau(starting_level):
    """
    Run Sequential N-back practice blocks until accuracy stabilises.

    Administers practice blocks, adjusting the N-back level based on a rolling
    average of performance. The loop continues until one of three conditions is met:
    1. The participant's accuracy variance across three blocks is low (plateau).
    2. The maximum number of blocks is reached.
    3. The user manually skips the stage.

    Crucially, if a participant triggers a level promotion (e.g., 2 -> 3),
    the plateau check is skipped for that block to ensure they attempt the
    new difficulty level.

    Parameters
    ----------
    starting_level : int
        The initial N-back level (2 or 3).

    Returns
    -------
    tuple
        (final_n_level, final_accuracy, final_avg_rt) corresponding to the
        last completed block.
    """
    global skip_to_next_stage
    n_level = starting_level
    block_results = []
    max_blocks = 12
    scored_trials = 90
    block_count = 0

    in_grace_period = False
    slow_phase = False

    while block_count < max_blocks:
        block_count += 1
        num_trials = scored_trials

        # 1. Grace Period Message
        if in_grace_period:
            grace_message = visual.TextStim(
                win,
                text="Moving to the next level.\n\nThis block is for familiarisation.",
                color="white",
                height=24,
                wrapWidth=800,
            )
            grace_message.draw()
            win.flip()
            core.wait(4)

        # 2. Run the Block
        accuracy, errors, lapses, avg_reaction_time = run_sequential_nback_practice(
            n_level, num_trials=num_trials
        )
        elapsed = time.time() - START_TIME
        logging.info(
            f"Sequential Block {block_count} (Level {n_level}) finished. Accuracy: {accuracy:.1f}%, Avg RT: {avg_reaction_time:.3f}s. Elapsed: {int(elapsed // 60)}m {int(elapsed % 60)}s"
        )

        # 3. Log Results (if not in a special slow phase)
        if not slow_phase:
            log_seq_block(n_level, block_count, accuracy, errors, lapses)

        # 4. Check for User Skip
        if skip_to_next_stage:
            break

        # 5. Block Summary Screen
        sum_txt = (
            f"Sequential N-back Practice Block {block_count} (Level: {n_level}-back)\n\n"
            "Block complete.\n\n"
            "Press 'space' to continue."
        )
        show_text_screen(win, sum_txt, keys=["space"])

        # 6. Grace Period Exit
        # If this was a familiarisation block, we do not use it for scoring logic.
        if in_grace_period:
            in_grace_period = False
            continue

        # 7. Append Results
        block_results.append((block_count, n_level, accuracy, avg_reaction_time))

        # 8. Check for Level Promotion
        new_level = check_level_change(block_results, n_level, window_size=2)

        if new_level != n_level:
            # --- PROMOTION PATH ---
            # If the level changes, we MUST continue to the next block.
            # We do not check for plateau here.

            if new_level == 3 and n_level == 2:
                in_grace_period = True

            n_level = new_level
            level_change_text = f"Level change: Now switching to {n_level}-back."
            level_change_stim = visual.TextStim(
                win, text=level_change_text, color="white", height=24, wrapWidth=800
            )
            level_change_stim.draw()
            win.flip()
            logging.info(f"Level promoted to {n_level}-back")
            core.wait(2)

        elif check_plateau(block_results, variance_threshold=7):
            # --- PLATEAU PATH ---
            logging.info("Plateau reached (accuracy stable). Finishing practice.")
            # This runs ONLY if we did NOT just promote.
            # If performance is stable at the current level, we finish practice.
            break

        # 9. Max Blocks Warning
        if block_count == max_blocks:
            warning_text = (
                "Maximum number of blocks reached.\n\n" "Press 'space' to continue."
            )
            warning_stim = visual.TextStim(
                win, text=warning_text, color="orange", height=24, wrapWidth=800
            )
            warning_stim.draw()
            win.flip()
            event.waitKeys(keyList=["space"])

    if block_results:
        last_block = block_results[-1]
        final_n_level = last_block[1]
        final_accuracy = last_block[2]
        final_avg_rt = last_block[3]
    else:
        # Fallback if skipped immediately or no valid blocks recorded
        final_n_level = n_level
        final_accuracy = 0
        final_avg_rt = 0

    return final_n_level, final_accuracy, final_avg_rt


# =============================================================================
#  SECTION 10: MAIN EXECUTION
# =============================================================================


def main():
    """
    Execute the complete WAND practice protocol (Spatial → Dual → Sequential).

    Responsibilities
    ----------------
    - Collect options (seed, distractors) if not provided via CLI.
    - Run guided demos and practice blocks with speed-profile control.
    - Apply slow-gating and two-pass promotion logic for Spatial and Dual.
    - For Sequential: adaptive blocks until plateau (with grace on 2→3).
    - Log sequential block summaries to `./data/seq_<PID>.csv`.
    - Show brief summaries and a final completion screen.

    Returns
    -------
    None
    """
    global skip_to_next_stage, win, grid_lines, PARTICIPANT_ID, CSV_PATH
    global GLOBAL_SEED, DISTRACTORS_ENABLED, SPEED_PROFILE, SPEED_MULT, START_TIME

    print("Starting script...")

    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - [PRACTICE] %(message)s",
        datefmt="%H:%M:%S",
    )
    logging.info("Practice session started")
    START_TIME = time.time()

    print("Creating window...")
    try:
        win = visual.Window(
            size=WIN_SIZE,
            fullscr=WIN_FULLSCR,
            screen=0,
            allowGUI=False,
            allowStencil=False,
            monitor=WIN_MONITOR,
            color=WIN_BG,
            colorSpace=WIN_COLORSP,
            blendMode="avg",
            useFBO=WIN_USEFBO,
            units="pix",
            winType="pyglet",
        )

        # Shared error handler bound to this window
        install_error_hook(win)

        # Build and register the background grid once
        grid_lines = create_grid_lines(win)
        set_grid_lines(grid_lines)

        # Initialise participant logging
        PARTICIPANT_ID, CSV_PATH = init_seq_logger(win)

    except Exception as e:
        print(f"Error creating window: {e}")
        try:
            input("Press Enter to exit...")
        except Exception:
            pass
        sys.exit(1)

    try:
        # --- Options and seeding ---
        options = get_practice_options(win)
        GLOBAL_SEED = options["Seed"]
        DISTRACTORS_ENABLED = options["Distractors"]
        _apply_seed(GLOBAL_SEED)

        # --- Load Enable Flags from GUI Config ---
        from wand_common import load_gui_config

        gui_config = load_gui_config()
        if gui_config:
            spa_enabled = gui_config.get("spatial_enabled", True)
            dual_enabled = gui_config.get("dual_enabled", True)
            seq_enabled = gui_config.get("sequential_enabled", True)
            print(
                f"Tasks Enabled: Spatial={spa_enabled}, Dual={dual_enabled}, Sequential={seq_enabled}"
            )
        else:
            spa_enabled = True
            dual_enabled = True
            seq_enabled = True

        show_practice_entry_screen(
            win,
            spa_enabled=spa_enabled,
            dual_enabled=dual_enabled,
            seq_enabled=seq_enabled,
        )

        # ===== Spatial phase =====
        if spa_enabled:
            show_task_instructions(win, "Spatial")
            if prompt_demo_choice(win, "Spatial"):
                logging.info("User chose to watch Spatial demo")
                show_spatial_demo(win, n=2)
            else:
                logging.info("User skipped Spatial demo")
            _set_speed(choose_practice_speed(win, SPEED_PROFILE))

            # Slow gating loop, promote on first block ≥ 65 %
            if SPEED_PROFILE == "slow":
                while True:
                    show_countdown()
                    acc, corr, incorr, lapses = run_spatial_nback_practice(
                        n=2, num_trials=60
                    )
                    elapsed = time.time() - START_TIME
                    logging.info(
                        f"Spatial-SLOW Block finished. Accuracy: {acc:.1f}%. Elapsed: {int(elapsed // 60)}m {int(elapsed % 60)}s"
                    )
                    display_block_results(
                        win, "Spatial-slow", acc, corr, incorr, lapses
                    )

                    if skip_to_next_stage:
                        break

                    if acc >= 65:
                        _set_speed("normal")
                        visual.TextStim(
                            win,
                            text=get_text("practice_slow_promo"),
                            color="white",
                            height=24,
                            wrapWidth=800,
                        ).draw()
                        win.flip()
                        core.wait(2)
                        break

                    visual.TextStim(
                        win,
                        text=get_text("practice_slow_retry"),
                        color="white",
                        height=24,
                        wrapWidth=800,
                    ).draw()
                    win.flip()
                    event.waitKeys(keyList=["space"])

            # Need two successive normal-speed blocks ≥ 65 %
            passes = 0
            while passes < 2 and not skip_to_next_stage:
                show_countdown()
                acc, corr, incorr, lapses = run_spatial_nback_practice(
                    n=2, num_trials=60
                )
                elapsed = time.time() - START_TIME
                logging.info(
                    f"Spatial-NORMAL Block finished. Accuracy: {acc:.1f}%. Elapsed: {int(elapsed // 60)}m {int(elapsed % 60)}s"
                )
                display_block_results(win, "Spatial", acc, corr, incorr, lapses)

                if skip_to_next_stage:
                    break

                passes = passes + 1 if acc >= 65 else 0
                if passes < 2:
                    visual.TextStim(
                        win,
                        text="Let's do another block to make sure the performance is consistent.\n\nPress SPACE to continue.",
                        color="white",
                        height=24,
                        wrapWidth=800,
                    ).draw()
                    win.flip()
                    event.waitKeys(keyList=["space"])

        skip_to_next_stage = False  # reset for next phase

        # ===== Dual phase =====
        if dual_enabled:
            show_task_instructions(win, "Dual")
            if prompt_demo_choice(win, "Dual"):
                logging.info("User chose to watch Dual demo")
                show_dual_demo(win, n=2)
            else:
                logging.info("User skipped Dual demo")
            _set_speed(choose_practice_speed(win, SPEED_PROFILE))

            # Slow gating loop, promote on first block ≥ 65 %
            if SPEED_PROFILE == "slow":
                while True:
                    show_countdown()
                    acc, corr, incorr, lapses = run_dual_nback_practice(
                        n=2, num_trials=60
                    )
                    elapsed = time.time() - START_TIME
                    logging.info(
                        f"Dual-SLOW Block finished. Accuracy: {acc:.1f}%. Elapsed: {int(elapsed // 60)}m {int(elapsed % 60)}s"
                    )
                    display_block_results(win, "Dual-slow", acc, corr, incorr, lapses)

                    if skip_to_next_stage:
                        break

                    if acc >= 65:
                        _set_speed("normal")
                        visual.TextStim(
                            win,
                            text=get_text("practice_slow_promo"),
                            color="white",
                            height=24,
                            wrapWidth=800,
                        ).draw()
                        win.flip()
                        core.wait(2)
                        break

                    visual.TextStim(
                        win,
                        text=get_text("practice_slow_retry"),
                        color="white",
                        height=24,
                        wrapWidth=800,
                    ).draw()
                    win.flip()
                    event.waitKeys(keyList=["space"])

            # Need two successive normal-speed blocks ≥ 65 %
            passes = 0
            while passes < 2 and not skip_to_next_stage:
                show_countdown()
                acc, corr, incorr, lapses = run_dual_nback_practice(n=2, num_trials=60)
                elapsed = time.time() - START_TIME
                logging.info(
                    f"Dual-NORMAL Block finished. Accuracy: {acc:.1f}%. Elapsed: {int(elapsed // 60)}m {int(elapsed % 60)}s"
                )
                display_block_results(win, "Dual", acc, corr, incorr, lapses)

                if skip_to_next_stage:
                    break

            passes = passes + 1 if acc >= 65 else 0
            if passes < 2:
                visual.TextStim(
                    win,
                    text="Let's do another block to make sure the performance is consistent.\n\nPress SPACE to continue.",
                    color="white",
                    height=24,
                    wrapWidth=800,
                ).draw()
                win.flip()
                event.waitKeys(keyList=["space"])

        skip_to_next_stage = False

        # ===== Sequential phase =====
        if seq_enabled:
            show_task_instructions(win, "Sequential", n_back_level=2)
            if prompt_demo_choice(win, "Sequential"):
                show_sequential_demo(
                    win, n=2, num_demo_trials=6, display_duration=0.8, isi=1.0
                )
            _set_speed(choose_practice_speed(win, SPEED_PROFILE))

            # Slow gating for sequential
            if SPEED_PROFILE == "slow":
                while True:
                    show_countdown()
                    acc, _, _, _ = run_sequential_nback_practice(n=2, num_trials=60)
                    display_block_results(win, "Sequential-slow", acc, 0, 0, 0)

                    if skip_to_next_stage:
                        break

                    if acc >= 65:
                        _set_speed("normal")
                        visual.TextStim(
                            win,
                            text=get_text("practice_slow_promo"),
                            color="white",
                            height=24,
                            wrapWidth=800,
                        ).draw()
                        win.flip()
                        core.wait(2)
                        break

                    visual.TextStim(
                        win,
                        text=get_text("practice_slow_retry"),
                        color="white",
                        height=24,
                        wrapWidth=800,
                    ).draw()
                    win.flip()
                    event.waitKeys(keyList=["space"])

            # Adaptive plateau routine, unless user skipped
            if not skip_to_next_stage:
                starting_level = prompt_starting_level()
                show_countdown()
                (
                    final_n_level,
                    final_accuracy,
                    final_avg_rt,
                ) = run_sequential_nback_until_plateau(starting_level)

            skip_to_next_stage = False  # reset before exit

        # ===== Final summary =====
        final_summary = get_text("practice_complete")
        visual.TextStim(
            win, text=final_summary, color="white", height=24, wrapWidth=800
        ).draw()
        win.flip()
        event.waitKeys(keyList=["space"])

    except Exception as e:
        print(f"Error in main: {e}")
        traceback.print_exc()
    finally:
        try:
            win.close()
        except Exception:
            pass
        core.quit()


if __name__ == "__main__":
    main()
