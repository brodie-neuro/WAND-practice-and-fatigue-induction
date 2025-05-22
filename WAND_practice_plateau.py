#!/usr/bin/env python3
import math
import os
import random
import sys
import traceback
import argparse

from psychopy import core, event, visual

"""
WAND-practice-plateau

Practice session protocol for calibrating working memory performance prior to cognitive fatigue induction
using the WAND (Working-memory Adaptive-fatigue with N-back Difficulty) model.

Participants complete Spatial, Dual, and Sequential N-back tasks with demonstrations until plateau is achieved. 
Designed for pre-fatigue calibration in cognitive fatigue experiments, suitable
for EEG and behavioural-only studies.

Requires: PsychoPy, Python 3.8+.

Author: Brodie Mangan
Version: 1.0
"""

# Licensed under the MIT License (see LICENSE file for full text)

# --------------- CLI FLAGS (dummy‑run placeholders) ---------------
parser = argparse.ArgumentParser(add_help=False)
parser.add_argument("--seed",        type=int,            default=None,      help="Fix RNG (blank = random)")
parser.add_argument("--distractors", choices=["on","off"], default=None,     help="Toggle mini‑distractor flashes")
args, _ = parser.parse_known_args()

# Global flags that the on‑screen wizard can overwrite later
GLOBAL_SEED          = args.seed
DISTRACTORS_ENABLED  = (args.distractors != "off") if args.distractors else True


def _apply_seed(seed_val):
    """Seed Python & NumPy RNGs once, if a seed is provided."""
    if seed_val is None:
        return
    random.seed(seed_val)
    try:
        import numpy as np
        np.random.seed(seed_val)
    except ModuleNotFoundError:
        pass


if getattr(sys, "frozen", False):
    # if you’ve bundled into an executable
    base_dir = sys._MEIPASS
else:
    base_dir = os.path.dirname(os.path.abspath(__file__))

skip_to_next_stage = False

grid_lines = []


