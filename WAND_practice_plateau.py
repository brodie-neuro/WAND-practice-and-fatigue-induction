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
1.0

Environment
-----------
Tested on Windows, Python 3.8. See requirements.txt for exact pins.

License
-------
MIT (see LICENSE).
"""
import argparse
import math
import os
import random
import sys
import traceback

from psychopy import core, event, visual

from wand_common import (
    create_grid,
    create_grid_lines,
    display_dual_stimulus,
    display_grid,
    draw_grid,
    generate_dual_nback_sequence,
    generate_positions_with_matches,
    get_level_color,
    get_param,
    get_text,
    install_error_hook,
    load_config,
    set_grid_lines,
)

if getattr(sys, "frozen", False):
    # if you’ve bundled into an executable
    base_dir = sys._MEIPASS
else:
    base_dir = os.path.dirname(os.path.abspath(__file__))

# ────────────────────────────────────────────────────────────────
#  ▶▶  SEQUENTIAL BLOCK LOGGER  ◀◀
#      • ask for Participant ID immediately
#      • create ./data if missing
#      • write rows:  PID,level,block,accuracy,lapses,errors
#      • whenever the N-back level changes, start a new section
# ────────────────────────────────────────────────────────────────
import csv
import datetime

data_dir = os.path.join(base_dir, "data")
os.makedirs(data_dir, exist_ok=True)

CONFIG_DIR = os.path.join(base_dir, "config")
load_config(lang="en", config_dir=CONFIG_DIR)

# Window configuration from params.json
WIN_FULLSCR = bool(get_param("window.fullscreen", False))
WIN_SIZE = tuple(get_param("window.size", [1650, 1000]))
WIN_MONITOR = str(get_param("window.monitor", "testMonitor"))
WIN_BG = get_param("window.background_color", "black")
WIN_COLORSP = get_param("window.color_space", "rgb")
WIN_USEFBO = bool(get_param("window.use_fbo", True))


def _prompt_participant_id(win) -> str:
    """
    Prompt the experimenter for a participant-ID via an on-screen textbox.

    A minimal text editor is drawn in the centre of the PsychoPy window.
    Characters are appended one-by-one; **Backspace** deletes the last
    character.  The routine returns only when the user presses
    **Return / Enter** *and* at least one character has been typed.

    Parameters
    ----------
    win : psychopy.visual.Window
        The active PsychoPy window.

    Returns
    -------
    str
        A non-empty participant identifier.

    Notes
    -----
    * The routine purposefully ignores *Escape* so the experiment cannot
      proceed without an ID.
    * The textbox width is fixed at 380 px; text wraps automatically
      after 900 px to avoid runaway lines.
    """
    txt = dict(height=24, color="white", wrapWidth=900)
    pid = ""
    while True:
        visual.TextStim(win, text=get_text("get_pid"), **txt, pos=(0, 120)).draw()
        visual.Rect(win, width=380, height=50, lineColor="white", pos=(0, 40)).draw()
        visual.TextStim(win, text=pid, **txt, pos=(0, 40)).draw()
        win.flip()

        keys = event.waitKeys()
        if "return" in keys and pid:
            return pid
        if "backspace" in keys:
            pid = pid[:-1]
        elif len(keys[0]) == 1:
            pid += keys[0]


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


# --------------- CLI FLAGS (optional; wizard falls back) ---------------
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

# May still be None – that’s OK.
GLOBAL_SEED = args.seed
# None  → wizard asks.  'on'/'off' → use immediately.
DISTRACTORS_ENABLED = None if args.distractors is None else (args.distractors != "off")


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


skip_to_next_stage = False

grid_lines = []


def set_skip_flag():
    """Mark that the user has requested to skip the remainder of the current phase.

    When bound to a global key (’5’), this lets any running practice/demo block
    check `skip_to_next_stage` and exit early.

    Side effects:
        Sets the module‐level boolean `skip_to_next_stage` to True.

    Returns:
        None
    """
    global skip_to_next_stage
    skip_to_next_stage = True


event.globalKeys.add(key="5", func=set_skip_flag)


def prompt_starting_level():
    """Prompt the user to select the starting N-back level for the Sequential task.

    Displays instructions and waits for '2' or '3' key press to set the starting level.

    Returns:
        int: The chosen starting level (2 or 3).

    Raises:
        SystemExit: If 'escape' is pressed, the program exits.
    """
    instructions = get_text("practice_seq_start_level")
    instruction_text = visual.TextStim(
        win, text=instructions, color="white", height=24, wrapWidth=800
    )
    instruction_text.draw()
    win.flip()
    starting_level = None
    while starting_level not in [2, 3]:
        keys = event.waitKeys(keyList=["2", "3", "escape"])
        if "escape" in keys:
            core.quit()
        elif "2" in keys:
            starting_level = 2
        elif "3" in keys:
            starting_level = 3
    return starting_level


def get_practice_options(win):
    """
    Wizard that fills in any runtime options not set via CLI flags.

    This function will prompt for:
    1.  An optional RNG seed (if not provided via `--seed`).
    2.  The distractor flash setting (if not provided via `--distractors`).

    Args:
        win (visual.Window): The active PsychoPy window.

    Returns:
        dict: A dictionary with keys {"Seed": int|None, "Distractors": bool}.
    """
    win.mouseVisible = False
    txt = dict(height=24, color="white", wrapWidth=900)

    # 1) Seed entry  ── only if not given at CLI ───────────────────────────
    seed_val = GLOBAL_SEED
    if seed_val is None:  # <<< new guard
        seed_str = ""
        while True:
            visual.TextStim(
                win,
                text=get_text("get_seed"),
                **txt,
                pos=(0, 120),
            ).draw()
            visual.Rect(
                win, width=380, height=50, lineColor="white", pos=(0, 40)
            ).draw()
            visual.TextStim(win, text=seed_str, **txt, pos=(0, 40)).draw()
            win.flip()
            keys = event.waitKeys()
            if "return" in keys:
                seed_val = int(seed_str) if seed_str.isdigit() else None
                break
            if "backspace" in keys:
                seed_str = seed_str[:-1]
            elif keys[0].isdigit():
                seed_str += keys[0]

    # 2) Distractor toggle  ── only if not given at CLI ────────────────────
    distractors = DISTRACTORS_ENABLED
    if distractors is None:  # <<< new guard
        while True:
            prompt = get_text("get_distractors")
            visual.TextStim(win, text=prompt, **txt).draw()
            win.flip()
            key = event.waitKeys(keyList=["y", "n"])[0]
            distractors = key == "y"
            break

    win.flip()
    return {"Seed": seed_val, "Distractors": distractors}


# ───── speed helpers for the PRACTICE blocks only ─────
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


# Defaults pulled from config (with safe fallbacks)
SPEED_PROFILE = get_param("practice.speed_default", "normal")
SPEED_MULT = float(get_param(f"practice.speed_multiplier.{SPEED_PROFILE}", 1.0))


def choose_practice_speed(win, current_profile):
    """
    Prompt for speed profile ('normal' or 'slow').

    Parameters
    ----------
    win : psychopy.visual.Window
        PsychoPy window used to render the prompt.
    current_profile : str
        Current profile label for display (e.g., "normal" or "slow").

    Returns
    -------
    str
        "normal" or "slow".

    Notes
    -----
    - Keys: 'n' → normal, 's' → slow, 'escape' → quit (via `core.quit()`).
    """
    txt = dict(height=24, color="white", wrapWidth=900)
    while True:
        msg = get_text("practice_speed_selection", current=current_profile.upper())
        visual.TextStim(win, text=msg, **txt).draw()
        win.flip()
        key = event.waitKeys(keyList=["n", "s", "escape"])[0]
        if key == "escape":
            core.quit()
        return "slow" if key == "s" else "normal"


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


# point at the stimuli folder next to this script
image_dir = os.path.join(base_dir, "Abstract Stimuli", "apophysis")
image_files = [f for f in os.listdir(image_dir) if f.endswith(".png")]

if len(image_files) < 24:
    print("Not enough images found in directory")
    sys.exit(1)


def show_practice_entry_screen():
    """
    Display an initial welcome screen and wait for Space.

    Returns
    -------
    None

    Notes
    -----
    The function waits for the Space key; Escape is not accepted at this screen.
    """
    pilot_text = get_text("practice_welcome")
    pilot_message = visual.TextStim(
        win, text=pilot_text, color="white", height=24, wrapWidth=800
    )
    pilot_message.draw()
    win.flip()
    event.waitKeys(keyList=["space"])


def show_task_instructions(win, task_name, n_back_level=None):
    """
    Display task-specific instructions and wait for Space.

    Parameters
    ----------
    win : psychopy.visual.Window
        The PsychoPy window to draw instructions on.
    task_name : str
        One of {"spatial", "dual", "sequential"} (case-insensitive).
    n_back_level : Optional[int], optional
        N-back level text for sequential instructions (2 or 3). Default None.

    Returns
    -------
    None

    Notes
    -----
    Pressing Escape exits the program via `core.quit()`.
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

    instruction_text = visual.TextStim(
        win, text=welcome_text, color="white", height=24, wrapWidth=800
    )
    instruction_text.draw()
    win.flip()

    # Wait until participant presses SPACE
    while True:
        keys = event.waitKeys(keyList=["space", "escape"])
        if "space" in keys:
            break
        elif "escape" in keys:
            core.quit()


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
    Show a minimal on-screen summary of a block (task name + accuracy).

    Parameters
    ----------
    win : psychopy.visual.Window
        PsychoPy window.
    task_name : str
        Task label for the header.
    accuracy : float
        Block accuracy in percent.
    *_ :
        Ignored positional extras for call-site compatibility.

    Returns
    -------
    None
    """
    results_text = get_text(
        "practice_block_results", task_name=task_name, accuracy=accuracy
    )
    visual.TextStim(
        win, text=results_text, color="white", height=24, wrapWidth=800
    ).draw()
    win.flip()
    event.waitKeys(keyList=["space"])


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
        num_demo_trials, n, target_percentage=0.4
    )

    # ---------------------------------------------------------------------
    # INTRO SCREEN
    # ---------------------------------------------------------------------
    intro_text = get_text(
        "demo_intro", task_name="Spatial", n=n, num_demo_trials=num_demo_trials
    )
    intro_stim = visual.TextStim(
        win, text=intro_text, color="white", height=24, wrapWidth=800
    )
    intro_stim.draw()
    win.flip()
    keys = event.waitKeys(keyList=["space", "escape", "5"])
    if "escape" in keys or "5" in keys:
        return

    # ---------------------------------------------------------------------
    # PASS 1: NORMAL SPEED
    # ---------------------------------------------------------------------
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
    if "escape" in keys or "5" in keys:
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
    if "escape" in keys or "5" in keys:
        return

    # ---------------------------------------------------------------------
    # PASS 2: EXPLANATORY WITH SPACE-TO-PROCEED (NO FLASHING)
    # ---------------------------------------------------------------------
    pass2_text = get_text("demo_pass2_intro_spa", num_demo_trials=num_demo_trials)
    pass2_stim = visual.TextStim(
        win, text=pass2_text, color="white", height=24, wrapWidth=800
    )
    pass2_stim.draw()
    win.flip()
    keys = event.waitKeys(keyList=["space", "escape", "5"])
    if "escape" in keys or "5" in keys:
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
    if "escape" in keys or "5" in keys:
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
    demo_rate = float(get_param("dual.target_rate", 0.4))
    demo_positions, demo_images = generate_dual_nback_sequence(
        num_demo_trials, grid_size, n, image_files, target_rate=demo_rate
    )

    # ---------------------------------------------------------------------
    # INTRO SCREEN
    # ---------------------------------------------------------------------
    intro_text = get_text(
        "demo_intro", task_name="Dual", n=n, num_demo_trials=num_demo_trials
    )
    intro_stim = visual.TextStim(
        win, text=intro_text, color="white", height=24, wrapWidth=800
    )
    intro_stim.draw()
    win.flip()
    keys = event.waitKeys(keyList=["space", "escape", "5"])
    if "escape" in keys or "5" in keys:
        return

    # ---------------------------------------------------------------------
    # PASS 1: NORMAL SPEED
    # ---------------------------------------------------------------------
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
    if "escape" in keys or "5" in keys:
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
    if "escape" in keys or "5" in keys:
        return

    # ---------------------------------------------------------------------
    # PASS 2: EXPLANATORY WITH SPACE-TO-PROCEED (NO FLASHING)
    # ---------------------------------------------------------------------
    pass2_text = get_text("demo_pass2_intro_dual", num_demo_trials=num_demo_trials)
    pass2_stim = visual.TextStim(
        win, text=pass2_text, color="white", height=24, wrapWidth=800
    )
    pass2_stim.draw()
    win.flip()
    keys = event.waitKeys(keyList=["space", "escape", "5"])
    if "escape" in keys or "5" in keys:
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
    if "escape" in keys or "5" in keys:
        return


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
    # Generate the demo sequence.
    demo_sequence, _ = generate_sequential_image_sequence(
        num_demo_trials, n, target_percentage=0.4
    )

    # -------------- PASS 1: NORMAL --------------
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
    if "escape" in keys or "5" in keys:
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
    if "escape" in keys or "5" in keys:
        return

    # -------------- PASS 2: EXPLANATORY (MOVING WINDOW) --------------
    pass2_text = get_text("demo_pass2_intro_seq")
    pass2_stim = visual.TextStim(
        win, text=pass2_text, color="white", height=24, wrapWidth=800
    )
    pass2_stim.draw()
    win.flip()
    keys = event.waitKeys(keyList=["space", "escape", "5"])
    if "escape" in keys or "5" in keys:
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
    if "escape" in keys or "5" in keys:
        return


def run_spatial_nback_practice(n, num_trials=50, display_duration=1.0, isi=1.0):
    """
    Run one block of Spatial N-back practice.

    Parameters
    ----------
    n : int
        N-back level.
    num_trials : int, optional
        Number of trials to present. Default 50.
    display_duration : float, optional
        On-screen time (s) per stimulus (scaled by `T`). Default 1.0.
    isi : float, optional
        Inter-stimulus interval (s) (scaled by `T`). Default 1.0.

    Returns
    -------
    Tuple[float, int, int, int]
        (accuracy_pct, correct_responses, incorrect_responses, lapses)

    Notes
    -----
    Escape exits via `core.quit()`. Pressing '5' skips the remainder of the phase.
    """
    display_duration = T(display_duration)
    isi = T(isi)
    global skip_to_next_stage
    positions = generate_positions_with_matches(num_trials, n)
    nback_queue = []
    correct_responses = 0
    incorrect_responses = 0
    lapses = 0
    total_reaction_time = 0
    reaction_times = []
    responses = []

    last_lapse = False  # 1. Initialize a boolean flag here

    initial_feedback = get_text("no_response_needed", n=n)
    draw_grid()  # Add background grid
    feedback_text = visual.TextStim(
        win, text=initial_feedback, color=get_level_color(n), height=24, pos=(0, 0)
    )
    feedback_text.draw()
    win.flip()
    core.wait(2)

    draw_grid()  # Add background grid
    win.flip()
    core.wait(0.5)

    for i, pos in enumerate(positions):
        # 2. Add this block to check the flag at the START of the trial
        if last_lapse:
            lapse_feedback = get_text("lapse_feedback")
            last_lapse = False
        else:
            lapse_feedback = None

        if skip_to_next_stage:
            break  # Exit the task early

        is_target = len(nback_queue) >= n and pos == nback_queue[-n]

        display_grid(
            win,
            highlight_pos=pos,
            highlight=True,
            n_level=n,
            lapse_feedback=lapse_feedback,
        )
        win.flip()
        core.wait(display_duration)

        display_grid(win, highlight_pos=None, highlight=False, n_level=n)
        win.flip()

        response_timer = core.Clock()
        response = None
        while response_timer.getTime() < isi:
            keys = event.getKeys(keyList=["z", "m", "escape", "5"])
            if "escape" in keys:
                core.quit()
            if "5" in keys:
                skip_to_next_stage = True
                break
            if keys and response is None and i >= n:
                reaction_time = response_timer.getTime()
                response = "z" in keys

                if response == is_target:
                    correct_responses += 1
                else:
                    incorrect_responses += 1

                display_grid(win, highlight_pos=None, highlight=False, n_level=n)
                display_feedback(win, response == is_target)
                win.flip()
                core.wait(0.2)

                display_grid(win, highlight_pos=None, highlight=False, n_level=n)
                win.flip()

                total_reaction_time += reaction_time
                reaction_times.append(reaction_time)
                responses.append((i + 1, pos, is_target, response, reaction_time))

        if skip_to_next_stage:
            break  # Exit the task early

        # 3. Change the logic at the END of the trial to only set the flag
        if response is None and i >= n:
            lapses += 1
            responses.append((i + 1, pos, is_target, None, None))
            last_lapse = True

        nback_queue.append(pos)
        if len(nback_queue) > n:
            nback_queue.pop(0)

        event.clearEvents()

    total_responses = correct_responses + incorrect_responses + lapses
    accuracy = (correct_responses / total_responses) * 100 if total_responses > 0 else 0
    avg_reaction_time = (
        sum(reaction_times) / len(reaction_times) if reaction_times else 0
    )

    return accuracy, correct_responses, incorrect_responses, lapses


def run_dual_nback_practice(n, num_trials=50, display_duration=1.0, isi=1.2):
    """
    Run one block of Dual N-back practice on a 3×3 grid.

    Parameters
    ----------
    n : int
        N-back level.
    num_trials : int, optional
        Number of trials to present. Default 50.
    display_duration : float, optional
        On-screen time (s) per stimulus (scaled by `T`). Default 1.0.
    isi : float, optional
        Inter-stimulus interval (s) (scaled by `T`). Default 1.2.

    Returns
    -------
    Tuple[float, int, int, int]
        (accuracy_pct, correct_responses, incorrect_responses, lapses)

    Notes
    -----
    Escape exits via `core.quit()`. Pressing '5' skips the remainder of the phase.
    """
    display_duration = T(display_duration)
    isi = T(isi)
    global skip_to_next_stage
    grid_size = 3
    positions, images = generate_dual_nback_sequence(num_trials, 3, n, image_files)
    nback_queue = []
    responses = []
    correct_responses = 0
    incorrect_responses = 0
    lapses = 0
    total_reaction_time = 0
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

    initial_feedback = get_text("no_response_needed", n=n)
    draw_grid()  # Add background grid
    feedback_text = visual.TextStim(
        win, text=initial_feedback, color=level_color, height=24, pos=(0, 0)
    )
    feedback_text.draw()
    win.flip()
    core.wait(2)

    draw_grid()  # Add background grid
    win.flip()
    core.wait(0.5)

    last_lapse = False

    for i, (pos, img) in enumerate(zip(positions, images)):
        if last_lapse:
            lapse_feedback = get_text("lapse_feedback")
            last_lapse = False
        else:
            lapse_feedback = None

        if skip_to_next_stage:
            break  # Exit the task early

        is_target = (
            len(nback_queue) >= n
            and pos == nback_queue[-n][0]
            and img == nback_queue[-n][1]
        )

        image_stim = display_dual_stimulus(
            win, pos, img, grid_size, n_level=n, return_stim=True
        )

        def draw_current_state():
            draw_grid()  # Add background grid
            for rect in grid:
                rect.lineColor = level_color
                rect.draw()
            outline.lineColor = level_color
            outline.draw()
            if image_stim:
                image_stim.draw()
            if lapse_feedback:
                lapse_feedback_stim = visual.TextStim(
                    win, text=lapse_feedback, color="orange", height=24, pos=(0, -350)
                )
                lapse_feedback_stim.draw()
            level_text.draw()

        draw_current_state()
        win.flip()

        core.wait(display_duration)

        image_stim = None

        draw_current_state()
        win.flip()

        response_timer = core.Clock()
        response = None
        while response_timer.getTime() < isi:
            keys = event.getKeys(keyList=["z", "m", "escape", "5"])
            if "escape" in keys:
                core.quit()
            if "5" in keys:
                skip_to_next_stage = True
                break
            if keys and response is None and i >= n:
                reaction_time = response_timer.getTime()
                response = "z" in keys

                if response == is_target:
                    correct_responses += 1
                else:
                    incorrect_responses += 1

                feedback_pos = (0, 300)

                draw_current_state()
                display_feedback(win, response == is_target, pos=feedback_pos)
                win.flip()
                core.wait(0.3)

                draw_current_state()
                win.flip()

                total_reaction_time += reaction_time
                reaction_times.append(reaction_time)
                responses.append((i, pos, img, is_target, response, reaction_time))

        if skip_to_next_stage:
            break  # Exit the task early

        if response is None and i >= n:
            lapses += 1
            responses.append((i, pos, img, is_target, None, None))
            last_lapse = True

        nback_queue.append((pos, img))
        if len(nback_queue) > n:
            nback_queue.pop(0)

        event.clearEvents()

    total_responses = correct_responses + incorrect_responses + lapses
    accuracy = (correct_responses / total_responses) * 100 if total_responses > 0 else 0
    avg_reaction_time = (
        sum(reaction_times) / len(reaction_times) if reaction_times else 0
    )

    return accuracy, correct_responses, incorrect_responses, lapses


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


def generate_sequential_image_sequence(num_trials, n, target_percentage=0.5):
    """
    Generate a sequence of images for the Sequential N-back task.

    Creates a sequence with a requested target rate while avoiding unintended
    repeats where possible. Images are taken from the module-level ``image_files``
    pool without replacement until exhausted, then the pool is replenished and
    reshuffled.

    Parameters
    ----------
    num_trials : int
        Total number of trials to generate.
    n : int
        N-back level (e.g., 2 or 3).
    target_percentage : float, default 0.5
        Proportion of eligible trials (i.e., after the first ``n``) that should
        be true n-back matches.

    Returns
    -------
    sequence : list[str]
        Ordered list of image filenames (length == ``num_trials``).
    yes_positions : list[int]
        Sorted indices where true n-back matches occur.

    Notes
    -----
    - Consecutive true matches are capped at
      ``get_param("sequential.max_consecutive_matches", 2)``.
    - For non-target trials, candidates are chosen to avoid creating unintended
      n-back or 2-back repeats; if no candidates remain, the available pool is
      used as a fallback.
    """

    available_images = image_files.copy()
    random.shuffle(available_images)

    sequence = []
    max_consecutive_matches = int(get_param("sequential.max_consecutive_matches", 2))
    consecutive_count = 0

    eligible_range = range(n, num_trials)
    target_num_yes = int((num_trials - n) * target_percentage)
    yes_positions = (
        sorted(random.sample(eligible_range, target_num_yes))
        if target_num_yes > 0
        else []
    )

    for i in range(num_trials):
        if i in yes_positions and consecutive_count < max_consecutive_matches:
            # true n-back match
            sequence.append(sequence[i - n])
            consecutive_count += 1
            continue

        if not available_images:
            available_images = image_files.copy()
            random.shuffle(available_images)

        # avoid unintended n-back or 2-back repeats where possible
        candidates = [
            img
            for img in available_images
            if (len(sequence) < n or img not in sequence[-n:])
            and (len(sequence) < 2 or img != sequence[-2])
        ]
        if not candidates:
            candidates = available_images

        chosen = random.choice(candidates)
        sequence.append(chosen)
        available_images.remove(chosen)
        consecutive_count = 0

    return sequence, yes_positions


def run_sequential_nback_practice(
    n, num_trials=90, target_percentage=0.5, display_duration=0.8, isi=1.0
):
    """
    Run one block of **Sequential N-back practice** (with optional 200 ms distractors).

    Parameters
    ----------
    n : int
        The current N-back level (2 or 3).
    num_trials : int, default 90
        Total trials in this block.
    target_percentage : float, default 0.5
        Proportion of target trials (matches).
    display_duration : float, default 0.8
        Seconds each stimulus is shown.
    isi : float, default 1.0
        Inter-stimulus interval *before* any speed multiplier is applied.

    Returns
    -------
    tuple
        ``(accuracy_pct, errors, lapses, avg_reaction_time)``
        * accuracy_pct  – percent correct (0-100)
        * errors        – number of wrong key presses
        * lapses        – number of missed responses
        * avg_reaction_time – mean RT for scored trials (s)
    """
    display_duration = T(display_duration)
    isi = T(isi)
    global skip_to_next_stage

    # Generate the sequence
    images, yes_positions = generate_sequential_image_sequence(
        num_trials, n, target_percentage
    )

    nback_queue = []
    correct_responses = 0
    incorrect_responses = 0
    lapses = 0
    total_reaction_time = 0
    reaction_times = []
    last_lapse = False

    # Fixation cross for after each stimulus
    fixation_cross = visual.TextStim(win, text="+", color="white", height=32)

    # Create a level indicator just like in Spatial/Dual tasks
    level_text = visual.TextStim(
        win,
        text=get_text("level_label", n=n),
        color="white",
        height=24,
        pos=(-450, 350),  # same location as in spatial/dual
    )

    # --- Display initial feedback screen ---
    initial_feedback = get_text("no_response_needed", n=n)

    # Draw grid + level indicator
    draw_grid()
    level_text.draw()

    # Then draw the initial feedback text
    feedback_text = visual.TextStim(
        win, text=initial_feedback, color="white", height=24, pos=(0, 0)
    )
    feedback_text.draw()
    win.flip()
    core.wait(2)

    # Small gap
    draw_grid()
    level_text.draw()
    win.flip()
    core.wait(0.5)

    # --------------- Main Trial Loop ---------------
    for i, img in enumerate(images):
        if skip_to_next_stage:
            break  # If user pressed '5' in a prior iteration

        # If the previous trial was a lapse, show short feedback
        prompt_text = None
        if last_lapse and i >= n:
            prompt_text = get_text("lapse_feedback")
            last_lapse = False

        # Show the main image
        image_path = os.path.join(image_dir, img)
        image_stim = visual.ImageStim(win, image=image_path, size=(350, 350))

        # Draw grid + level, then the image
        draw_grid()
        level_text.draw()
        image_stim.draw()

        # If there's a lapse prompt, draw it
        if prompt_text:
            feedback_stim = visual.TextStim(
                win, text=prompt_text, color="orange", height=24, pos=(0, 200)
            )
            feedback_stim.draw()

        win.flip()
        core.wait(display_duration)  # Display the image for 'display_duration' seconds

        # Clear screen: draw grid + level, then fixation cross
        draw_grid()
        level_text.draw()
        fixation_cross.draw()
        win.flip()

        # Now the participant can respond during the ISI
        response_timer = core.Clock()
        response = None

        # We'll handle the distractor if it's the 12th trial
        show_distractor = DISTRACTORS_ENABLED and (i > 0) and (i % 12 == 0)
        distractor_shown = False

        while response_timer.getTime() < isi:
            keys = event.getKeys(keyList=["z", "m", "escape", "5"])

            # 1) Early escape
            if "escape" in keys:
                core.quit()
            if "5" in keys:
                skip_to_next_stage = True
                break

            # 2) Display the distractor (white square) at midpoint of ISI
            if show_distractor and not distractor_shown:
                if response_timer.getTime() >= isi / 2:
                    # Draw grid + level, then the distractor
                    draw_grid()
                    level_text.draw()

                    distractor_square = visual.Rect(
                        win,
                        width=100,
                        height=100,
                        fillColor="white",
                        lineColor=None,
                        pos=(0, 0),  # White distractor
                    )
                    distractor_square.draw()
                    win.flip()
                    core.wait(0.2)  # 200ms flash

                    # Return to the fixation state
                    draw_grid()
                    level_text.draw()
                    fixation_cross.draw()
                    win.flip()

                    distractor_shown = True

            # 3) Participant response
            if keys and response is None and i >= n:
                reaction_time = response_timer.getTime()
                # Check if this is a 'target' trial
                is_target = (len(nback_queue) >= n) and (img == nback_queue[-n])
                # 'z' => True, 'm' => False
                response = "z" in keys

                if response == is_target:
                    correct_responses += 1
                else:
                    incorrect_responses += 1

                # Show immediate feedback (✓ or ✗) WITHOUT re-drawing the grid
                display_feedback(win, response == is_target)

                # Track RT
                total_reaction_time += reaction_time
                reaction_times.append(reaction_time)

        # End of while loop (ISI)
        if skip_to_next_stage:
            break

        # If no response and it's past the first n trials => lapse
        if response is None and i >= n:
            lapses += 1
            last_lapse = True

        # Update n-back queue
        nback_queue.append(img)
        if len(nback_queue) > n:
            nback_queue.pop(0)

        event.clearEvents()

    # Compute performance
    total_responses = correct_responses + incorrect_responses + lapses
    accuracy = (correct_responses / total_responses) * 100 if total_responses > 0 else 0
    avg_reaction_time = (
        (sum(reaction_times) / len(reaction_times)) if reaction_times else 0
    )

    return accuracy, incorrect_responses, lapses, avg_reaction_time


def run_sequential_nback_until_plateau(starting_level):
    """
    Run Sequential N-back practice until accuracy stabilises (plateau).

    Parameters
    ----------
    starting_level : int
        Initial N-back level (2 or 3).

    Returns
    -------
    Tuple[int, float, float]
        (final_n_level, final_accuracy_pct, final_avg_rt)

    Notes
    -----
    - Includes a one-block grace period immediately after promoting 2→3.
    - Pressing '5' skips the remainder of the practice.
    - Escape exits via `core.quit()`.
    """
    global skip_to_next_stage
    n_level = starting_level
    block_results = []
    max_blocks = 12
    scored_trials = 90
    block_count = 0

    # Flag to track if the participant is in the familiarisation grace period
    in_grace_period = False

    # This hook is from the original code; it's unused but kept for consistency.
    slow_phase = False

    while block_count < max_blocks:
        block_count += 1
        num_trials = scored_trials

        # If this is a grace block, inform the user before it starts.
        if in_grace_period:
            grace_message = visual.TextStim(
                win,
                text=get_text("practice_grace_period"),
                color="white",
                height=24,
                wrapWidth=800,
            )
            grace_message.draw()
            win.flip()
            core.wait(4)  # Show the message for 4 seconds

        # Run the practice block for the current level
        accuracy, errors, lapses, avg_reaction_time = run_sequential_nback_practice(
            n_level, num_trials=num_trials
        )

        # Log results to the CSV file every time for a complete record.
        if not slow_phase:
            log_seq_block(n_level, block_count, accuracy, errors, lapses)

        if skip_to_next_stage:
            break

        # Always display a summary to the participant after each block.
        summary_text = get_text(
            "practice_seq_summary",
            block_count=block_count,
            n_level=n_level,
            accuracy=accuracy,
            avg_reaction_time=avg_reaction_time,
        )
        summary_stim = visual.TextStim(
            win, text=summary_text, color="white", height=24, wrapWidth=800
        )
        summary_stim.draw()
        win.flip()
        event.waitKeys(keyList=["space"])

        # If the block just completed was a grace block, reset the flag and
        # skip the performance evaluation for this iteration.
        if in_grace_period:
            in_grace_period = False
            continue

        # --- The following code only runs for scored (non-grace) blocks ---

        # Record the block result for the performance algorithm
        block_results.append((block_count, n_level, accuracy, avg_reaction_time))

        # Update the n-back level based on a rolling average of recent blocks.
        new_level = check_level_change(block_results, n_level, window_size=2)
        if new_level != n_level:
            # If moving up from 2 to 3, activate the grace period for the next block
            if new_level == 3 and n_level == 2:
                in_grace_period = True

            n_level = new_level
            level_change_text = get_text("practice_level_change", n_level=n_level)
            level_change_stim = visual.TextStim(
                win, text=level_change_text, color="white", height=24, wrapWidth=800
            )
            level_change_stim.draw()
            win.flip()
            core.wait(2)

        # Plateau check
        if check_plateau(block_results, variance_threshold=7):
            break

        # If max blocks were completed without plateau, warn about unstable performance
        if block_count == max_blocks:
            warning_text = get_text("practice_max_blocks")
            warning_stim = visual.TextStim(
                win, text=warning_text, color="orange", height=24, wrapWidth=800
            )
            warning_stim.draw()
            win.flip()
            event.waitKeys(keyList=["space"])

    # Determine final results from the last block recorded
    if block_results:
        last_block = block_results[-1]
        final_n_level = last_block[1]
        final_accuracy = last_block[2]
        final_avg_rt = last_block[3]
    else:
        # Fallback if no scored blocks were completed (e.g., user skipped immediately)
        final_n_level = n_level
        final_accuracy = 0
        final_avg_rt = 0

    return final_n_level, final_accuracy, final_avg_rt


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
    global GLOBAL_SEED, DISTRACTORS_ENABLED, SPEED_PROFILE, SPEED_MULT

    print("Starting script...")
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

        show_practice_entry_screen()

        # ===== Spatial phase =====
        show_task_instructions(win, "Spatial")
        show_spatial_demo(win, n=2)
        _set_speed(choose_practice_speed(win, SPEED_PROFILE))

        # Slow gating loop, promote on first block ≥ 65 %
        if SPEED_PROFILE == "slow":
            while True:
                show_countdown()
                acc, corr, incorr, lapses = run_spatial_nback_practice(
                    n=2, num_trials=60
                )
                display_block_results(win, "Spatial-slow", acc, corr, incorr, lapses)

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
            acc, corr, incorr, lapses = run_spatial_nback_practice(n=2, num_trials=60)
            display_block_results(win, "Spatial", acc, corr, incorr, lapses)

            if skip_to_next_stage:
                break

            passes = passes + 1 if acc >= 65 else 0
            if passes < 2:
                visual.TextStim(
                    win,
                    text=get_text(
                        "practice_streak", task_name="Spatial", passes=passes
                    ),
                    color="white",
                    height=24,
                    wrapWidth=800,
                ).draw()
                win.flip()
                event.waitKeys(keyList=["space"])

        skip_to_next_stage = False  # reset for next phase

        # ===== Dual phase =====
        show_task_instructions(win, "Dual")
        show_dual_demo(win, n=2)
        _set_speed(choose_practice_speed(win, SPEED_PROFILE))

        # Slow gating loop, promote on first block ≥ 65 %
        if SPEED_PROFILE == "slow":
            while True:
                show_countdown()
                acc, corr, incorr, lapses = run_dual_nback_practice(n=2, num_trials=60)
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
            display_block_results(win, "Dual", acc, corr, incorr, lapses)

            if skip_to_next_stage:
                break

            passes = passes + 1 if acc >= 65 else 0
            if passes < 2:
                visual.TextStim(
                    win,
                    text=get_text("practice_streak", task_name="Dual", passes=passes),
                    color="white",
                    height=24,
                    wrapWidth=800,
                ).draw()
                win.flip()
                event.waitKeys(keyList=["space"])

        skip_to_next_stage = False

        # ===== Sequential phase =====
        show_task_instructions(win, "Sequential", n_back_level=2)
        show_sequential_demo(win, n=2, num_demo_trials=6, display_duration=0.8, isi=1.0)
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