def create_grid_lines(win, grid_spacing=100, grid_color="gray", opacity=0.2):
    """Create a grid of lines for the background of the N-back tasks.

    Args:
        win (psychopy.visual.Window): The PsychoPy window to draw the grid on.
        grid_spacing (int, optional): Distance between grid lines in pixels. Defaults to 100.
        grid_color (str, optional): Color of the grid lines (e.g., 'gray'). Defaults to 'gray'.
        opacity (float, optional): Opacity of grid lines (0 to 1). Defaults to 0.2.

    Returns:
        list: List of visual.Line objects representing the grid.
    """
    win_width, win_height = win.size
    half_width = win_width / 2
    half_height = win_height / 2

    lines = []
    num_vertical_lines = int(win_width // grid_spacing) + 2
    num_horizontal_lines = int(win_height // grid_spacing) + 2

    start_x = -(num_vertical_lines // 2) * grid_spacing + grid_spacing / 2
    x_positions = [start_x + i * grid_spacing for i in range(num_vertical_lines)]

    start_y = -(num_horizontal_lines // 2) * grid_spacing + grid_spacing / 2
    y_positions = [start_y + i * grid_spacing for i in range(num_horizontal_lines)]

    for x in x_positions:
        line = visual.Line(
            win, start=(x, -half_height), end=(x, half_height), lineColor=grid_color, opacity=opacity, units="pix"
        )
        lines.append(line)

    for y in y_positions:
        line = visual.Line(
            win, start=(-half_width, y), end=(half_width, y), lineColor=grid_color, opacity=opacity, units="pix"
        )
        lines.append(line)

    return lines


def draw_grid():
    """Render the background grid lines into the current PsychoPy window.

    Side effects:
        Draws all Line stimuli stored in the global `grid_lines` list
        onto the global `win` before the next `win.flip()`.

    Returns:
        None
    """
    for line in grid_lines:
        line.draw()


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
    instructions = (
        "Sequential N-back Task\n\n"
        "You can choose your starting level:\n"
        "Press '2' for 2-back\n"
        "Press '3' for 3-back\n\n"
        "Press the corresponding key to begin."
    )
    instruction_text = visual.TextStim(win, text=instructions, color="white", height=24, wrapWidth=800)
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
    On‑screen wizard (same look‑and‑feel as the main script) that asks for:
        • RNG seed   (optional, blank = random)
        • Distractor flashes ON / OFF
    Returns dict {"Seed": int|None, "Distractors": bool}
    """
    win.mouseVisible = False
    txt = dict(height=24, color="white", wrapWidth=900)

    # 1) Seed entry
    seed_str = ""
    while True:
        visual.TextStim(win, text="Optional: enter RNG seed  (Blank = Random) then press return", **txt, pos=(0, 120)).draw()
        visual.Rect(win, width=380, height=50, lineColor="white", pos=(0, 40)).draw()
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

    # 2) Distractor toggle
    while True:
        prompt = "Enable 200 ms distractor flashes?\n\nPress Y for ON   |   N for OFF"
        visual.TextStim(win, text=prompt, **txt).draw(); win.flip()
        key = event.waitKeys(keyList=["y", "n"])[0]
        distractors = (key == "y"); break

    win.flip()
    return {"Seed": seed_val, "Distractors": distractors}


def error_catcher(type, value, tb):
    """Custom exception hook to handle and display errors gracefully.

    Args:
        type: The exception type.
        value: The exception instance.
        tb: The traceback object.

    Note:
        Prints error details and waits for user input before exiting.
    """
    print("An error occurred:")
    print("Type:", type)
    print("Value:", value)
    traceback.print_tb(tb)
    input("Press Enter to exit...")
    sys.exit(1)


sys.excepthook = error_catcher

print("Starting script...")
print("Creating window...")

try:
    win = visual.Window(fullscr=False, color="black", units="pix")
    print("Window created successfully.")
    grid_lines = create_grid_lines(win)
except Exception as e:
    print(f"Error creating window: {e}")
    input("Press Enter to exit...")
    sys.exit(1)

# ────────────────────────────────────────────────────────────────
#  Step 3: on‑screen wizard → update globals → seed the RNGs
# ────────────────────────────────────────────────────────────────
options               = get_practice_options(win)   # ask Seed & Distractors
GLOBAL_SEED           = options["Seed"]
DISTRACTORS_ENABLED   = options["Distractors"]
_apply_seed(GLOBAL_SEED)                            # seed Python + NumPy

# ────────────────────────────────────────────────────────────────
event.globalKeys.add(key="escape", func=core.quit)

# point at the stimuli folder next to this script
image_dir   = os.path.join(base_dir, "Abstract Stimuli", "apophysis")
image_files = [f for f in os.listdir(image_dir) if f.endswith(".png")]

if len(image_files) < 22:
    print("Not enough images found in directory")
    sys.exit(1)


def show_pilot_entry_screen():
    """Display an initial welcome screen outlining the practice session structure.

    Informs participants about the three N-back task types and waits for 'space' to begin.

    Raises:
        SystemExit: If 'escape' is pressed, the program exits.
    """
    pilot_text = (
        "Welcome to the N-back Practice Session\n\n"
        "You will complete three types of tasks:\n\n"
        "1. Spatial N-back (2 x 2-minute blocks)\n"
        "2. Dual N-back (2 x 2-minute blocks)\n"
        "3. Sequential N-back (until performance stabilises)\n\n"
        "Press 'space' to begin."
    )
    pilot_message = visual.TextStim(win, text=pilot_text, color="white", height=24, wrapWidth=800)
    pilot_message.draw()
    win.flip()
    event.waitKeys(keyList=["space"])



def show_task_instructions(win, task_name, n_back_level=None):
    """Display task-specific instructions based on the task type.

    Args:
        win (psychopy.visual.Window): The PsychoPy window to draw instructions on.
        task_name (str): The task type ('spatial', 'dual', or 'sequential').
        n_back_level (int, optional): The N-back level for sequential tasks (2 or 3). Defaults to None.

    Raises:
        SystemExit: If 'escape' is pressed, the program exits.
    """
    welcome_text = f"Welcome to the {task_name} Task\n\n"
    welcome_text += "You will first complete a demonstration, followed by a practice session.\n\n"

    if task_name.lower() == "sequential":
        nb = n_back_level if n_back_level in [2, 3] else 2
        welcome_text += (
            "You will see a series of images displayed one after another.\n"
            f"Your task is to decide if the current image matches the image from {nb} steps back.\n\n"
            "Press 'Z' if the current image matches the image from N steps back.\n"
            "Press 'M' if it does not match.\n\n"
            f"No response is required for the first {nb} images.\n"
            "After that, you must respond to every image.\n\n"
            "**Important:**\n"
            "- A grid will be displayed in the background during the task. This grid is **not part of the task**. "
            "Please **ignore it** and focus solely on the images.\n"
            "- Occasionally, a brief distractor image (a square) will appear. "
            "**Ignore these distractors** and stay focused on the main task.\n\n"
            "Respond as quickly and accurately as possible.\n"
        )
    elif task_name.lower() == "spatial":
        welcome_text += (
            "You will see a series of positions highlighted on a circular grid.\n"
            "Your task is to decide if the current position matches the position from N steps back (starting at N = 2).\n\n"
            "Press 'Z' if the current position matches the position N steps back.\n"
            "Press 'M' if it does not match.\n\n"
            "No response is required for the first two positions.\n"
            "After that, you must respond to every position.\n\n"
            "**Important:**\n"
            "- A grid will be displayed in the background. This grid is **not part of the task**.\n\n"
            "Respond as quickly and accurately as possible.\n"
        )
    elif task_name.lower() == "dual":
        welcome_text += (
            "You will see a sequence of images and corresponding positions on a grid.\n"
            "Your task is to decide if BOTH the image AND the position match those from N steps back (starting at N = 2).\n\n"
            "Press 'Z' if both the image and position match.\n"
            "Press 'M' if either the image or the position (or both) do not match.\n\n"
            "No response is required for the first two trials.\n"
            "After that, you must respond to every trial.\n\n"
            "**Important:**\n"
            "- A grid will be displayed in the background. This grid is **not part of the task**.\n\n"
            "Respond as quickly and accurately as possible.\n"
        )
    else:
        welcome_text += "(No specific instructions available for this task.)\n\n"

    instruction_text = visual.TextStim(win, text=welcome_text, color="white", height=24, wrapWidth=800)
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
    """Display a 3-2-1 countdown sequence before each task block.

    Uses a 1-second interval for each number, drawn on the global `win`.
    """
    for i in [3, 2, 1]:
        countdown_message = visual.TextStim(win, text=str(i), color="white", height=72)
        countdown_message.draw()
        win.flip()
        core.wait(1)


def display_feedback(win, correct, pos=(0, 400)):
    """Display feedback symbol (✓ or ✗) based on response correctness.

    Args:
        win (psychopy.visual.Window): The PsychoPy window to draw feedback on.
        correct (bool): True for correct response, False for incorrect.
        pos (tuple, optional): Position (x, y) of the feedback symbol. Defaults to (0, 400).
    """
    feedback_symbol = "✓" if correct else "✗"
    feedback_color = "green" if correct else "red"
    feedback_stim = visual.TextStim(win, text=feedback_symbol, color=feedback_color, height=48, pos=pos)
    feedback_stim.draw()


def display_block_results(task_name, accuracy, num_correct, num_incorrect, num_lapses):
    """Display performance summary after each N-back practice block.

    Args:
        task_name (str): The task type ('Spatial', 'Dual', or 'Sequential').
        accuracy (float): Percentage accuracy of the block.
        num_correct (int): Number of correct responses.
        num_incorrect (int): Number of incorrect responses.
        num_lapses (int): Number of missed responses.

    Raises:
        SystemExit: If 'escape' is pressed, the program exits.
    """
    results_text = (
        f"{task_name} N-back Block Results\n\n"
        f"Accuracy: {accuracy:.1f}%\n"
        f"Correct Responses: {num_correct}\n"
        f"Incorrect Responses: {num_incorrect}\n"
        f"Missed Responses: {num_lapses}\n\n"
        "Press 'space' to continue."
    )
    results_stim = visual.TextStim(win, text=results_text, color="white", height=24, wrapWidth=800)
    results_stim.draw()
    win.flip()
    event.waitKeys(keyList=["space"])


def show_spatial_demo(win, n=2, num_demo_trials=6, display_duration=1.0, isi=1.0):
    """Run a two-pass demo for the Spatial N-back task.

    PASS 1: Normal speed with brief feedback.
    PASS 2: Explanatory pass with extended feedback and space-to-proceed.

    Args:
        win (psychopy.visual.Window): The PsychoPy window to draw the demo on.
        n (int, optional): The N-back level. Defaults to 2.
        num_demo_trials (int, optional): Number of trials in the demo. Defaults to 6.
        display_duration (float, optional): Duration to display each stimulus. Defaults to 1.0.
        isi (float, optional): Inter-stimulus interval. Defaults to 1.0.

    Raises:
        SystemExit: If 'escape' or '5' is pressed, the demo skips.
    """

    # Generate a 6-trial sequence (using ~40% targets)
    demo_positions = generate_positions_with_matches(num_demo_trials, n, target_percentage=0.4)

    # ---------------------------------------------------------------------
    # INTRO SCREEN
    # ---------------------------------------------------------------------
    intro_text = (
        f"Spatial {n}-back Demo\n\n"
        f"We will show {num_demo_trials} trials in two passes:\n"
        "  1) Normal speed (brief feedback)\n"
        "  2) Slowed/Explanatory version – after extended feedback, press SPACE to proceed\n\n"
        "Press SPACE to begin."
    )
    intro_stim = visual.TextStim(win, text=intro_text, color="white", height=24, wrapWidth=800)
    intro_stim.draw()
    win.flip()
    keys = event.waitKeys(keyList=["space", "escape", "5"])
    if "escape" in keys or "5" in keys:
        return

    # ---------------------------------------------------------------------
    # PASS 1: NORMAL SPEED
    # ---------------------------------------------------------------------
    pass1_text = (
        f"PASS 1: {num_demo_trials} trials at normal speed.\n"
        f"For the first {n} trials, no feedback is shown.\n"
        f"From trial {n + 1} onward, a brief ✓ or ✗ will appear.\n\n"
        "Press SPACE to start PASS 1."
    )
    pass1_stim = visual.TextStim(win, text=pass1_text, color="white", height=24, wrapWidth=800)
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
    pass1_end_text = "End of PASS 1.\nPress SPACE to continue to PASS 2 (Explanatory)."
    pass1_end_stim = visual.TextStim(win, text=pass1_end_text, color="white", height=24, wrapWidth=800)
    pass1_end_stim.draw()
    win.flip()
    keys = event.waitKeys(keyList=["space", "escape", "5"])
    if "escape" in keys or "5" in keys:
        return

    # ---------------------------------------------------------------------
    # PASS 2: EXPLANATORY WITH SPACE-TO-PROCEED (NO FLASHING)
    # ---------------------------------------------------------------------
    pass2_text = (
        f"PASS 2: Replaying the same {num_demo_trials} trials.\n"
        "In this pass, stimuli will remain visible and extended feedback will be shown.\n"
        "If there's a mismatch, the old square will be highlighted in orange alongside the current square.\n\n"
        "Press SPACE to begin PASS 2."
    )
    pass2_stim = visual.TextStim(win, text=pass2_text, color="white", height=24, wrapWidth=800)
    pass2_stim.draw()
    win.flip()
    keys = event.waitKeys(keyList=["space", "escape", "5"])
    if "escape" in keys or "5" in keys:
        return

    # Reset queue for PASS 2
    nback_queue = []
    for i, current_pos in enumerate(demo_positions):
        trial_num = i + 1

        # Calculate positions on the circle for current position
        radius = 150
        angles = [idx * (360 / 12) for idx in range(12)]
        cur_x = radius * math.cos(math.radians(angles[current_pos]))
        cur_y = radius * math.sin(math.radians(angles[current_pos]))
        current_rect = visual.Rect(win, width=50, height=50, pos=(cur_x, cur_y), fillColor="white")

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
                mismatch_rect = visual.Rect(win, width=50, height=50, pos=(old_x, old_y), fillColor="orange")
                mismatch_rect.draw()

            if is_target:
                fb_text = f"If you remember, {n} steps back, this was the highlighted square. (✓)"
            else:
                fb_text = f"If you remember, {n} steps back, that was a different square. (✗)"

            feedback_stim = visual.TextStim(win, text=fb_text, color="white", height=24, pos=(0, -250), wrapWidth=800)
            feedback_stim.draw()
            display_feedback(win, is_target, pos=(0, 400))

            # Add the prompt for the next step
            if trial_num == num_demo_trials:
                proceed_text = "This was the final trial. Press SPACE to finish the demo."
            else:
                proceed_text = "Press SPACE to proceed to the next trial."

            proceed_stim = visual.TextStim(
                win, text=proceed_text, color="white", height=24, wrapWidth=800, pos=(0, -280)
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
                proceed_text = "This was the final trial. Press SPACE to finish the demo."
            else:
                proceed_text = "Press SPACE to proceed to the next trial."

            proceed_stim = visual.TextStim(
                win, text=proceed_text, color="white", height=24, wrapWidth=800, pos=(0, -280)
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
    pass2_end_text = "End of PASS 2 (Explanatory).\nPress SPACE to finish the demo."
    pass2_end_stim = visual.TextStim(win, text=pass2_end_text, color="white", height=24, wrapWidth=800)
    pass2_end_stim.draw()
    win.flip()
    keys = event.waitKeys(keyList=["space", "escape", "5"])
    if "escape" in keys or "5" in keys:
        return


def show_dual_demo(win, n=2, num_demo_trials=6, display_duration=1.0, isi=1.2):
    """
    Dual 2-back Demo in two passes:

      PASS 1 (Normal):
        - 6 trials at normal speed.
        - Each trial: present the dual stimulus for display_duration,
          then clear it and wait for a full delay period (isi) before showing brief feedback
          (tick/cross) for trials > n.

      PASS 2 (Explanatory):
        - Replays the same 6 trials.
        - Each trial: present the dual stimulus and keep it visible throughout the explanation.
        - Immediately show extended feedback without clearing the stimulus:
            * If there's a mismatch, show the old stimulus with an orange border alongside
              the current stimulus.
            * Display explanatory text.
        - The extended feedback remains for 2 seconds, then a prompt appears asking the user to press SPACE.
          On the final trial, the prompt reads "This was the final trial. Press SPACE to finish the demo."

    Pressing "5" (or "escape") at any prompt will skip the demo.
    """
    # Generate a 6-trial demo sequence using your dual task generator.
    grid_size = 3
    demo_positions, demo_images = generate_dual_nback_sequence(num_demo_trials, grid_size, n, target_rate=0.4)

    # ---------------------------------------------------------------------
    # INTRO SCREEN
    # ---------------------------------------------------------------------
    intro_text = (
        f"Dual {n}-back Demo\n\n"
        f"We will show {num_demo_trials} trials in two passes:\n"
        "  1) Normal speed (brief feedback)\n"
        "  2) Extended/Explanatory version – after extended feedback, press SPACE to proceed\n\n"
        "Press SPACE to begin."
    )
    intro_stim = visual.TextStim(win, text=intro_text, color="white", height=24, wrapWidth=800)
    intro_stim.draw()
    win.flip()
    keys = event.waitKeys(keyList=["space", "escape", "5"])
    if "escape" in keys or "5" in keys:
        return

    # ---------------------------------------------------------------------
    # PASS 1: NORMAL SPEED
    # ---------------------------------------------------------------------
    pass1_text = (
        f"PASS 1: {num_demo_trials} trials at normal speed.\n"
        f"For the first {n} trials, no feedback is shown.\n"
        f"From trial {n + 1} onward, a brief tick (✓) or cross (✗) will appear.\n\n"
        "Press SPACE to start PASS 1."
    )
    pass1_stim = visual.TextStim(win, text=pass1_text, color="white", height=24, wrapWidth=800)
    pass1_stim.draw()
    win.flip()
    keys = event.waitKeys(keyList=["space", "escape", "5"])
    if "escape" in keys or "5" in keys:
        return

    nback_queue = []
    for i, (pos, img) in enumerate(zip(demo_positions, demo_images)):
        trial_num = i + 1

        # Present the dual stimulus.
        dual_stim = display_dual_stimulus(win, pos, img, grid_size, n_level=n, return_stim=True)
        grid, outline = create_grid(win, grid_size)
        level_text = visual.TextStim(win, text=f"Level: {n}-back", color="white", height=24, pos=(-450, 350))

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
    pass1_end_text = "End of PASS 1.\nPress SPACE to continue to PASS 2 (Explanatory)."
    pass1_end_stim = visual.TextStim(win, text=pass1_end_text, color="white", height=24, wrapWidth=800)
    pass1_end_stim.draw()
    win.flip()
    keys = event.waitKeys(keyList=["space", "escape", "5"])
    if "escape" in keys or "5" in keys:
        return

    # ---------------------------------------------------------------------
    # PASS 2: EXPLANATORY WITH SPACE-TO-PROCEED (NO FLASHING)
    # ---------------------------------------------------------------------
    pass2_text = (
        f"PASS 2: Replaying the same {num_demo_trials} trials.\n"
        "In this pass, stimuli will remain visible and extended feedback will be shown.\n"
        "If there's a mismatch, the old stimulus will be highlighted with an orange border\n"
        "alongside the current stimulus.\n\n"
        "Press SPACE to begin PASS 2."
    )
    pass2_stim = visual.TextStim(win, text=pass2_text, color="white", height=24, wrapWidth=800)
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
        dual_stim = display_dual_stimulus(win, pos, img, grid_size, n_level=n, return_stim=True)
        grid, outline = create_grid(win, grid_size)
        level_text = visual.TextStim(win, text=f"Level: {n}-back", color="white", height=24, pos=(-450, 350))

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
            core.wait(display_duration)  # Wait the display duration but keep stimulus visible

            old_pos, old_img = nback_queue[-n]
            is_target = pos == old_pos and img == old_img

            # Redraw everything including current stimulus
            draw_current_state(True)

            # If mismatch, also draw the old stimulus with an orange border
            if not is_target:
                old_stim = display_dual_stimulus(win, old_pos, old_img, grid_size, n_level=n, return_stim=True)
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
                fb_text = f"If you remember, {n} steps back, this was the dual stimulus. (✓)"
            else:
                fb_text = f"If you remember, {n} steps back, that was a different dual stimulus. (✗)"

            feedback_stim = visual.TextStim(win, text=fb_text, color="white", height=24, pos=(0, -250), wrapWidth=800)
            feedback_stim.draw()
            display_feedback(win, is_target, pos=(0, 400))

            if trial_num == num_demo_trials:
                proceed_text = "This was the final trial. Press SPACE to finish the demo."
            else:
                proceed_text = "Press SPACE to proceed to the next trial."

            proceed_stim = visual.TextStim(
                win, text=proceed_text, color="white", height=24, wrapWidth=800, pos=(0, -280)
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
                proceed_text = "This was the final trial. Press SPACE to finish the demo."
            else:
                proceed_text = "Press SPACE to proceed to the next trial."

            proceed_stim = visual.TextStim(
                win, text=proceed_text, color="white", height=24, wrapWidth=800, pos=(0, -280)
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
    pass2_end_text = "End of PASS 2 (Explanatory).\nPress SPACE to finish the demo."
    pass2_end_stim = visual.TextStim(win, text=pass2_end_text, color="white", height=24, wrapWidth=800)
    pass2_end_stim.draw()
    win.flip()
    keys = event.waitKeys(keyList=["space", "escape", "5"])
    if "escape" in keys or "5" in keys:
        return


def compute_positions_ref(num_items, ref_index, spacing=110, center_x=0, y=0):
    """Compute evenly spaced horizontal positions with a reference index at center_x.

    Args:
        num_items (int): Total number of items to position.
        ref_index (int): Index of the item to place at center_x.
        spacing (int, optional): Distance between items in pixels. Defaults to 110.
        center_x (int, optional): X-coordinate of the reference position. Defaults to 0.
        y (int, optional): Y-coordinate for all positions. Defaults to 0.

    Returns:
        list: List of (x, y) tuples for each position.
    """
    positions = []
    for i in range(num_items):
        x = center_x + (i - ref_index) * spacing
        positions.append((x, y))
    return positions


def draw_sequence(win, seq_images, positions, size=(100, 100), current_idx=None):
    """Draw a sequence of images at specified positions.

    Args:
        win (psychopy.visual.Window): The PsychoPy window to draw on.
        seq_images (list): List of image file names.
        positions (list): List of (x, y) position tuples.
        size (tuple, optional): Size (width, height) of each image. Defaults to (100, 100).
        current_idx (int, optional): Index of the current image (for highlighting). Defaults to None.
    """
    for i, (img_file, pos) in enumerate(zip(seq_images, positions)):
        stim = visual.ImageStim(win, image=os.path.join(image_dir, img_file), pos=pos, size=size)
        stim.draw()


def draw_center_frame(win, current_pos, size):
    """Draw a white rectangular frame around the current stimulus.

    Args:
        win (psychopy.visual.Window): The PsychoPy window to draw on.
        current_pos (tuple): (x, y) position of the current stimulus.
        size (tuple): (width, height) of the stimulus.
    """
    frame = visual.Rect(
        win, width=size[0] + 20, height=size[1] + 20, pos=current_pos, lineColor="white", fillColor=None, lineWidth=2
    )
    frame.draw()


def draw_n_back_box(win, pos, size, is_match):
    """Draw a colored box around the n-back position based on match status.

    Args:
        win (psychopy.visual.Window): The PsychoPy window to draw on.
        pos (tuple): (x, y) position of the n-back stimulus.
        size (tuple): (width, height) of the stimulus.
        is_match (bool): True if the n-back matches, False otherwise.
    """
    border_color = "green" if is_match else "red"
    border = visual.Rect(
        win, width=size[0] + 10, height=size[1] + 10, pos=pos, lineColor=border_color, lineWidth=4, fillColor=None
    )
    border.draw()


def show_sequential_demo(win, n=2, num_demo_trials=6, display_duration=0.8, isi=1.0):
    """
    Sequential N-back Demo in two passes.

    PASS 1 (Normal):
      - Each trial is presented individually.
      - The current stimulus is shown centered for display_duration,
        then cleared for a full ISI delay.
      - For trials > n, a brief tick (✓) or cross (✗) feedback is shown.

    PASS 2 (Explanatory – Moving Window):
      - The entire sequence is preloaded and displayed as a horizontal row.
      - A frame is drawn only around the current trial stimulus.
      - The positions are computed so that on the first trial, the stimulus from trial n (index n-1) is at x = 0.
      - On each subsequent trial, the entire sequence shifts left by a fixed amount (spacing) so that the reference remains centered.
      - For trials > n, the n-back stimulus is highlighted with a green border for correct matches or red for incorrect.
      - Each trial advances with a spacebar press, with concise feedback.

    Pressing "5" or "escape" at any prompt will skip the demo.
    """
    # Generate the demo sequence.
    demo_sequence, _ = generate_sequential_image_sequence(num_demo_trials, n, target_percentage=0.4)

    # -------------- PASS 1: NORMAL --------------
    intro_text = (
        "Sequential 2-back Demo (PASS 1: Normal)\n\n"
        f"We will present {num_demo_trials} trials one by one.\n"
        f"For the first {n} trials, no feedback is given.\n"
        f"From trial {n + 1} onward, brief feedback (✓ or ✗) is shown.\n\n"
        "Press SPACE to start PASS 1."
    )
    intro_stim = visual.TextStim(win, text=intro_text, color="white", height=24, wrapWidth=800)
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
        stim = visual.ImageStim(win, image=os.path.join(image_dir, img), pos=(0, 0), size=stim_size)
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
                fb = visual.TextStim(win, text="✓", color="green", height=48, pos=(0, 150))
            else:
                fb = visual.TextStim(win, text="✗", color="red", height=48, pos=(0, 150))
            fb.draw()
            win.flip()
            core.wait(0.5)
        else:
            core.wait(0.5)
        core.wait(0.2)

    end_pass1 = visual.TextStim(
        win,
        text="End of PASS 1.\nPress SPACE to continue to PASS 2 (Explanatory).",
        color="white",
        height=24,
        wrapWidth=800,
    )
    end_pass1.draw()
    win.flip()
    keys = event.waitKeys(keyList=["space", "escape", "5"])
    if "escape" in keys or "5" in keys:
        return

    # -------------- PASS 2: EXPLANATORY (MOVING WINDOW) --------------
    pass2_text = (
        "Sequential 2-back Demo (PASS 2: Explanatory)\n\n"
        "The entire sequence is now shown as a horizontal row.\n"
        "On each trial, the sequence shifts left so that the 2-back position remains centered.\n"
        "The current stimulus has a white frame around it.\n"
        "The 2-back position will be highlighted in green (if matched) or red (if not matched).\n\n"
        "Press SPACE to start PASS 2."
    )
    pass2_stim = visual.TextStim(win, text=pass2_text, color="white", height=24, wrapWidth=800)
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
    positions0 = compute_positions_ref(num_demo_trials, ref_index=0, spacing=spacing, center_x=0, y=0)

    for i in range(num_demo_trials):
        trial_num = i + 1
        # Compute shifted positions so that the current trial is centered
        shifted_positions = [(x - i * spacing, y) for (x, y) in positions0]

        # Draw level indicator
        level_stim = visual.TextStim(win, text=f"Level: {n}-back", color="white", height=24, pos=(-450, 350))
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
                tick = visual.TextStim(win, text="✓", color="green", height=48, pos=(0, 150))
                fb_text = "Correct match: Same as 2-back."
            else:
                tick = visual.TextStim(win, text="✗", color="red", height=48, pos=(0, 150))
                fb_text = "No match: Different from 2-back."
            tick.draw()

            # Show concise feedback text
            feedback_stim = visual.TextStim(win, text=fb_text, color="white", height=24, pos=(0, -250))
            feedback_stim.draw()
        else:
            # For trials before or equal to n, explain why there's no reference yet
            if trial_num < n:
                fb_text = f"Building up sequence ({trial_num}/{n} trials)."
            else:  # trial_num == n
                fb_text = (
                    f"This is trial {n}. We need to wait until trial {n + 1} to have a complete {n}-back reference."
                )
            feedback_stim = visual.TextStim(win, text=fb_text, color="white", height=24, pos=(0, -250))
            feedback_stim.draw()

        # Show prompt for all trials
        if trial_num == num_demo_trials:
            prompt_text = "This was the final trial. Press SPACE to finish the demo."
        else:
            prompt_text = "Press SPACE to proceed to the next trial."
        prompt_stim = visual.TextStim(win, text=prompt_text, color="white", height=24, pos=(0, -300))
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
        text="End of PASS 2 (Explanatory).\nPress SPACE to finish the demo.",
        color="white",
        height=24,
        wrapWidth=800,
    )
    end_pass2.draw()
    win.flip()
    keys = event.waitKeys(keyList=["space", "escape", "5"])
    if "escape" in keys or "5" in keys:
        return


def generate_positions_with_matches(num_positions, n, target_percentage=0.5):
    """Generate a sequence of positions with specified target percentage.

    Args:
        num_positions (int): Total number of positions to generate.
        n (int): The N-back level.
        target_percentage (float, optional): Percentage of trials that are targets. Defaults to 0.5.

    Returns:
        list: Sequence of position indices (0-11).
    """
    positions = list(range(12))
    sequence = [random.choice(positions) for _ in range(num_positions)]

    num_targets = int((num_positions - n) * target_percentage)
    target_indices = random.sample(range(n, num_positions), num_targets)

    for idx in target_indices:
        sequence[idx] = sequence[idx - n]

    return sequence


def get_level_color(n_level):
    """Return a color based on the N-back level.

    Args:
        n_level (int): The N-back level (1, 2, or 3).

    Returns:
        str: Color name ('white', 'lightblue', 'lightgreen', or 'white' for other levels).
    """
    if n_level == 1:
        return "white"
    elif n_level == 2:
        return "lightblue"
    elif n_level == 3:
        return "lightgreen"
    else:
        return "white"


def display_grid(win, highlight_pos=None, highlight=False, n_level=None, feedback_text=None, lapse_feedback=None):
    """Display a circular grid with optional highlighted position and feedback.

    Args:
        win (psychopy.visual.Window): The PsychoPy window to draw on.
        highlight_pos (int, optional): Index of position to highlight (0-11). Defaults to None.
        highlight (bool, optional): Whether to highlight a position. Defaults to False.
        n_level (int, optional): The N-back level for color. Defaults to None.
        feedback_text (str, optional): Text to display as feedback. Defaults to None.
        lapse_feedback (str, optional): Text to display for lapses. Defaults to None.
    """
    radius = 150
    center = (0, 0)
    num_positions = 12
    angles = [i * (360 / num_positions) for i in range(num_positions)]
    positions = [
        (center[0] + radius * math.cos(math.radians(angle)), center[1] + radius * math.sin(math.radians(angle)))
        for angle in angles
    ]

    grid_color = get_level_color(n_level)

    fixation_cross = visual.TextStim(win, text="+", color="white", height=32)
    fixation_cross.draw()

    for i, pos in enumerate(positions):
        rect = visual.Rect(win, width=50, height=50, pos=pos, lineColor=grid_color, lineWidth=2)
        rect.draw()

    if highlight and highlight_pos is not None:
        highlight_color = "white"
        highlight = visual.Rect(win, width=50, height=50, pos=positions[highlight_pos], fillColor=highlight_color)
        highlight.draw()

    if feedback_text:
        feedback_message = visual.TextStim(win, text=feedback_text, color=grid_color, height=24, pos=(0, 250))
        feedback_message.draw()

    if lapse_feedback:
        lapse_message = visual.TextStim(win, text=lapse_feedback, color="orange", height=24, pos=(0, 300))
        lapse_message.draw()

    if n_level:
        level_indicator = visual.TextStim(
            win, text=f"Level: {n_level}-back", color="white", height=24, pos=(-450, 350), alignText="left"
        )
        level_indicator.draw()


def run_spatial_nback_practice(n, num_trials=50, display_duration=1.0, isi=1.0):
    """Run a single block of Spatial N-back practice.

    Args:
        n (int): The N-back level.
        num_trials (int, optional): Number of trials in the block. Defaults to 50.
        display_duration (float, optional): Duration to display each stimulus. Defaults to 1.0.
        isi (float, optional): Inter-stimulus interval. Defaults to 1.0.

    Returns:
        tuple: (accuracy, correct_responses, incorrect_responses, lapses) for the block.

    Raises:
        SystemExit: If 'escape' is pressed, the program exits.
    """
    global skip_to_next_stage
    positions = generate_positions_with_matches(num_trials, n)
    nback_queue = []
    correct_responses = 0
    incorrect_responses = 0
    lapses = 0
    total_reaction_time = 0
    reaction_times = []
    responses = []

    lapse_feedback = None

    initial_feedback = f"No response required for the first {n} trials"
    draw_grid()  # Add background grid
    feedback_text = visual.TextStim(win, text=initial_feedback, color=get_level_color(n), height=24, pos=(0, 0))
    feedback_text.draw()
    win.flip()
    core.wait(2)

    draw_grid()  # Add background grid
    win.flip()
    core.wait(0.5)

    for i, pos in enumerate(positions):
        if skip_to_next_stage:
            break  # Exit the task early

        is_target = len(nback_queue) >= n and pos == nback_queue[-n]

        display_grid(win, highlight_pos=pos, highlight=True, n_level=n, lapse_feedback=lapse_feedback)
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

        if response is None and i >= n:
            lapses += 1
            responses.append((i + 1, pos, is_target, None, None))
            lapse_feedback = "Previous lapse, please respond"
        else:
            lapse_feedback = None

        nback_queue.append(pos)
        if len(nback_queue) > n:
            nback_queue.pop(0)

        event.clearEvents()

    total_responses = correct_responses + incorrect_responses + lapses
    accuracy = (correct_responses / total_responses) * 100 if total_responses > 0 else 0
    avg_reaction_time = sum(reaction_times) / len(reaction_times) if reaction_times else 0

    return accuracy, correct_responses, incorrect_responses, lapses


def generate_dual_nback_sequence(num_trials, grid_size, n, target_rate=0.5):
    """Generate a dual N-back sequence of positions and images.

    Args:
        num_trials (int): Number of trials to generate.
        grid_size (int): Size of the grid (e.g., 3 for 3x3).
        n (int): The N-back level.
        target_rate (float, optional): Rate of target trials. Defaults to 0.5.

    Returns:
        tuple: (list of positions, list of image file names).
    """
    positions = [(x, y) for x in range(grid_size) for y in range(grid_size)]
    pos_seq = [random.choice(positions) for _ in range(num_trials)]
    image_seq = [random.choice(image_files) for _ in range(num_trials)]

    num_targets = int((num_trials - n) * target_rate)
    target_indices = random.sample(range(n, num_trials), num_targets)

    for idx in target_indices:
        pos_seq[idx] = pos_seq[idx - n]
        image_seq[idx] = image_seq[idx - n]

    return pos_seq, image_seq


def display_dual_stimulus(win, pos, image_file, grid_size, n_level, return_stim=False):
    """Display a dual stimulus (position and image) on a grid.

    Args:
        win (psychopy.visual.Window): The PsychoPy window to draw on.
        pos (tuple): (x, y) position on the grid.
        image_file (str): Path or name of the image file.
        grid_size (int): Size of the grid (e.g., 3 for 3x3).
        n_level (int): The N-back level.
        return_stim (bool, optional): Whether to return the stimulus object. Defaults to False.

    Returns:
        psychopy.visual.ImageStim: The stimulus object if return_stim is True.
    """
    grid_length = 600 * 0.8
    cell_length = grid_length // grid_size
    top_left = (-grid_length // 2, grid_length // 2)
    x, y = top_left[0] + pos[0] * cell_length, top_left[1] - pos[1] * cell_length

    image_path = os.path.join(image_dir, image_file)
    image_stim = visual.ImageStim(
        win,
        image=image_path,
        pos=(x + cell_length // 2, y - cell_length // 2),
        size=(cell_length - 10, cell_length - 10),
    )

    if return_stim:
        return image_stim
    else:
        image_stim.draw()
        win.flip()


def create_grid(win, grid_size):
    """Create a grid of rectangles for the Dual N-back task.

    Args:
        win (psychopy.visual.Window): The PsychoPy window to draw on.
        grid_size (int): Size of the grid (e.g., 3 for 3x3).

    Returns:
        tuple: (list of Rect objects, outline Rect object).
    """
    grid_length = 600 * 0.8
    cell_length = grid_length // grid_size
    top_left = (-grid_length // 2, grid_length // 2)

    grid = []
    for i in range(grid_size):
        for j in range(grid_size):
            rect = visual.Rect(
                win,
                width=cell_length,
                height=cell_length,
                pos=(
                    top_left[0] + i * cell_length + cell_length // 2,
                    top_left[1] - j * cell_length - cell_length // 2,
                ),
                lineColor="white",
                fillColor=None,
            )
            grid.append(rect)

    outline = visual.Rect(
        win, width=grid_length, height=grid_length, pos=(0, 0), lineColor="white", fillColor=None, lineWidth=2
    )

    return grid, outline


def run_dual_nback_practice(n, num_trials=50, display_duration=1.0, isi=1.2):
    """Run a single block of Dual N-back practice.

    Args:
        n (int): The N-back level.
        num_trials (int, optional): Number of trials in the block. Defaults to 50.
        display_duration (float, optional): Duration to display each stimulus. Defaults to 1.0.
        isi (float, optional): Inter-stimulus interval. Defaults to 1.2.

    Returns:
        tuple: (accuracy, correct_responses, incorrect_responses, lapses) for the block.

    Raises:
        SystemExit: If 'escape' is pressed, the program exits.
    """
    global skip_to_next_stage
    grid_size = 3
    positions, images = generate_dual_nback_sequence(num_trials, grid_size, n, target_rate=0.5)
    nback_queue = []
    responses = []
    correct_responses = 0
    incorrect_responses = 0
    lapses = 0
    total_reaction_time = 0
    reaction_times = []

    grid, outline = create_grid(win, grid_size)
    level_color = get_level_color(n)
    level_text = visual.TextStim(win, text=f"Level: {n}-back", color="white", height=24, pos=(-450, 350))

    initial_feedback = f"No response required for the first {n} trials"
    draw_grid()  # Add background grid
    feedback_text = visual.TextStim(win, text=initial_feedback, color=level_color, height=24, pos=(0, 0))
    feedback_text.draw()
    win.flip()
    core.wait(2)

    draw_grid()  # Add background grid
    win.flip()
    core.wait(0.5)

    lapse_feedback = None

    for i, (pos, img) in enumerate(zip(positions, images)):
        if skip_to_next_stage:
            break  # Exit the task early

        is_target = len(nback_queue) >= n and pos == nback_queue[-n][0] and img == nback_queue[-n][1]

        image_stim = display_dual_stimulus(win, pos, img, grid_size, n_level=n, return_stim=True)

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
            lapse_feedback = "Previous lapse, please respond"
        else:
            lapse_feedback = None

        nback_queue.append((pos, img))
        if len(nback_queue) > n:
            nback_queue.pop(0)

        event.clearEvents()

    total_responses = correct_responses + incorrect_responses + lapses
    accuracy = (correct_responses / total_responses) * 100 if total_responses > 0 else 0
    avg_reaction_time = sum(reaction_times) / len(reaction_times) if reaction_times else 0

    return accuracy, correct_responses, incorrect_responses, lapses


def show_break_screen(win, duration):
    """Display a break screen with a countdown timer.

    Shows a message instructing the participant to rest, with a live countdown
    of the remaining time. The task resumes automatically after the duration.

    Args:
        win (psychopy.visual.Window): The PsychoPy window to draw the break screen on.
        duration (float): Duration of the break in seconds.

    Raises:
        SystemExit: If 'escape' is pressed, the program exits.

    Note:
        The countdown updates every frame, showing the remaining seconds.
    """
    break_text = (
        f"Take a {duration}-second break\n\n"
        "Use this time to rest your eyes and relax\n\n"
        "The task will continue automatically"
    )
    break_stim = visual.TextStim(win, text=break_text, color="white", height=24, wrapWidth=800)

    timer = core.CountdownTimer(duration)
    while timer.getTime() > 0:
        break_stim.text = f"{break_text}\n\nTime remaining: {int(timer.getTime())} seconds"
        break_stim.draw()
        win.flip()
        if event.getKeys(["escape"]):
            core.quit()


def check_level_change(block_results, current_level, window_size=2):
    """Determine if the N-back level should change based on recent accuracy.

    Evaluates a rolling average of accuracy over the last `window_size` blocks to decide
    if the N-back level should increase (from 2 to 3 if accuracy ≥ 82%) or decrease
    (from 3 to 2 if accuracy < 70%).

    Args:
        block_results (list): List of tuples (block_count, n_level, accuracy, avg_reaction_time)
            representing past block results.
        current_level (int): Current N-back level (2 or 3).
        window_size (int, optional): Number of recent blocks to average. Defaults to 2.

    Returns:
        int: New N-back level (2 or 3) based on performance criteria.

    Note:
        Returns the current level if no change criteria are met.
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
    """Check if performance has plateaued based on recent accuracy variance.

    Args:
        block_results (list): List of (block_count, n_level, accuracy, avg_reaction_time) tuples.
        variance_threshold (float, optional): Maximum deviation for stability. Defaults to 7%.

    Returns:
        bool: True if performance has plateaued, False otherwise.
    """
    if len(block_results) < 3:
        return False

    # Check if there was a level change in the last three blocks
    last_three_levels = [block[1] for block in block_results[-3:]]
    if len(set(last_three_levels)) > 1:
        return False  # Levels changed, so performance hasn't stabilised

    current_level = block_results[-1][1]
    current_level_blocks = [block for block in block_results[-3:] if block[1] == current_level]

    recent_accuracies = [block[2] for block in current_level_blocks]
    avg_accuracy = sum(recent_accuracies) / len(recent_accuracies)
    deviations = [abs(acc - avg_accuracy) for acc in recent_accuracies]
    stable_blocks = sum(1 for dev in deviations if dev <= variance_threshold)
    return stable_blocks >= 3


def generate_sequential_image_sequence(num_trials, n, target_percentage=0.5):
    """Generate a sequence of images for the Sequential N-back task.

    Creates a sequence with a specified target percentage, avoiding excessive consecutive matches
    and incorporating misleading matches for n=3. Images are selected from the global `image_files`
    list without replacement until exhausted, then recycled.

    Args:
        num_trials (int): Number of trials to generate.
        n (int): The N-back level.
        target_percentage (float, optional): Percentage of trials that are targets. Defaults to 0.5.

    Returns:
        tuple: (list of image file names, list of target indices).

    Note:
        For n=3, approximately 30% of non-target trials include a misleading match (n-1 back).
        Limits consecutive matches to 2 to maintain task difficulty.
    """
    available_images = image_files.copy()
    sequence = []
    max_consecutive_matches = 2
    consecutive_count = 0
    target_num_yes = int((num_trials - n) * target_percentage)
    yes_positions = random.sample(range(n, num_trials), target_num_yes)

    if n == 3:
        misleading_positions = random.sample(
            [p for p in range(n, num_trials) if p not in yes_positions], int(target_num_yes * 0.3)
        )

    for i in range(num_trials):
        if i in yes_positions and consecutive_count < max_consecutive_matches:
            sequence.append(sequence[i - n])
            consecutive_count += 1
        elif n == 3 and i in misleading_positions:
            sequence.append(sequence[i - 2])
            consecutive_count = 0
        else:
            if not available_images:
                available_images = image_files.copy()
            non_matching_images = [
                img
                for img in available_images
                if img not in sequence[-n:] and (len(sequence) < 2 or img != sequence[-2])
            ]
            if not non_matching_images:
                non_matching_images = available_images
            chosen_image = random.choice(non_matching_images)
            sequence.append(chosen_image)
            available_images.remove(chosen_image)
            consecutive_count = 0

    return sequence, yes_positions


def display_image(win, image_file, feedback_text=None):
    """Display a single image with optional feedback text in the Sequential N-back task.

    Args:
        win (psychopy.visual.Window): The PsychoPy window to draw the image on.
        image_file (str): Name of the image file (relative to the image_dir).
        feedback_text (str, optional): Text to display below the image, typically for lapse feedback.
            Defaults to None.

    Note:
        The image is drawn centered with a fixed size of (350, 350) pixels.
        Feedback text, if provided, is drawn in orange below the image.
    """
    image_path = os.path.join(image_dir, image_file)
    image_stim = visual.ImageStim(win, image=image_path, size=(350, 350))
    image_stim.draw()
    if feedback_text:
        feedback_message = visual.TextStim(
            win, text=feedback_text, color="orange", height=24, pos=(0, image_stim.size[1] / 2 + 20)
        )
        feedback_message.draw()
    win.flip()


def run_sequential_nback_practice(n, num_trials=90, target_percentage=0.5, display_duration=0.8, isi=1.0):
    """Run a single block of Sequential N-back practice with distractors.

    Args:
        n (int): The N-back level.
        num_trials (int, optional): Number of trials in the block. Defaults to 90.
        target_percentage (float, optional): Percentage of target trials. Defaults to 0.5.
        display_duration (float, optional): Duration to display each stimulus. Defaults to 0.8.
        isi (float, optional): Inter-stimulus interval. Defaults to 1.0.

    Returns:
        tuple: (accuracy, avg_reaction_time) for the block.

    Raises:
        SystemExit: If 'escape' is pressed, the program exits.
    """
    global skip_to_next_stage

    # Generate the sequence
    images, yes_positions = generate_sequential_image_sequence(num_trials, n, target_percentage)

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
        win, text=f"Level: {n}-back", color="white", height=24, pos=(-450, 350)  # same location as in spatial/dual
    )

    # --- Display initial feedback screen ---
    initial_feedback = f"No response required for the first {n} trials"

    # Draw grid + level indicator
    draw_grid()
    level_text.draw()

    # Then draw the initial feedback text
    feedback_text = visual.TextStim(win, text=initial_feedback, color="white", height=24, pos=(0, 0))
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
            prompt_text = "Previous lapse, please respond"
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
            feedback_stim = visual.TextStim(win, text=prompt_text, color="orange", height=24, pos=(0, 200))
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
                        win, width=100, height=100, fillColor="white", lineColor=None, pos=(0, 0)  # White distractor
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
    avg_reaction_time = (sum(reaction_times) / len(reaction_times)) if reaction_times else 0

    return accuracy, avg_reaction_time


def run_sequential_nback_until_plateau(starting_level):
    """Run Sequential N-back practice until performance plateaus or max blocks are reached.

    Args:
        starting_level (int): Initial N-back level (2 or 3).

    Returns:
        tuple: (final_n_level, final_accuracy, final_avg_rt) from the last block.

    Raises:
        SystemExit: If 'escape' is pressed, the program exits.
    """
    global skip_to_next_stage
    n_level = starting_level
    block_results = []  # Each element: (block_count, n_level, accuracy, avg_reaction_time)
    max_blocks = 12
    scored_trials = 90
    block_count = 0

    while block_count < max_blocks:
        block_count += 1

        # Always use 90 trials per block (no warm-up now)
        num_trials = scored_trials

        # Run the practice block for the current level
        accuracy, avg_reaction_time = run_sequential_nback_practice(n_level, num_trials=num_trials)

        if skip_to_next_stage:
            break  # User skipped the session

        # Record the block result
        block_results.append((block_count, n_level, accuracy, avg_reaction_time))

        # Display a quick summary after each block
        summary_text = (
            f"Sequential N-back Practice Block {block_count} (Level: {n_level}-back):\n\n"
            f"Accuracy: {accuracy:.2f}%\n"
            f"Average Reaction Time: {avg_reaction_time:.2f} s\n\n"
            "Press 'space' to continue."
        )
        summary_stim = visual.TextStim(win, text=summary_text, color="white", height=24, wrapWidth=800)
        summary_stim.draw()
        win.flip()
        event.waitKeys(keyList=["space"])

        # Update the n-back level based on a rolling average of recent blocks.
        new_level = check_level_change(block_results, n_level, window_size=2)
        if new_level != n_level:
            n_level = new_level
            level_change_text = f"Level change: Now switching to {n_level}-back."
            level_change_stim = visual.TextStim(win, text=level_change_text, color="white", height=24, wrapWidth=800)
            level_change_stim.draw()
            win.flip()
            core.wait(2)

        # Plateau check
        if check_plateau(block_results, variance_threshold=7):
            break

        # If max blocks were completed without plateau, warn about unstable performance
        if block_count == max_blocks:
            warning_text = (
                "Maximum number of blocks reached without achieving stable performance.\n\n"
                "Participant may have unstable performance across blocks.\n\n"
                "Press 'space' to continue."
            )
            warning_stim = visual.TextStim(win, text=warning_text, color="orange", height=24, wrapWidth=800)
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
        final_n_level = n_level
        final_accuracy = 0
        final_avg_rt = 0

    return final_n_level, final_accuracy, final_avg_rt


def main():
    """Execute the complete WAND practice protocol.

    Runs Spatial, Dual, and Sequential N-back tasks with demos and practice
    blocks.  Spatial and Dual phases now demand *two consecutive* ≥ 65 % blocks
    before progression.

    Any unhandled exception is caught and printed with traceback.
    """
    global skip_to_next_stage
    try:
        # === Start: Spatial N-back Demo Phase ===
        show_task_instructions(win, "Spatial")
        show_spatial_demo(win, n=2)

        # === Start: Spatial N-back Practice Blocks (two successive ≥ 65 %) ===
        passes = 0
        while passes < 2 and not skip_to_next_stage:
            for _ in range(2):   # always run two blocks per attempt
                show_countdown()
                acc, corr, incorr, lapses = run_spatial_nback_practice(n=2, num_trials=60)
                display_block_results("Spatial", acc, corr, incorr, lapses)

                if skip_to_next_stage:        # user aborted with ‘5’/Esc
                    passes = 2                # force exit
                    break

                passes = passes + 1 if acc >= 65 else 0
                if passes == 2:               # criterion met
                    break

            if passes < 2 and not skip_to_next_stage:
                visual.TextStim(
                    win,
                    text=f"Need 2 successive Spatial blocks ≥ 65 %.  "
                         f"Current streak {passes}/2.\nPress SPACE to retry.",
                    color="white",
                    height=24,
                    wrapWidth=800,
                ).draw()
                win.flip()
                event.waitKeys(keyList=["space"])

        skip_to_next_stage = False  # reset flag

        # === Start: Dual N-back Demo Phase ===
        show_task_instructions(win, "Dual")
        show_dual_demo(win, n=2)

        # === Start: Dual N-back Practice Blocks (two successive ≥ 65 %) ===
        passes = 0
        while passes < 2 and not skip_to_next_stage:
            for _ in range(2):
                show_countdown()
                acc, corr, incorr, lapses = run_dual_nback_practice(n=2, num_trials=60)
                display_block_results("Dual", acc, corr, incorr, lapses)

                if skip_to_next_stage:
                    passes = 2
                    break

                passes = passes + 1 if acc >= 65 else 0
                if passes == 2:
                    break

            if passes < 2 and not skip_to_next_stage:
                visual.TextStim(
                    win,
                    text=f"Need 2 successive Dual blocks ≥ 65 %.  "
                         f"Current streak {passes}/2.\nPress SPACE to retry.",
                    color="white",
                    height=24,
                    wrapWidth=800,
                ).draw()
                win.flip()
                event.waitKeys(keyList=["space"])

        skip_to_next_stage = False

        # === Start: Sequential N-back Demo Phase ===
        show_task_instructions(win, "Sequential", n_back_level=2)
        show_sequential_demo(win, n=2, num_demo_trials=6, display_duration=0.8, isi=1.0)

        # === Start: Sequential N-back Adaptive Practice Phase ===
        starting_level = prompt_starting_level()
        show_countdown()
        final_n_level, final_accuracy, final_avg_rt = run_sequential_nback_until_plateau(starting_level)

        # === Final Summary Screen ===
        final_summary = (
            f"Practice Session Completed!\n\n"
            f"Please note this level for the main induction.\n"
            f"Press 'space' to exit."
        )
        visual.TextStim(win, text=final_summary, color="white",
                        height=24, wrapWidth=800).draw()
        win.flip()
        event.waitKeys(keyList=["space"])

    except Exception as e:
        print(f"Error in main: {e}")
        traceback.print_exc()
    finally:
        win.close()
        core.quit()


if __name__ == "__main__":
    main()
