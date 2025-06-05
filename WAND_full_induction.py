#!/usr/bin/env python3
import csv
import logging
import math
import os
import random
import sys
import time
import argparse

from psychopy import core, event, visual

"""
WAND-fatigue-induction

Full cognitive fatigue induction protocol using the WAND (Working-memory Adaptive-fatigue with N-back Difficulty) model.

Participants complete adaptive Sequential, Spatial, and Dual N-back tasks to induce active mental fatigue,
with detailed behavioural performance and subjective measures collected throughout.

Designed for cognitive fatigue research, including EEG or behavioural-only implementations.

Requires: PsychoPy, Python 3.8+.

Author: Brodie Mangan
Version: 1.0
"""

# Licensed under the MIT License (see LICENSE file for full text)

# --------------- CLI FLAGS (dummy‑run only) ---------------
import argparse, random
parser = argparse.ArgumentParser(add_help=False)
parser.add_argument("--seed", type=int, default=None)          # still allowed but GUI will override
parser.add_argument("--distractors", choices=["on", "off"], default=None)
parser.add_argument("--dummy", action="store_true",
                    help="Run 20‑trial test then exit")
args, _ = parser.parse_known_args()

# placeholders – will be overwritten by the GUI wizard later
GLOBAL_SEED = args.seed                    # None → random each run
DISTRACTORS_ENABLED = (args.distractors != "off") if args.distractors else True


try:
    from scipy.stats import norm
except ImportError:
    logging.error("SciPy is required for d-prime calculation. Install with 'pip install scipy'.")
    core.quit()

# determine where this script lives on _any_ machine

if getattr(sys, "frozen", False):
    # if you’ve bundled into an executable
    base_dir = sys._MEIPASS
else:
    base_dir = os.path.dirname(os.path.abspath(__file__))


# === Experiment Settings ===
FULLSCREEN = True  # Set to False for windowed mode during testing
WINDOW_SIZE = (1200, 800)  # Only used if FULLSCREEN = False
MONITOR_NAME = "testMonitor"  # Update to match lab monitor profile if necessary
BACKGROUND_COLOR = "black"  # Background colour of experiment window
COLOR_SPACE = "rgb"  # Colour space
USE_FBO = True  # Framebuffer object for better rendering
GRID_SPACING = 100  # Grid line spacing in pixels
GRID_COLOR = "gray"  # Colour of grid lines
GRID_OPACITY = 0.2  # Opacity of grid lines
image_dir = os.path.join(base_dir, "Abstract Stimuli", "apophysis")  # Relative path to image folder

# === Logging Configuration ===
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


class FlushFileHandler(logging.FileHandler):
    """Custom file handler that flushes after every log record."""

    def emit(self, record):
        super().emit(record)
        self.flush()


# Suppress verbose PIL (image library) logging
pil_logger = logging.getLogger("PIL")
pil_logger.setLevel(logging.INFO)

# === Create the experiment window ===
win = visual.Window(
    size=WINDOW_SIZE,
    fullscr=FULLSCREEN,
    screen=0,
    allowGUI=False,
    allowStencil=False,
    monitor=MONITOR_NAME,
    color=BACKGROUND_COLOR,
    colorSpace=COLOR_SPACE,
    blendMode="avg",
    useFBO=USE_FBO,
    units="pix",
    winType="pyglet",  # Explicit window type
)

# Determine the base directory
if getattr(sys, "frozen", False):
    # Running as compiled app
    base_dir = sys._MEIPASS
else:
    # Running as script
    base_dir = os.path.dirname(os.path.abspath(__file__))

logging.info("Script started")
logging.debug(f"Python version: {sys.version}")
logging.debug(f"Base directory: {base_dir}")
logging.debug(f"Current working directory: {os.getcwd()}")

try:
    import psychopy

    logging.debug(f"PsychoPy version: {psychopy.__version__}")
except ImportError:
    logging.error("Failed to import PsychoPy")

# After global variables
grid_lines = []
win_units = "pix"  # Ensure consistent units across all stimuli


def create_grid_lines(win, grid_spacing=100, grid_color="gray", opacity=0.2):
    """
    Generate vertical and horizontal grid lines over the experiment window.

    Args:
        win (visual.Window): The PsychoPy window object.
        grid_spacing (int): Distance in pixels between each grid line.
        grid_color (str): Colour of the grid lines.
        opacity (float): Opacity of the grid lines (0 = transparent, 1 = opaque).

    Returns:
        list: A list of PsychoPy Line stimuli representing the grid.
    """
    # Get window size
    win_width, win_height = win.size
    half_width = win_width / 2
    half_height = win_height / 2

    # Create lists to hold the lines
    lines = []

    # Calculate number of lines to draw
    num_vertical_lines = int(win_width // grid_spacing) + 2  # +2 to ensure coverage
    num_horizontal_lines = int(win_height // grid_spacing) + 2

    # Calculate starting positions
    # Shift grid so that the center of a square is at (0,0)
    start_x = -(num_vertical_lines // 2) * grid_spacing + grid_spacing / 2
    x_positions = [start_x + i * grid_spacing for i in range(num_vertical_lines)]

    start_y = -(num_horizontal_lines // 2) * grid_spacing + grid_spacing / 2
    y_positions = [start_y + i * grid_spacing for i in range(num_horizontal_lines)]

    # Now create vertical lines
    for x in x_positions:
        line = visual.Line(
            win, start=(x, -half_height), end=(x, half_height), lineColor=grid_color, opacity=opacity, units="pix"
        )
        lines.append(line)

    # Create horizontal lines
    for y in y_positions:
        line = visual.Line(
            win, start=(-half_width, y), end=(half_width, y), lineColor=grid_color, opacity=opacity, units="pix"
        )
        lines.append(line)

    return lines


# Now create the grid lines once
grid_lines = create_grid_lines(win)


def get_jitter(base_duration, jitter_range=0.2):
    """
    Calculate a jittered time value by adding random variation to a base time.

    This function introduces controlled randomness to timing, useful for stimulus presentation
    to prevent predictability in experiments.

    Args:
        base_duration (float): The base duration in seconds to which jitter is added.
        jitter_range (float, optional): The range of random variation as a fraction of base_time.

    Returns:
        float: The jittered time value in seconds.
    """
    return base_duration + random.uniform(-jitter_range / 2, jitter_range / 2)


# error_catcher function
def error_catcher(type, value, tb):
    """
    Handle unhandled exceptions by logging the error and displaying a message to the user.

    This function is set as sys.excepthook to catch unhandled exceptions during the experiment.
    It logs the exception details and shows an error message in the experiment window.

    Args:
        type: The type of the exception.
        value: The exception instance.
        tb: The traceback object.
    """
    logging.exception("An unexpected error occurred")
    # Display a message in the window
    error_message = visual.TextStim(
        win, text="An unexpected error occurred. Please inform the researcher.", color="white", height=24, wrapWidth=800
    )
    error_message.draw()
    win.flip()
    event.waitKeys()
    core.quit()


sys.excepthook = error_catcher
logging.info("Starting script...")
logging.info("Defining global variables...")
logging.info("Creating window...")
logging.info("Windowed mode created. Proceeding with the rest of the script...")


event.globalKeys.add(key="escape", func=core.quit)

# Check if the directory exists
if not os.path.exists(image_dir):
    raise FileNotFoundError(f"The image directory does not exist: {image_dir}")

# Get the list of image files
image_files = [f for f in os.listdir(image_dir) if f.endswith(".png")]

# Print the image directory path and number of files found to verify
logging.debug(f"Image directory: {image_dir}")
logging.debug(f"Number of image files found: {len(image_files)}")

# If no image files are found, log a warning
if not image_files:
    logging.warning("No PNG files found in the image directory.")


# Ensure there are enough images for the N-back task
num_images = 24  # Number of images to use in the main task

if len(image_files) < num_images:
    raise ValueError("Not enough images for the N-back task")

# Preload images into a dictionary
# Separate dictionaries for sequential and dual tasks
preloaded_images_sequential = {
    image_file: visual.ImageStim(win, image=os.path.join(image_dir, image_file), size=(350, 350))
    for image_file in image_files
}

preloaded_images_dual = {
    image_file: visual.ImageStim(win, image=os.path.join(image_dir, image_file), size=(100, 100))
    for image_file in image_files
}


EEG_ENABLED = False  # Set True to activate EEG triggering

def send_trigger(trigger_code):
    """Send EEG trigger if configured. Placeholder."""
    if EEG_ENABLED:
        # Insert parallel port code here (e.g., port.setData(trigger_code))
        core.wait(0.005)  # Simulate duration



def get_participant_info(win):
    """
    On‑screen wizard that collects:
        • Participant ID
        • Starting Sequential N‑back level (2 or 3)
        • RNG seed   (leave blank → random each run)
        • Distractor flashes ON / OFF
    Returns a dict with those four keys.
    """
    win.mouseVisible = False
    text24 = dict(height=24, color="white", wrapWidth=900)

    # — 1 Participant ID —
    pid = ""
    while True:
        visual.TextStim(win, text="Enter Participant ID then press return", **text24, pos=(0, 120)).draw()
        box = visual.Rect(win, width=380, height=50, lineColor="white", pos=(0, 40)); box.draw()
        visual.TextStim(win, text=pid, **text24, pos=(0, 40)).draw()
        win.flip()
        keys = event.waitKeys()
        if "return" in keys and pid:
            break
        if "backspace" in keys:
            pid = pid[:-1]
        elif len(keys[0]) == 1:
            pid += keys[0]

    # — 2 Select N‑back level —
    while True:
        prompt = "Select Sequential N‑back level\n\nPress 2 or 3"
        visual.TextStim(win, text=prompt, **text24).draw(); win.flip()
        key = event.waitKeys(keyList=["2", "3"])[0]
        n_level = int(key); break

    # — 3 Seed entry (optional) —
    seed_txt = ""
    while True:
        msg = "Optional: enter RNG seed (blank = random) then press return"
        visual.TextStim(win, text=msg, **text24, pos=(0, 120)).draw()
        box = visual.Rect(win, width=380, height=50, lineColor="white", pos=(0, 40)); box.draw()
        visual.TextStim(win, text=seed_txt, **text24, pos=(0, 40)).draw()
        win.flip()
        keys = event.waitKeys()
        if "return" in keys:
            seed_val = int(seed_txt) if seed_txt.isdigit() else None
            break
        if "backspace" in keys:
            seed_txt = seed_txt[:-1]
        elif keys[0].isdigit():
            seed_txt += keys[0]

    # — 4 Distractor toggle —
    while True:
        prompt = "Enable 200 ms distractor flashes?\n\nPress Y for ON   |   N for OFF"
        visual.TextStim(win, text=prompt, **text24).draw(); win.flip()
        key = event.waitKeys(keyList=["y", "n"])[0]
        distractors = (key == "y"); break

    win.flip()
    return {
        "Participant ID":   pid,
        "N-back Level":     n_level,
        "Seed":             seed_val,
        "Distractors":      distractors,
    }



def save_results_to_csv(filename, results, subjective_measures=None, mode="w"):
    """
    Write behavioural results and optional subjective measures to a CSV.

    Args:
        filename (str):  Base name of the CSV file (e.g. 'participant_01_results.csv').
        results (list of dict):
            Each dict must have keys:
              – 'Participant ID', 'Task', 'Block', 'Results' (nested dict of metrics).
        subjective_measures (dict, optional):
            Mapping of time‑point labels to four scores
            [Mental Fatigue, Task Effort, Mind Wandering, Overwhelmed].
        mode (str): File mode, either 'w' (write new file) or 'a' (append).

    Returns:
        str | None: Full path to the saved CSV, or None on failure.
    """

    logging.info(f"Starting to save results to {filename}")
    data_dir = os.path.join(base_dir, "data")
    os.makedirs(data_dir, exist_ok=True)

    full_path = os.path.join(data_dir, filename)
    logging.info(f"Saving results to: {full_path}")

    try:
        with open(full_path, mode=mode, newline="") as file:
            writer = csv.writer(file)

            # ─────────────────────────────────────────────────────────
            #   first‑time header rows  (only if we are *creating* file)
            # ─────────────────────────────────────────────────────────
            if mode == "w":
                # provenance row: record the seed or the fact it was random
                writer.writerow(["Seed Used", GLOBAL_SEED if GLOBAL_SEED is not None else "random"])
                # standard behavioural header row
                writer.writerow(
                    ["Participant ID", "Task", "Block", "N-back Level", "Measure", "Value"]
                )
                logging.debug("Headers + seed row written")

            # ─────────────────────────────────────────────────────────
            #   behavioural results blocks
            # ─────────────────────────────────────────────────────────
            for i, result in enumerate(results):
                logging.debug(f"Processing result {i + 1}")
                try:
                    participant_id = result.get("Participant ID", "Unknown")
                    task           = result.get("Task",        "Unknown Task")
                    block          = result.get("Block",       "Unknown Block")
                    n_back_level   = result.get("N-back Level", "Unknown")
                    data           = result.get("Results")

                    if isinstance(data, dict):
                        # overall metrics
                        for measure in [
                            "Correct Responses", "Incorrect Responses", "Lapses",
                            "Accuracy", "Total Reaction Time",
                            "Average Reaction Time", "Overall D-Prime",
                        ]:
                            writer.writerow([participant_id, task, block, n_back_level,
                                             measure, data.get(measure, "N/A")])

                        # pre‑ & post‑distractor metrics
                        for section in [("Pre",  ["Accuracy", "Avg RT", "A-Prime"]),
                                        ("Post", ["Accuracy", "Avg RT", "A-Prime"])]:
                            prefix, keys = section
                            for k in keys:
                                col_name = f"{prefix}-Distractor {k}"
                                writer.writerow([participant_id, task, block, n_back_level,
                                                 col_name, data.get(col_name, "N/A")])
                    else:
                        logging.warning(f"Result {i + 1} has unexpected format: {data}")

                except Exception as e:
                    logging.error(f"Error processing result {i + 1}: {e}")
                    logging.debug(f"Faulty result data: {result}")
                    continue  # skip to next result

            # ─────────────────────────────────────────────────────────
            #   subjective measures block (optional)
            # ─────────────────────────────────────────────────────────
            if subjective_measures:
                logging.info("Writing subjective measures")
                writer.writerow([])  # blank line separator
                writer.writerow(["Participant ID", "Time Point", "Measure", "Value"])

                for time_point, measures in subjective_measures.items():
                    try:
                        writer.writerow([participant_id, time_point, "Mental Fatigue", measures[0]])
                        writer.writerow([participant_id, time_point, "Task Effort",     measures[1]])
                        writer.writerow([participant_id, time_point, "Mind Wandering", measures[2]])
                        writer.writerow([participant_id, time_point, "Overwhelmed",    measures[3]])
                    except Exception as e:
                        logging.error(f"Error saving subjective measures for {time_point}: {e}")
                        continue

        logging.info(f"Results and subjective measures saved to {full_path}")
        return full_path

    except Exception as e:
        logging.error(f"Failed to save results to {full_path}: {e}")
        # fail‑safe: display error to participant if the window exists
        try:
            error_stim = visual.TextStim(
                win,
                text="An error occurred while saving data. Please inform the researcher.",
                color="white",
                height=24,
                wrapWidth=800,
            )
            error_stim.draw()
            win.flip()
            event.waitKeys()
        except Exception as inner_e:
            logging.error(f"Error displaying save‑failure message: {inner_e}")

        return None


def save_sequential_results(participant_id, n_back_level, block_name, seq_results):
    """
    Save the results from a Sequential N-back block to a CSV file.

    Constructs a filename using participant ID, N-back level, and block name.
    Wraps the results into a structured list and calls `save_results_to_csv` for output.

    Args:
        participant_id (str): Unique identifier for the participant.
        n_back_level (int): The N-back difficulty level used in the block.
        block_name (str): Label for the block (e.g., 'First_Block').
        seq_results (dict): Dictionary containing detailed block-level performance data.

    Logs:
        - Info log on successful save including file path.
        - Error log if saving fails.

    Returns:
        None
    """
    results_filename = f"participant_{participant_id}_n{n_back_level}_{block_name}_results.csv"
    all_results = [
        {
            "Participant ID": participant_id,
            "Task": f"Sequential {n_back_level}-back",
            "Block": block_name,
            "Results": seq_results,
        },
    ]
    saved_file_path = save_results_to_csv(results_filename, all_results)
    if saved_file_path:
        logging.info(f"Results saved to {saved_file_path}")
    else:
        logging.error(f"Failed to save results after Sequential N-back {block_name}")


def show_overall_welcome_screen(win):
    """
    Display the overall experiment welcome screen (∼90 min warning), advance on space.

    Args:
        win (visual.Window): PsychoPy window.
    """
    welcome_text = (
        "Welcome to this Cognitive Study\n\n"
        "In this experiment, you will complete a series of cognitive tasks involving working memory and attention.\n\n"
        "You will perform different variations of these tasks, with several short breaks spaced out inbetween.\n\n"
        "These tasks are designed to be difficult.\n\n"
        "The entire session will last approximately 90 minutes.\n\n"
        "Please try to stay focused and do your very best throughout the entire experiment.\n\n"
        "\n\n"
        "Press 'space' to begin."
    )

    welcome_message = visual.TextStim(win, text=welcome_text, color="white", height=24, wrapWidth=800)
    welcome_message.draw()
    win.flip()
    event.waitKeys(keyList=["space"])


def show_welcome_screen(win, task_name, n_back_level=None):
    """
    Show task-specific instructions with auto-advance timer.

    Args:
        win (visual.Window): PsychoPy window.
        task_name (str): One of "Sequential N-back", "Spatial N-back", "Dual N-back".
        n_back_level (int, optional): N-back distance for description (only seq task uses it).

    """
    if task_name == "Sequential N-back":
        welcome_text = (
            f"Sequential N-back Task\n\n"
            f"Decide if the current image is the same as the image from {n_back_level} steps back.\n"
            "Press 'Z' for match, 'M' for no match.\n"
            "Ignore the background grid and distractors."
        )
    elif task_name == "Spatial N-back":
        welcome_text = (
            "Spatial N-back Task\n\n"
            "Decide if the highlighted position matches the one from N steps back.\n"
            "Press 'Z' for match, 'M' for no match."
        )
    elif task_name == "Dual N-back":
        welcome_text = (
            "Dual N-back Task\n\n"
            "Decide if both the image and the position match those from N steps back.\n"
            "Press 'Z' for match, 'M' for no match."
        )
    else:
        welcome_text = "Task Instructions\nPress 'space' to begin."

    # Append a concise auto-advance prompt
    welcome_text += "\n\nThis screen will advance in 20 seconds.\nPress 'space' to start now."

    welcome_message = visual.TextStim(win, text=welcome_text, color="white", height=24, wrapWidth=800)
    welcome_message.draw()
    win.flip()

    timer = core.CountdownTimer(20)
    while timer.getTime() > 0:
        keys = event.getKeys(keyList=["space", "escape"])
        if "space" in keys:
            break
        elif "escape" in keys:
            core.quit()

        time_left = int(timer.getTime())
        timer_text = f"Time remaining: {time_left} seconds"
        timer_stim = visual.TextStim(win, text=timer_text, color="white", height=18, pos=(0, -300))
        welcome_message.draw()
        timer_stim.draw()
        win.flip()
    event.clearEvents()


def show_break_screen(win, duration):
    """
    Display a timed rest screen between blocks.

    Args:
        win (visual.Window): PsychoPy window.
        duration (int): Break length in seconds.

    """
    break_text = (
        f"Take a {duration}-second break\n\n"
        "Feel free to move around in your seat\n\n"
        "The experiment will continue automatically"
    )
    break_stim = visual.TextStim(win, text=break_text, color="white", height=24, wrapWidth=800)

    timer = core.CountdownTimer(duration)
    while timer.getTime() > 0:
        break_stim.text = f"{break_text}\n\nTime remaining: {int(timer.getTime())} seconds"
        break_stim.draw()
        win.flip()
        if event.getKeys(["escape"]):
            core.quit()

    event.clearEvents()


def collect_subjective_measures(win):
    """
    Present four Likert questions (1–8) on fatigue, effort, mind-wandering, overwhelmed.

    Args:
        win (visual.Window): PsychoPy window.

    Returns:
        list of int:
            Four responses in order: [Mental Fatigue, Task Effort, Mind Wandering, Overwhelmed].
    """
    questions = [
        "How mentally fatigued do you feel right now?",
        "How effortful do you find the task at this moment?",
        "Do you currently find your mind wandering or becoming distracted?",
        "How overwhelmed do you feel by the task demands right now?",
    ]
    responses = []

    for question in questions:
        instruction_text = f"{question}\n\nPress a key from 1 (Not at all) to 8 (Extremely)"
        instruction_stim = visual.TextStim(win, text=instruction_text, height=24, wrapWidth=800)

        response = None
        while response is None:
            instruction_stim.draw()
            win.flip()
            keys = event.getKeys(keyList=["1", "2", "3", "4", "5", "6", "7", "8", "escape"])
            if keys:
                if "escape" in keys:
                    core.quit()
                response = int(keys[0])
        responses.append(response)

    return responses


def get_progressive_timings(task_name, block_number):
    """
    Stimuli presentation and ISI times that shrink gradually across blocks.

    Args:
        task_name (str): "Spatial N-back" or "Dual N-back" (otherwise defaults to no change).
        block_number (int): Zero-based block index for cumulative reductions.

    Returns:
        tuple (float, float):
            (presentation_time_s, isi_time_s) for this block.
    """
    if task_name == "Spatial N-back":
        base_presentation = 1.0  # Base presentation time in seconds
        base_isi = 1.0  # Base ISI in seconds
        presentation_reduction_per_block = 0.03  # Reduction per block in seconds
        isi_reduction_per_block = 0.05  # Reduction per block in seconds
        max_presentation_reduction = 0.15  # Maximum total reduction in seconds
        max_isi_reduction = 0.225  # Maximum total reduction in seconds
    elif task_name == "Dual N-back":
        base_presentation = 1.0  # Base presentation time in seconds
        base_isi = 1.2  # Base ISI in seconds
        presentation_reduction_per_block = 0.03  # Reduction per block in seconds
        isi_reduction_per_block = 0.05  # Reduction per block in seconds
        max_presentation_reduction = 0.15  # Maximum total reduction in seconds
        max_isi_reduction = 0.15  # Maximum total reduction in seconds
    else:
        base_presentation = 1.0
        base_isi = 1.0
        presentation_reduction_per_block = 0.0
        isi_reduction_per_block = 0.0
        max_presentation_reduction = 0.0
        max_isi_reduction = 0.0

    presentation_reduction = min(block_number * presentation_reduction_per_block, max_presentation_reduction)
    isi_reduction = min(block_number * isi_reduction_per_block, max_isi_reduction)

    presentation_time = base_presentation - presentation_reduction
    isi = base_isi - isi_reduction

    return presentation_time, isi


def calculate_A_prime(trials):
    """
    Calculate the A-prime sensitivity index from trial data.

    A-prime is a non-parametric measure of sensitivity, similar to d-prime, but does not assume
    equal variance in signal and noise distributions. It adjusts for extreme hit and false alarm rates.

    Args:
        trials: A list of trial dictionaries containing 'Is Target' and 'Response' keys.

    Returns:
        The A-prime value as a float, or None if it cannot be computed.
    """
    hits = sum(1 for trial in trials if trial["Is Target"] and trial["Response"] == "match")
    false_alarms = sum(1 for trial in trials if not trial["Is Target"] and trial["Response"] == "match")
    misses = sum(1 for trial in trials if trial["Is Target"] and trial["Response"] != "match")
    correct_rejections = sum(1 for trial in trials if not trial["Is Target"] and trial["Response"] != "match")

    total_targets = hits + misses
    total_nontargets = false_alarms + correct_rejections

    if total_targets == 0 or total_nontargets == 0:
        return None  # Cannot compute A'

    hit_rate = hits / total_targets
    false_alarm_rate = false_alarms / total_nontargets

    # Adjust hit_rate and false_alarm_rate to avoid extreme values
    hit_rate = min(max(hit_rate, 0.0001), 0.9999)
    false_alarm_rate = min(max(false_alarm_rate, 0.0001), 0.9999)

    if hit_rate >= false_alarm_rate:
        A_prime = 0.5 + ((hit_rate - false_alarm_rate) * (1 + hit_rate - false_alarm_rate)) / (
            4 * hit_rate * (1 - false_alarm_rate)
        )
    else:
        A_prime = 0.5 - ((false_alarm_rate - hit_rate) * (1 + false_alarm_rate - hit_rate)) / (
            4 * false_alarm_rate * (1 - hit_rate)
        )

    return A_prime


def calculate_accuracy_and_rt(trials):
    """
    Calculate accuracy and reaction time metrics from trial data.

    Computes the percentage of correct responses and the total and average reaction times
    based on trial data.

    Args:
        trials: A list of trial dictionaries containing 'Accuracy' and 'Reaction Time' keys.

    Returns:
        A tuple of (accuracy, total_rt, avg_rt) where:
        - accuracy: Percentage of correct responses (float).
        - total_rt: Sum of reaction times (float).
        - avg_rt: Average reaction time (float).
    """
    total_trials = len(trials)
    correct = sum(1 for trial in trials if trial["Accuracy"])
    accuracy = (correct / total_trials) * 100 if total_trials > 0 else 0.0
    reaction_times = [trial["Reaction Time"] for trial in trials if trial["Reaction Time"] is not None]
    total_rt = sum(reaction_times)
    avg_rt = total_rt / len(reaction_times) if reaction_times else 0.0
    return accuracy, total_rt, avg_rt


def calculate_dprime(detailed_data):
    """
    Calculate the d-prime sensitivity index from detailed trial data.

    D-prime measures the ability to distinguish targets from non-targets in signal detection theory.

    Args:
        detailed_data: A list of trial dictionaries containing 'Is Target' and 'Response' keys.

    Returns:
        The d-prime value as a float.
    """
    if not detailed_data or all(trial["Response"] == "lapse" for trial in detailed_data):
        return 0.0

    hits = sum(1 for trial in detailed_data if trial["Is Target"] and trial["Response"] == "match")
    false_alarms = sum(1 for trial in detailed_data if not trial["Is Target"] and trial["Response"] == "match")
    misses = sum(1 for trial in detailed_data if trial["Is Target"] and trial["Response"] != "match")
    correct_rejections = sum(1 for trial in detailed_data if not trial["Is Target"] and trial["Response"] != "match")

    total_targets = hits + misses
    total_non_targets = false_alarms + correct_rejections

    # Adjust hits and false alarms to avoid extreme values
    hit_rate = hits / total_targets if total_targets > 0 else 0
    fa_rate = false_alarms / total_non_targets if total_non_targets > 0 else 0

    # Apply the log-linear correction to avoid infinite z-scores
    adjusted_hit_rate = (hits + 0.5) / (total_targets + 1)
    adjusted_fa_rate = (false_alarms + 0.5) / (total_non_targets + 1)

    from scipy.stats import norm

    try:
        d_prime = norm.ppf(adjusted_hit_rate) - norm.ppf(adjusted_fa_rate)
    except ValueError:
        d_prime = 0.0

    return d_prime


def show_summary(win, task_name, *results):
    """
    After a block finishes, display overall correct/incorrect/lapse counts, accuracy, RTs, d′.

    Args:
        win (visual.Window): PsychoPy window.
        task_name (str): Name of the task for the header.
        *results: Tuple of
            (correct_responses, incorrect_responses, lapses,
             total_reaction_time, reaction_times_list, detailed_data, accuracy).

    Side effect:
        Renders a 10 s summary screen or advances on space.
    """
    correct_responses, incorrect_responses, lapses, total_reaction_time, reaction_times, detailed_data, accuracy = (
        results
    )
    total_responses = correct_responses + incorrect_responses + lapses
    avg_reaction_time = total_reaction_time / len(reaction_times) if reaction_times else 0
    d_prime = calculate_dprime(detailed_data)

    summary_text = (
        f"{task_name} Task Completed!\n\n"
        f"Correct Responses: {correct_responses}\n"
        f"Incorrect Responses: {incorrect_responses}\n"
        f"Lapses: {lapses}\n"
        f"Overall Accuracy: {accuracy:.2f}%\n"
        f"Average Reaction Time: {avg_reaction_time:.2f} s\n"
        f"Total Response Time: {total_reaction_time:.2f} s\n"
        f"D-Prime: {d_prime:.2f}\n\n"
        f"This screen will automatically advance in 10 seconds.\nPress 'space' to continue immediately."
    )

    summary_message = visual.TextStim(win, text=summary_text, color="white", height=24, wrapWidth=800)
    summary_message.draw()
    win.flip()

    timer = core.Clock()
    while timer.getTime() < 10:
        keys = event.getKeys(keyList=["space", "escape"])
        if "space" in keys:
            break
        elif "escape" in keys:
            core.quit()
    event.clearEvents()


def generate_image_sequence_with_matches(num_trials, n, target_percentage=0.5, skip_responses=1):
    """
    Build an image sequence for an N-back task, inserting true targets and (for 3-back) misleading trials.

    Args:
        num_trials (int):
            Total number of trials to generate, including the initial skip_responses.
        n (int):
            N-back distance (e.g. 2 for 2-back, 3 for 3-back).
        target_percentage (float):
            Proportion of eligible trials (i.e. after the first n) that should be true N-back matches.
            Defaults to 0.5 (50% targets).
        skip_responses (int):
            Number of initial trials during which no response is required (these still count towards sequence length).

    Behaviour:
        - Selects positions for true N-back matches (“yes” trials) and limits consecutive matches to 2.
        - If n == 3, additionally inserts misleading trials on 30% of the non-target positions,
          where the stimulus matches the item from (n–1) steps back rather than n.
        - Fills all other trials with randomly chosen images that avoid creating unintended n- or (for 3-back) 2-back repeats.
        - Re-shuffles image pool when exhausted.

    Returns:
        tuple:
            sequence (list of str):
                Ordered list of image filenames for each trial.
            yes_positions (list of int):
                Indices where true N-back matches occur.
    """
    # Start with a fresh copy of the image list and shuffle it
    available_images = image_files.copy()
    random.shuffle(available_images)

    sequence = []
    max_consecutive_matches = 2  # Limit consecutive matches
    consecutive_count = 0
    target_num_yes = int((num_trials - n) * target_percentage)
    yes_positions = random.sample(range(n, num_trials), target_num_yes)

    # Add misleading patterns (for 3-back)
    if n == 3:
        misleading_positions = random.sample(
            [p for p in range(n, num_trials) if p not in yes_positions],
            int(target_num_yes * 0.3),  # 30% misleading trials
        )
    else:
        misleading_positions = []

    for i in range(num_trials):
        if i in yes_positions and consecutive_count < max_consecutive_matches:
            # This is a target trial: replicate the image from n steps back
            sequence.append(sequence[i - n])
            consecutive_count += 1
        elif n == 3 and i in misleading_positions:
            # Misleading trial for 3-back: use the image from 2 steps back
            sequence.append(sequence[i - 2])
            consecutive_count = 0
        else:
            # Non-target trial
            if not available_images:
                # If we've exhausted available_images, reset and shuffle again
                available_images = image_files.copy()
                random.shuffle(available_images)

            # Find images that do not create unwanted n-back or 2-back matches
            non_matching_images = [
                img
                for img in available_images
                if img not in sequence[-n:] and (len(sequence) < 2 or img != sequence[-2])
            ]

            if not non_matching_images:
                # If no suitable non-matching images, fallback to whatever is available
                non_matching_images = available_images

            chosen_image = random.choice(non_matching_images)
            sequence.append(chosen_image)
            available_images.remove(chosen_image)
            consecutive_count = 0

    return sequence, yes_positions


def draw_grid():
    """
    Draw all predefined grid lines on the PsychoPy window.
    Assumes global variable 'grid_lines' has already been populated.
    """
    for line in grid_lines:
        line.draw()


def display_image(win, image_file, level_indicator, feedback_text=None, task="sequential"):
    """
    Draw grid, level text, then a central image (with optional feedback) and flip.

    Args:
        win (visual.Window): PsychoPy window.
        image_file (str): Key into preloaded_images dict.
        level_indicator (visual.TextStim): The “Level: N-back” text stim.
        feedback_text (str, optional): Feedback string to show above image.
        task (str): 'sequential' or 'dual' to pick image size dictionary.

    """
    # Select the correct preloaded images based on the task
    if task == "sequential":
        image_stim = preloaded_images_sequential[image_file]
    elif task == "dual":
        image_stim = preloaded_images_dual[image_file]
    else:
        raise ValueError("Invalid task type. Choose 'sequential' or 'dual'.")

    # Ensure consistent size and position
    image_stim.size = (350, 350) if task == "sequential" else (100, 100)  # Default sizes for each task
    image_stim.pos = (0, 0)  # Always center for sequential

    # Draw the grid and level indicator first
    draw_grid()
    level_indicator.draw()

    # Draw the main image
    image_stim.draw()

    # Optionally, draw feedback text
    if feedback_text:
        feedback_message = visual.TextStim(
            win, text=feedback_text, color="orange", height=24, pos=(0, image_stim.size[1] / 2 + 50), units="pix"
        )
        feedback_message.draw()

    # Flip the display
    win.flip()


def calculate_sequential_nback_summary(results_dict, n_level):
    """
    Compute summary metrics from one Sequential N-back block’s results dictionary.

    Args:
        results_dict (dict): Dictionary returned by run_sequential_nback_block.
        n_level (int): N-back difficulty used.

    Returns:
        dict: Summary with keys 'N-back Level', 'Total Correct Responses', 'Total Incorrect Responses',
              'Total Lapses', 'Overall Accuracy (%)', 'Average Reaction Time (s)', 'Total Trials', 'D-Prime'.
    """
    correct_responses = results_dict["Correct Responses"]
    incorrect_responses = results_dict["Incorrect Responses"]
    lapses = results_dict["Lapses"]
    total_trials = correct_responses + incorrect_responses + lapses
    accuracy = results_dict["Accuracy"]
    avg_reaction_time = results_dict["Average Reaction Time"]
    d_prime = results_dict["Overall D-Prime"]

    return {
        "N-back Level": n_level,
        "Total Correct Responses": correct_responses,
        "Total Incorrect Responses": incorrect_responses,
        "Total Lapses": lapses,
        "Overall Accuracy (%)": accuracy,
        "Average Reaction Time (s)": avg_reaction_time,
        "Total Trials": total_trials,
        "D-Prime": d_prime,
    }


def run_sequential_nback_block(
    win,
    n,
    num_images,
    target_percentage=0.5,
    display_duration=0.8,
    isi=1.0,
    provide_feedback=False,
    num_trials=None,
    is_first_encounter=True,
    block_number=1,
):
    """
    Run one block of the Sequential N-back task, collecting responses and timing.

    Args:
        win (visual.Window): PsychoPy window.
        n (int): N-back distance.
        num_images (int): Number of distinct images available.
        target_percentage (float): Proportion of non-skip trials that are targets.
        display_duration (float): Stimulus on-screen time in seconds.
        isi (float): Base inter-stimulus interval in seconds.
        provide_feedback (bool): Whether to show trial-by-trial feedback.
        num_trials (int, optional): Override total trials (otherwise uses sequence length).
        is_first_encounter (bool): If True, show “no response” notice for first n trials.
        block_number (int): Zero-based index used for logging and progressive timing.

    Returns:
        dict: Block summary with keys 'Block Number', 'Correct Responses', 'Incorrect Responses',
              'Lapses', 'Accuracy', 'Total Reaction Time', 'Average Reaction Time',
              'Reaction Times', 'Detailed Data', 'Pre-Distractor Accuracy', 'Pre-Distractor Avg RT',
              'Pre-Distractor A-Prime', 'Post-Distractor Accuracy', 'Post-Distractor Avg RT',
              'Post-Distractor A-Prime', 'Overall D-Prime'.
    """

    # Number of initial trials without required responses
    skip_responses = n

    # Generate the image sequence and target positions
    num_images_to_generate = max(num_images, num_trials) if num_trials is not None else num_images
    images, yes_positions = generate_image_sequence_with_matches(
        num_images_to_generate, n, target_percentage, skip_responses=skip_responses
    )
    total_trials = num_trials if num_trials is not None else len(images)

    # Initialize tracking variables
    nback_queue = []
    detailed_data = []
    correct_responses = 0
    incorrect_responses = 0
    lapses = 0
    total_reaction_time = 0
    reaction_times = []
    last_lapse = False

    # Prepare fixation and level indicator
    fixation_cross = visual.TextStim(win, text="+", color="white", height=32, units="pix", pos=(0, 0))
    margin_x, margin_y = 350, 150
    level_indicator = visual.TextStim(
        win,
        text=f"Level: {n}-back",
        color="white",
        height=32,
        pos=(-win.size[0] // 2 + margin_x, win.size[1] // 2 - margin_y),
        units="pix",
        alignText="left",
    )

    # ─────────────────────────────────────────────────────────────
    #  Determine where distractors will occur  ─ hard‑cap = 13
    #      • never during the initial non‑response trials
    #      • leave 3 scored trials before the first flash
    #      • leave 3 scored trials after the last flash
    #      • ≥ 6 trials between successive flashes
    # ─────────────────────────────────────────────────────────────
    DISTRACTORS_PER_BLOCK = 13  # hard cap
    MIN_GAP_BETWEEN = 6  # trials
    # skip_responses = n (defined above).  +3 scored trials before first flash
    FIRST_SCORABLE_TRIAL = skip_responses + 1
    EARLIEST_DISTRACTOR = FIRST_SCORABLE_TRIAL + 3
    LATEST_DISTRACTOR = total_trials - 3  # keep 3 at the end flash‑free

    if (
            DISTRACTORS_ENABLED
            and LATEST_DISTRACTOR - EARLIEST_DISTRACTOR + 1 >= 1
    ):
        # build a shuffled pool of candidate trials
        candidate_trials = list(range(EARLIEST_DISTRACTOR, LATEST_DISTRACTOR + 1))
        random.shuffle(candidate_trials)

        distractor_trials = []
        for t in candidate_trials:
            # honour minimum gap constraint
            if all(abs(t - prev) >= MIN_GAP_BETWEEN for prev in distractor_trials):
                distractor_trials.append(t)
                if len(distractor_trials) == DISTRACTORS_PER_BLOCK:
                    break

        distractor_trials.sort()
        if len(distractor_trials) < DISTRACTORS_PER_BLOCK:
            logging.warning(
                f"Block {block_number}: could only place "
                f"{len(distractor_trials)} / {DISTRACTORS_PER_BLOCK} distractors "
                f"with current constraints."
            )
        logging.info(f"Block {block_number}: Distractor positions → {distractor_trials}")
    else:
        distractor_trials = []
        logging.info(f"Block {block_number}: Distractors disabled")

    # ─────────────────────────────────────────────────────────────
    #  First‑block notice (for the initial n non‑response trials)
    # ─────────────────────────────────────────────────────────────
    if is_first_encounter:
        msg = f"No response required for the first {n} trials"
        feedback_text = visual.TextStim(win, text=msg, color="white", height=24, units="pix")
        draw_grid()
        level_indicator.draw()
        feedback_text.draw()
        win.flip()
        core.wait(2)

    # --- Trial Loop ---
    for i in range(total_trials):
        img = images[i]
        feedback_text = None
        if last_lapse and i >= skip_responses:
            feedback_text = "Previous lapse, please respond"
            last_lapse = False

        # Show stimulus
        display_image(win, img, level_indicator, feedback_text=feedback_text)
        send_trigger(1)

        # Collect response during stimulus
        response_timer = core.Clock()
        response = None
        while response_timer.getTime() < display_duration:
            keys = event.getKeys(keyList=["z", "m", "escape"])
            if "escape" in keys:
                core.quit()
            if keys and response is None and i >= skip_responses:
                rt = response_timer.getTime()
                is_target = len(nback_queue) >= n and img == nback_queue[-n]
                response = "match" if "z" in keys else "non-match"
                correct_responses += int((response == "match") == is_target)
                incorrect_responses += int((response == "match") != is_target)
                total_reaction_time += rt
                reaction_times.append(rt)
                detailed_data.append(
                    {
                        "Trial": i + 1,
                        "Image": img,
                        "Is Target": is_target,
                        "Response": response,
                        "Reaction Time": rt,
                        "Accuracy": (response == "match") == is_target,
                    }
                )

        # ISI + possible distractor
        draw_grid()
        fixation_cross.draw()
        level_indicator.draw()
        win.flip()
        isi_timer = core.Clock()
        jittered = get_jitter(isi)
        distractor_displayed = False
        while isi_timer.getTime() < jittered:
            if (i + 1) in distractor_trials and not distractor_displayed and isi_timer.getTime() >= jittered / 2 - 0.1:
                draw_grid()
                fixation_cross.draw()
                level_indicator.draw()
                sq = visual.Rect(win, width=100, height=100, fillColor="white", units="pix")
                sq.draw()
                win.flip()
                core.wait(0.2)
                draw_grid()
                fixation_cross.draw()
                level_indicator.draw()
                win.flip()
                distractor_displayed = True
                logging.info(f"Distractor @ trial {i+1}")
            keys = event.getKeys(keyList=["z", "m", "escape"])
            if "escape" in keys:
                core.quit()
            if keys and response is None and i >= skip_responses:
                rt = display_duration + isi_timer.getTime()
                is_target = len(nback_queue) >= n and img == nback_queue[-n]
                response = "match" if "z" in keys else "non-match"
                correct_responses += int((response == "match") == is_target)
                incorrect_responses += int((response == "match") != is_target)
                total_reaction_time += rt
                reaction_times.append(rt)
                detailed_data.append(
                    {
                        "Trial": i + 1,
                        "Image": img,
                        "Is Target": is_target,
                        "Response": response,
                        "Reaction Time": rt,
                        "Accuracy": (response == "match") == is_target,
                    }
                )

        # Handle lapse
        if response is None and i >= skip_responses:
            lapses += 1
            last_lapse = True
            is_target = len(nback_queue) >= n and img == nback_queue[-n]
            detailed_data.append(
                {
                    "Trial": i + 1,
                    "Image": img,
                    "Is Target": is_target,
                    "Response": "lapse",
                    "Reaction Time": None,
                    "Accuracy": False,
                }
            )

        # Update queue & clear events
        nback_queue.append(img)
        if len(nback_queue) > n:
            nback_queue.pop(0)
        event.clearEvents()

    # Compute summary stats
    total_responded = correct_responses + incorrect_responses + lapses
    accuracy = (correct_responses / total_responded) * 100 if total_responded else 0.0

    # --- Compute Pre- and Post-Distractor Metrics ---
    # Pre = 3 trials before each distractor; Post = 3 trials after
    pre_indices = set()
    post_indices = set()
    for d in distractor_trials:
        for j in range(d - 3, d):
            if 1 <= j <= total_trials:
                pre_indices.add(j)
        for j in range(d + 1, d + 4):
            if 1 <= j <= total_trials:
                post_indices.add(j)

    pre_data = [t for t in detailed_data if t["Trial"] in pre_indices]
    post_data = [t for t in detailed_data if t["Trial"] in post_indices]

    def _compute_metrics(trials):
        if not trials:
            return None, None, None
        # accuracy
        acc = sum(1 for t in trials if t["Accuracy"]) / len(trials) * 100
        # avg RT
        rts = [t["Reaction Time"] for t in trials if t["Reaction Time"] is not None]
        avg_rt = sum(rts) / len(rts) if rts else 0.0
        # A-prime
        ap = calculate_A_prime(trials)
        return acc, avg_rt, ap

    pre_acc, pre_rt, pre_ap = _compute_metrics(pre_data)
    post_acc, post_rt, post_ap = _compute_metrics(post_data)

    # Build and return the summary dict
    return {
        "Block Number": block_number,
        "Correct Responses": correct_responses,
        "Incorrect Responses": incorrect_responses,
        "Lapses": lapses,
        "Accuracy": accuracy,
        "Total Reaction Time": total_reaction_time,
        "Average Reaction Time": (total_reaction_time / len(reaction_times)) if reaction_times else 0.0,
        "Reaction Times": reaction_times,
        "Detailed Data": detailed_data,
        "Pre-Distractor Accuracy": pre_acc if pre_acc is not None else "N/A",
        "Pre-Distractor Avg RT": pre_rt if pre_rt is not None else "N/A",
        "Pre-Distractor A-Prime": pre_ap if pre_ap is not None else "N/A",
        "Post-Distractor Accuracy": post_acc if post_acc is not None else "N/A",
        "Post-Distractor Avg RT": post_rt if post_rt is not None else "N/A",
        "Post-Distractor A-Prime": post_ap if post_ap is not None else "N/A",
        "Overall D-Prime": calculate_dprime(detailed_data),
    }


def show_transition_screen(win, next_task_name):
    """
    Inform participant of upcoming task, advance on space or after 5 s

    Args:
        win (visual.Window): PsychoPy window.
        next_task_name (str): Name of the next task.
    """
    transition_text = f"Transitioning to the {next_task_name} Task.\n\nPress 'space' to continue immediately or wait 5 seconds to proceed."
    transition_message = visual.TextStim(win, text=transition_text, color="white", height=24, wrapWidth=750)
    transition_message.draw()
    win.flip()

    timer = core.Clock()
    while timer.getTime() < 5:
        keys = event.getKeys(keyList=["space", "escape"])
        if "space" in keys:
            break
        elif "escape" in keys:
            core.quit()
    event.clearEvents()


def show_level_change_screen(win, task_name, old_level, new_level, is_first_block=False):
    """
    Display a screen informing participants of a change in N-back difficulty level.

    Args:
        win (visual.Window): PsychoPy window.
        task_name (str): Name of the task (Sequential, Spatial, or Dual).
        old_level (int): Previous N-back level.
        new_level (int): Updated N-back level.
        is_first_block (bool, optional): Whether this is the first block of the task.
    """
    # determine phrasing of the level change
    if new_level > old_level:
        change_text = f"increasing from {old_level}-back to {new_level}-back"
    elif new_level < old_level:
        change_text = f"decreasing from {old_level}-back to {new_level}-back"
    else:
        change_text = f"continuing at {old_level}-back"

    # first‐trial notice
    feedback_text = f"No response required for the first {new_level} trials"

    # status indicators
    seed_status = (
        f"Seed: fixed ({GLOBAL_SEED})"
        if GLOBAL_SEED is not None
        else "Seed: random"
    )
    dist_status = "Distractors: ON" if DISTRACTORS_ENABLED else "Distractors: OFF"

    # assemble full on‐screen message
    message = (
        f"Based on your performance, the difficulty level is {change_text}.\n\n"
        f"The task will now be at {new_level}-back level.\n\n"
        f"{feedback_text}\n\n"
        f"{seed_status} | {dist_status}\n\n"
        f"After that, respond if the current stimulus matches the {new_level} steps back.\n\n"
        "This screen will automatically advance in 10 seconds.\n"
        "Press 'space' to continue immediately."
    )

    # draw & display
    level_change_stim = visual.TextStim(
        win, text=message, color="white", height=24, wrapWidth=750
    )
    level_change_stim.draw()
    win.flip()

    # wait with early‐exit
    timer = core.Clock()
    while timer.getTime() < 10:
        keys = event.getKeys(keyList=["space", "escape"])
        if "space" in keys:
            break
        elif "escape" in keys:
            core.quit()
    event.clearEvents()



def print_debug_info(sequence, n, is_dual=False):
    """
    Log debug info: where matches occur in an N-back sequence (for image, position, or dual).

    Args:
        sequence (list): Stimulus sequence (images or position-image pairs).
        n (int): N-back distance.
        is_dual (bool, optional): Whether the task is dual N-back.
    """
    if is_dual:
        match_positions = [
            i
            for i in range(n, len(sequence))
            if sequence[i][0] == sequence[i - n][0] and sequence[i][1] == sequence[i - n][1]
        ]
    else:
        match_positions = [i for i in range(n, len(sequence)) if sequence[i] == sequence[i - n]]

    response_positions = [i - (n - 1) for i in match_positions]

    logging.debug(f"Sequence: {[pos[0] if is_dual else pos for pos in sequence]}")
    logging.debug(f"Positive target positions: {response_positions}")


def generate_positions_with_matches(num_positions, n, target_percentage=0.5):
    """Generate a sequence of spatial positions with specified N-back matches.

    Args:
        num_positions (int): Number of positions in the sequence.
        n (int): N-back distance.
        target_percentage (float, optional): Proportion of trials that should be targets.

    Returns:
        list: Generated sequence of position indices.
    """
    positions = list(range(12))
    sequence = [random.choice(positions) for _ in range(num_positions)]

    num_targets = int((num_positions - n) * target_percentage)
    target_indices = random.sample(range(n, num_positions), num_targets)

    for idx in target_indices:
        sequence[idx] = sequence[idx - n]

    print_debug_info(sequence, n)

    return sequence


def get_level_color(n_level):
    """
    Return a color corresponding to the given N-back level.

    Provides visual distinction for different N-back levels during the task.

    Args:
        n_level: The N-back level (integer).

    Returns:
        A string representing the color name.
    """
    if n_level == 1:
        return "white"
    elif n_level == 2:
        return "lightblue"
    elif n_level == 3:
        return "lightgreen"
    else:
        return "white"  # Default color


def display_grid(win, highlight_pos=None, highlight=False, n_level=None, feedback_text=None, lapse_feedback=None):
    """
    Display the radial 12-position grid with optional highlighted position, feedback text, and lapse messages.

    Args:
        win (visual.Window): PsychoPy window.
        highlight_pos (int, optional): Index of position to highlight.
        highlight (bool, optional): Whether to highlight a grid square.
        n_level (int, optional): Current N-back level for colour coding.
        feedback_text (str, optional): Text feedback to display.
        lapse_feedback (str, optional): Lapse feedback text.
    """
    draw_grid()
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


def adjust_nback_level(current_level, accuracy, increase_threshold=82, decrease_threshold=65, max_level=4):
    """Adjust the N-back level based on participant accuracy.

    Args:
        current_level (int): Current N-back level.
        accuracy (float): Participant's accuracy percentage.
        increase_threshold (int): Accuracy threshold to increase difficulty.
        decrease_threshold (int): Accuracy threshold to decrease difficulty.
        max_level (int): Maximum allowed N-back level.

    Returns:
        int: Updated N-back level.
    """
    if accuracy >= increase_threshold and current_level < max_level:
        return current_level + 1
    elif accuracy <= decrease_threshold and current_level > 2:
        return max(2, current_level - 1)  # Ensures level never goes below 2
    else:
        return current_level


def run_spatial_nback_block(win, n, num_trials, display_duration=1.0, isi=1.0, is_first_encounter=True, block_number=0):
    """
    Run one block of the Spatial N-back task on a 12-position radial grid.

    Args:
        win (visual.Window): PsychoPy window.
        n (int): N-back distance.
        num_trials (int): Number of trials to present.
        display_duration (float): On-screen highlight time in seconds.
        isi (float): Base inter-stimulus interval in seconds.
        is_first_encounter (bool): If True, show “no response” for first n trials.
        block_number (int): Zero-based index for logging.

    Returns:
        int: Current N-back level (unchanged, since spatial is non-adaptive here).
    """
    positions = generate_positions_with_matches(num_trials, n)
    logging.info(f"Block {block_number + 1} timings - Presentation: {display_duration * 1000}ms, ISI: {isi * 1000}ms")

    nback_queue = []
    correct_responses = 0
    incorrect_responses = 0
    lapses = 0
    total_reaction_time = 0
    reaction_times = []
    responses = []

    lapse_feedback = None

    if is_first_encounter:
        initial_feedback = f"No response required for the first {n} trials"
        feedback_text = visual.TextStim(win, text=initial_feedback, color=get_level_color(n), height=24, pos=(0, 0))
        feedback_text.draw()
        win.flip()
        feedback_duration = 2 if n == 1 else 4 if n == 2 else 6
        core.wait(feedback_duration)
        win.flip()
        core.wait(0.5)

    for i, pos in enumerate(positions):
        is_target = len(nback_queue) == n and pos == nback_queue[0]

        display_grid(win, highlight_pos=pos, highlight=True, n_level=n, lapse_feedback=lapse_feedback)
        win.flip()
        core.wait(get_jitter(display_duration))

        display_grid(win, highlight_pos=None, highlight=False, n_level=n)
        win.flip()

        response_timer = core.Clock()
        response = None
        jittered_isi = get_jitter(isi)
        while response_timer.getTime() < jittered_isi:
            keys = event.getKeys(keyList=["z", "m", "escape"])
            if "escape" in keys:
                core.quit()

            if keys and response is None and i >= n:
                reaction_time = response_timer.getTime()
                if "z" in keys:
                    response = True
                elif "m" in keys:
                    response = False

                if response == is_target:
                    correct_responses += 1
                else:
                    incorrect_responses += 1

                total_reaction_time += reaction_time
                reaction_times.append(reaction_time)
                responses.append((i + 1, pos, is_target, response, reaction_time))

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

    return n


def generate_dual_nback_sequence(num_trials, grid_size, n, target_rate=0.5):
    """
    Build a combined (position,image) sequence for Dual N-back.

    Args:
        num_trials (int): Total trials.
        grid_size (int): Width/height of spatial grid (#cells per side).
        n (int): N-back distance.
        target_rate (float): Proportion of trials that are true dual-matches.

    Returns:
        tuple of lists:
          - pos_seq (list of (x,y) tuples)
          - image_seq (list of str image filenames)
    """
    positions = [(x, y) for x in range(grid_size) for y in range(grid_size)]
    pos_seq = [random.choice(positions) for _ in range(num_trials)]
    image_seq = [random.choice(image_files) for _ in range(num_trials)]

    num_targets = int((num_trials - n) * target_rate)
    target_indices = random.sample(range(n, num_trials), num_targets)

    for idx in target_indices:
        pos_seq[idx] = pos_seq[idx - n]
        image_seq[idx] = image_seq[idx - n]

    combined_seq = list(zip(pos_seq, image_seq))
    print_debug_info(combined_seq, n, is_dual=False)

    return pos_seq, image_seq


def display_dual_stimulus(win, pos, image_file, grid_size, n_level, feedback_text=None, return_stims=False):
    """
    Draw or return the highlight rect + image stim for Dual N-back trial.

    Args:
        win (visual.Window): PsychoPy window.
        pos ((int,int)): Grid‐cell coordinates.
        image_file (str): Filename key for preloaded_images_dual.
        grid_size (int): Number of cells per row/col.
        n_level (int): N-back level for colour coding.
        feedback_text (str, optional): Optional message above grid.
        return_stims (bool): If True, returns (Rect, ImageStim) instead of drawing.

    Returns:
        If return_stims: (highlight_rect, image_stim), else None.
    """
    # Define grid and cell properties
    grid_length = 600
    cell_length = grid_length / grid_size
    top_left = (-grid_length / 2, grid_length / 2)
    x = top_left[0] + pos[0] * cell_length + cell_length / 2
    y = top_left[1] - pos[1] * cell_length - cell_length / 2

    # Set the highlight rectangle for the position
    level_color = get_level_color(n_level)
    highlight = visual.Rect(
        win, width=cell_length - 2, height=cell_length - 2, pos=(x, y), fillColor=level_color, lineColor=None
    )

    # Use the preloaded image for dual tasks
    image_stim = preloaded_images_dual[image_file]  # Task-specific dictionary
    image_stim.pos = (x, y)
    image_stim.size = (cell_length - 10, cell_length - 10)  # Adjust size for dual-task grid

    # Optionally display feedback text
    if feedback_text:
        feedback_message = visual.TextStim(
            win, text=feedback_text, color=level_color, height=24, pos=(0, grid_length / 2 + 50)
        )

    # Return stimuli objects if requested
    if return_stims:
        return highlight, image_stim
    else:
        # Draw highlight, image, and optional feedback text
        highlight.draw()
        image_stim.draw()
        if feedback_text:
            feedback_message.draw()
        win.flip()


def create_grid(win, grid_size):
    """
    Build a grid of visual.Rect cells plus an outline rectangle.

    Args:
        win (visual.Window): PsychoPy window.
        grid_size (int): Number of rows/columns.

    Returns:
        tuple:
          - grid (list of visual.Rect): Individual cells.
          - outline (visual.Rect): Outer border of the grid.
    """
    grid_length = 600
    cell_length = grid_length / grid_size
    top_left = (-grid_length / 2, grid_length / 2)

    grid = []
    for i in range(grid_size):
        for j in range(grid_size):
            x = top_left[0] + i * cell_length + cell_length / 2
            y = top_left[1] - j * cell_length - cell_length / 2
            rect = visual.Rect(
                win, width=cell_length, height=cell_length, pos=(x, y), lineColor="white", fillColor=None
            )
            grid.append(rect)

    outline = visual.Rect(
        win, width=grid_length, height=grid_length, pos=(0, 0), lineColor="white", fillColor=None, lineWidth=2
    )

    return grid, outline


def run_dual_nback_block(win, n, num_trials, display_duration=1.0, isi=1.2, is_first_encounter=True, block_number=0):
    """
    Run one block of the Dual N-back task on a 3×3 grid with images.

    Args:
        win (visual.Window): PsychoPy window.
        n (int): N-back distance.
        num_trials (int): Number of trials.
        display_duration (float): Stimulus display time in seconds.
        isi (float): Base inter-stimulus interval in seconds.
        is_first_encounter (bool): Whether to show initial “no response” message.
        block_number (int): Zero-based index for logging.

    Returns:
        int: Updated N-back level (may increase or decrease based on accuracy).
    """

    # Add this line here
    logging.info(
        f"Dual N-back Block {block_number + 1} timings - Presentation: {display_duration * 1000}ms, ISI: {isi * 1000}ms"
    )

    positions, images = generate_dual_nback_sequence(num_trials, 3, n)
    nback_queue = []
    correct_responses = 0
    incorrect_responses = 0
    lapses = 0
    total_reaction_time = 0
    reaction_times = []

    # Create visual elements
    grid, outline = create_grid(win, 3)
    fixation_cross = visual.TextStim(win, text="+", color="white", height=32)
    level_text = visual.TextStim(win, text=f"Level: {n}-back", color="white", height=24, pos=(-450, 350))

    # Show initial instructions if first encounter
    if is_first_encounter:
        initial_feedback = f"No response required for the first {n} trials"
        feedback_text = visual.TextStim(win, text=initial_feedback, color=get_level_color(n), height=24, pos=(0, 0))

        # IMPORTANT: Do NOT draw the grid or lines here. Just show the text.
        feedback_text.draw()
        win.flip()
        core.wait(2)  # Wait for 2 seconds (or however long you need)

        # Clear the screen again (blank background) before starting actual trials
        win.flip()
        core.wait(0.5)

    lapse_feedback = None

    for i, (pos, img) in enumerate(zip(positions, images)):
        if i >= num_trials:
            break

        is_target = len(nback_queue) >= n and pos == nback_queue[-n][0] and img == nback_queue[-n][1]

        # Now that the instructions are done, draw the grid lines and background each trial
        draw_grid()
        for rect in grid:
            rect.lineColor = get_level_color(n)
            rect.draw()
        outline.lineColor = get_level_color(n)
        outline.draw()

        level_text.draw()
        fixation_cross.draw()

        # If lapse feedback is needed
        if lapse_feedback:
            lapse_feedback_stim = visual.TextStim(win, text=lapse_feedback, color="orange", height=24, pos=(0, 400))
            lapse_feedback_stim.draw()

        # Highlight and image stimuli
        highlight, image_stim = display_dual_stimulus(
            win, pos, img, 3, n_level=n, feedback_text=None, return_stims=True
        )
        highlight.draw()
        image_stim.draw()

        # Show everything
        win.flip()
        send_trigger(1)  # Send trigger for EEG
        core.wait(get_jitter(display_duration))

        # Clear stimuli and show fixation during ISI
        draw_grid()
        for rect in grid:
            rect.lineColor = get_level_color(n)
            rect.draw()
        outline.lineColor = get_level_color(n)
        outline.draw()
        fixation_cross.draw()
        level_text.draw()
        win.flip()

        # Response collection during ISI...
        response_timer = core.Clock()
        response = None
        jittered_isi = get_jitter(isi)

        while response_timer.getTime() < jittered_isi:
            keys = event.getKeys(keyList=["z", "m", "escape"])
            if "escape" in keys:
                core.quit()

            if keys and response is None and i >= n:
                reaction_time = response_timer.getTime()
                if "z" in keys:
                    response = True
                elif "m" in keys:
                    response = False

                if response == is_target:
                    correct_responses += 1
                else:
                    incorrect_responses += 1

                total_reaction_time += reaction_time
                reaction_times.append(reaction_time)

        # Handle lapses
        if response is None and i >= n:
            lapses += 1
            lapse_feedback = "Previous lapse, please respond"
        else:
            lapse_feedback = None

        nback_queue.append((pos, img))
        if len(nback_queue) > n:
            nback_queue.pop(0)

        event.clearEvents()

    # Adjust n-back level based on accuracy if needed
    total_responses = correct_responses + incorrect_responses + lapses
    accuracy = (correct_responses / total_responses) * 100 if total_responses > 0 else 0
    new_n_level = adjust_nback_level(n, accuracy)

    return new_n_level


def run_adaptive_nback_task(
    win, task_name, initial_n, num_blocks, target_duration, run_block_function, starting_block_number=0
):
    """Run a full adaptive N-back task across multiple blocks, adjusting difficulty based on performance.

    Args:
        win (visual.Window): PsychoPy window.
        task_name (str): Name of the task.
        initial_n (int): Starting N-back level.
        num_blocks (int): Number of blocks to run.
        target_duration (float): Total task duration in seconds.
        run_block_function (function): Block-running function specific to the task.
        starting_block_number (int, optional): Block numbering offset for progressive timing.
    """
    n_level = initial_n
    # Loop through main blocks
    for block in range(num_blocks):
        cumulative_block_number = starting_block_number + block
        logging.info(f"\nStarting block {cumulative_block_number + 1} of {task_name} with n-back level: {n_level}")

        # Get adjusted timings for the current block
        display_duration, isi = get_progressive_timings(task_name, cumulative_block_number)

        # Calculate the number of trials per sub-block
        sub_block_duration = target_duration / num_blocks / 3
        sub_block_trials = int(sub_block_duration / (display_duration + isi))

        for sub_block in range(3):
            is_first_encounter = cumulative_block_number == 0 and sub_block == 0

            # Run a sub-block using the provided run_block_function
            # The run_block_function adjusts the n-back level internally based on performance
            n_level = run_block_function(
                win,
                n_level,
                num_trials=sub_block_trials,
                display_duration=display_duration,
                isi=isi,
                is_first_encounter=is_first_encounter,
                block_number=cumulative_block_number,
            )

            # Display level change if n-back level was adjusted
            if n_level != initial_n:
                show_level_change_screen(win, task_name, initial_n, n_level, is_first_block=is_first_encounter)
                initial_n = n_level  # Update initial_n to the new level


def show_final_summary(win, seq_nbacks, subjective_measures, n_back_level):
    """
    Step through pages summarising every Sequential block, comparisons, and subjective changes.

    Args:
        win (visual.Window): PsychoPy window.
        seq_nbacks (list of dict): Block summaries from run_sequential_nback_block.
        subjective_measures (dict): Mapping time-points → four-item response lists.
        n_back_level (int): Final N-back level for headers.

    """
    logging.debug("Debug: Entering show_final_summary")
    summaries = []

    # Sequential N-back summaries
    for idx, seq_result in enumerate(seq_nbacks, 1):
        if seq_result is not None:
            seq_summary = calculate_sequential_nback_summary(seq_result, n_back_level)

            # Safely find and extract the detailed trial data for D-Prime calculation
            try:
                detailed_data = None

                # If seq_result is a list or tuple, try to get the trial data from position -2
                if isinstance(seq_result, (list, tuple)) and len(seq_result) >= 2:
                    detailed_data = seq_result[-2]
                    logging.debug(f"Found detailed_data at seq_result[-2]: {type(detailed_data)}")

                # If seq_result is a dictionary, look for keys that might contain the trial data
                elif isinstance(seq_result, dict):
                    # Try common keys that might contain trial data
                    possible_keys = ["detailed_data", "trials", "trial_data", "responses"]
                    for key in possible_keys:
                        if key in seq_result:
                            detailed_data = seq_result[key]
                            logging.debug(f"Found detailed_data at seq_result['{key}']: {type(detailed_data)}")
                            break

                # Make sure detailed_data is actually a list of dictionaries with required keys
                if detailed_data and isinstance(detailed_data, list) and len(detailed_data) > 0:
                    # Verify the expected structure by checking the first item
                    if (
                        isinstance(detailed_data[0], dict)
                        and "Is Target" in detailed_data[0]
                        and "Response" in detailed_data[0]
                    ):
                        seq_summary["D-Prime"] = calculate_dprime(detailed_data)
                        logging.debug(f"Successfully calculated D-Prime: {seq_summary['D-Prime']}")
                    else:
                        logging.warning(f"detailed_data items do not have the expected structure: {detailed_data[0]}")
                        seq_summary["D-Prime"] = 0.0
                else:
                    logging.warning(f"detailed_data is not a valid list: {detailed_data}")
                    seq_summary["D-Prime"] = 0.0

            except Exception as e:
                logging.error(f"Error calculating D-Prime: {e}")
                seq_summary["D-Prime"] = 0.0  # Default value

            summaries.append((f"Sequential {n_back_level}-back (Block {idx})", seq_summary))

    if not summaries:
        logging.debug("Debug: No valid results to display in the final summary.")
        return

    logging.debug(f"Debug: Number of summaries to display: {len(summaries)}")

    total_pages = len(summaries) + 2  # +2 for the comparison and subjective measures pages
    i = 0  # Index for the pages

    # Updated measure_names to include all four measures
    measure_names = ["Mental Fatigue", "Task Effort", "Mind Wandering", "Overwhelmed"]

    while i < total_pages:
        if i < len(summaries):
            # Display individual task summary
            task_name, summary = summaries[i]
            summary_text = f"{task_name} Summary:\n\n"
            summary_text += (
                f"N-back Level: {summary['N-back Level']}\n"
                f"Total Correct Responses: {summary['Total Correct Responses']}\n"
                f"Total Incorrect Responses: {summary['Total Incorrect Responses']}\n"
                f"Total Lapses: {summary['Total Lapses']}\n"
                f"Overall Accuracy: {summary['Overall Accuracy (%)']:.2f}%\n"
                f"Average Reaction Time: {summary['Average Reaction Time (s)']:.2f}s\n"
                f"Total Response Time: {summary['Average Reaction Time (s)'] * summary['Total Trials']:.2f}s\n"
                f"Total Trials: {summary['Total Trials']}\n"
                f"D-Prime: {summary['D-Prime']:.2f}\n"
            )

            summary_text += f"\nPage {i + 1} of {total_pages}\nPress 'space' to continue, 'backspace' to go back, or 'escape' to exit."

            summary_stim = visual.TextStim(win, text=summary_text, color="white", height=24, wrapWidth=800)
            summary_stim.draw()
            win.flip()

            keys = event.waitKeys(keyList=["space", "backspace", "escape"])
            if "space" in keys:
                i += 1
            elif "backspace" in keys:
                i = max(0, i - 1)
            elif "escape" in keys:
                return

        elif i == len(summaries):
            # Comparisons
            comparison_text = "Task Comparisons:\n\n"

            # Compare Sequential N-back tasks (first and fifth block)
            if seq_nbacks and seq_nbacks[0] is not None and seq_nbacks[-1] is not None:
                seq1 = calculate_sequential_nback_summary(seq_nbacks[0], n_back_level)
                seq5 = calculate_sequential_nback_summary(seq_nbacks[-1], n_back_level)

                # Safely calculate D-Prime for both sequences using the same approach as above
                for seq_idx, (seq_result, seq_summary) in enumerate([(seq_nbacks[0], seq1), (seq_nbacks[-1], seq5)]):
                    try:
                        detailed_data = None

                        if isinstance(seq_result, (list, tuple)) and len(seq_result) >= 2:
                            detailed_data = seq_result[-2]
                        elif isinstance(seq_result, dict):
                            possible_keys = ["detailed_data", "trials", "trial_data", "responses"]
                            for key in possible_keys:
                                if key in seq_result:
                                    detailed_data = seq_result[key]
                                    break

                        if detailed_data and isinstance(detailed_data, list) and len(detailed_data) > 0:
                            if (
                                isinstance(detailed_data[0], dict)
                                and "Is Target" in detailed_data[0]
                                and "Response" in detailed_data[0]
                            ):
                                seq_summary["D-Prime"] = calculate_dprime(detailed_data)
                            else:
                                seq_summary["D-Prime"] = 0.0
                        else:
                            seq_summary["D-Prime"] = 0.0
                    except Exception as e:
                        logging.error(f"Error calculating D-Prime for block {seq_idx + 1}: {e}")
                        seq_summary["D-Prime"] = 0.0

                accuracy_change = seq5["Overall Accuracy (%)"] - seq1["Overall Accuracy (%)"]
                rt_change = seq5["Average Reaction Time (s)"] - seq1["Average Reaction Time (s)"]
                total_rt1 = seq1["Average Reaction Time (s)"] * seq1["Total Trials"]
                total_rt5 = seq5["Average Reaction Time (s)"] * seq5["Total Trials"]
                total_rt_change = total_rt5 - total_rt1
                lapse_change = seq5["Total Lapses"] - seq1["Total Lapses"]
                d_prime_change = seq5["D-Prime"] - seq1["D-Prime"]

                comparison_text += "Sequential N-back (Block 1 vs Block 5):\n"
                comparison_text += f"Accuracy Change: {'Increase' if accuracy_change >= 0 else 'Decrease'} of {abs(accuracy_change):.2f}% ({seq1['Overall Accuracy (%)']:.2f}% to {seq5['Overall Accuracy (%)']:.2f}%)\n"
                comparison_text += f"Reaction Time Change: {'Increase' if rt_change >= 0 else 'Decrease'} of {abs(rt_change):.2f}s ({seq1['Average Reaction Time (s)']:.2f}s to {seq5['Average Reaction Time (s)']:.2f}s)\n"
                comparison_text += f"Total Response Time Change: {'Increase' if total_rt_change >= 0 else 'Decrease'} of {abs(total_rt_change):.2f}s ({total_rt1:.2f}s to {total_rt5:.2f}s)\n"
                comparison_text += f"Correct Responses Change: {seq5['Total Correct Responses'] - seq1['Total Correct Responses']} ({seq1['Total Correct Responses']} to {seq5['Total Correct Responses']})\n"
                comparison_text += f"Incorrect Responses Change: {seq5['Total Incorrect Responses'] - seq1['Total Incorrect Responses']} ({seq1['Total Incorrect Responses']} to {seq5['Total Incorrect Responses']})\n"
                comparison_text += f"Lapses Change: {lapse_change} ({seq1['Total Lapses']} to {seq5['Total Lapses']})\n"
                comparison_text += f"D-Prime Change: {'Increase' if d_prime_change >= 0 else 'Decrease'} of {abs(d_prime_change):.2f} ({seq1['D-Prime']:.2f} to {seq5['D-Prime']:.2f})\n"

            comparison_text += f"\nPage {i + 1} of {total_pages}\nPress 'space' to continue, 'backspace' to go back, or 'escape' to exit."

            comparison_stim = visual.TextStim(win, text=comparison_text, color="white", height=24, wrapWidth=800)
            comparison_stim.draw()
            win.flip()
            keys = event.waitKeys(keyList=["space", "backspace", "escape"])
            if "space" in keys:
                i += 1
            elif "backspace" in keys:
                i = max(0, i - 1)
            elif "escape" in keys:
                return

        else:
            # Subjective Measures Comparison
            subjective_text = "Subjective Measures Comparison:\n\n"

            time_points = list(subjective_measures.keys())

            for idx, measure in enumerate(measure_names):
                subjective_text += f"{measure}:\n"
                for time_point in time_points:
                    score = subjective_measures[time_point][idx]
                    subjective_text += f"  {time_point}: {score}\n"

                if len(time_points) > 1:
                    first_score = subjective_measures[time_points[0]][idx]
                    last_score = subjective_measures[time_points[-1]][idx]
                    change = last_score - first_score
                    subjective_text += f"  Overall Change: {'Increase' if change > 0 else 'Decrease' if change < 0 else 'No change'} of {abs(change)} ({first_score} to {last_score})\n"

                subjective_text += "\n"

            subjective_text += f"\nPage {i + 1} of {total_pages}\nPress 'space' to exit the summary, 'backspace' to go back, or 'escape' to exit."

            subjective_stim = visual.TextStim(win, text=subjective_text, color="white", height=24, wrapWidth=800)
            subjective_stim.draw()
            win.flip()
            keys = event.waitKeys(keyList=["space", "backspace", "escape"])
            if "space" in keys or "escape" in keys:
                return
            elif "backspace" in keys:
                i = max(0, i - 1)

    logging.debug("Debug: Exiting show_final_summary")


def run_dummy_session(win, n_back_level=2, num_trials=20):
    """
    Run a brief sequential N-back verification session.

    This does a fixed-length (default 20 trials) sequential N-back block
    so you can confirm that keys and window focus are working.  It then
    saves the results into a timestamped CSV under ./data/ and cleanly exits.

    1. Brings the PsychoPy window to the front.
    2. Shows a “focus and press space” screen so that you actually click
       the experiment window (locking keyboard focus).
    3. Runs the 20-trial sequential N-back.
    4. Writes out participant_dummy_n{level}_TestRun_{YYYYMMDD-HHMMSS}.csv.
    5. Prints the full path to console and quits.

    Args:
        win (visual.Window):
            Your PsychoPy window instance.
        n_back_level (int, optional):
            Which N-back to test (default=2).
        num_trials (int, optional):
            How many trials to run (default=20).

    Side-effects:
        - Creates ./data/ if needed.
        - Saves a timestamped CSV.
        - Closes the window and exits PsychoPy.
    """
    # --- 1) Bring the window forward and give it focus ---
    try:
        # pyglet backend: activate the context
        win.winHandle.activate()
    except Exception:
        pass
    core.wait(0.1)

    # --- 2) Instruction screen so user clicks and presses space ---
    instr = visual.TextStim(
        win,
        text=(
            "=== DUMMY TEST RUN ===\n\n"
            "This is a short 20-trial check.\n\n"
            "Please CLICK this window (to focus it) and then\n"
            "press SPACE to begin."
        ),
        color="white",
        height=24,
        wrapWidth=800,
    )
    instr.draw()
    win.flip()
    event.waitKeys(keyList=["space"])

    # --- 3) Run the tiny sequential N-back block ---
    dummy_results = run_sequential_nback_block(
        win=win,
        n=n_back_level,
        num_images=20,
        target_percentage=0.5,
        display_duration=0.8,
        isi=1.0,
        num_trials=num_trials,
        is_first_encounter=True,
        block_number=0,
    )

    # --- 4) Save to a timestamped CSV ---
    data_dir = os.path.join(base_dir, "data")
    os.makedirs(data_dir, exist_ok=True)
    timestamp = time.strftime("%Y%m%d-%H%M%S")
    fname = f"participant_dummy_n{n_back_level}_TestRun_{timestamp}.csv"

    full_path = save_results_to_csv(
        fname,
        [
            {
                "Participant ID": "dummy",
                "Task": f"Sequential {n_back_level}-back",
                "Block": "TestRun",
                "Results": dummy_results,
            }
        ],
    )

    # --- 5) Print & clean up ---
    print(f"\n✅ Dummy run complete!  CSV saved to:\n   {full_path}\n")
    win.close()
    core.quit()


def main_task_flow():
    """
    Main controller function for the full WAND fatigue induction experiment.

    Handles participant info, task sequencing, subjective measures, data logging,
    error management, and block-wise transitions for Sequential, Spatial, and Dual N-back.
    """
    logging.info("Entering main_task_flow()")
    try:
        # Hide the mouse cursor
        win.mouseVisible = False

        # Track block numbers for progressive timing
        spatial_block = 0
        dual_block = 0

        subjective_measures = {}

        # Get participant info including N-back level
        exp_info = get_participant_info(win)
        participant_id = exp_info["Participant ID"]
        n_back_level = exp_info["N-back Level"]

        # -- apply GUI seed / distractor choices ------------
        global GLOBAL_SEED, DISTRACTORS_ENABLED
        GLOBAL_SEED = exp_info["Seed"]
        DISTRACTORS_ENABLED = exp_info["Distractors"]

        if GLOBAL_SEED is not None:
            random.seed(GLOBAL_SEED)
            try:
                import numpy as np
                np.random.seed(GLOBAL_SEED)
            except ModuleNotFoundError:
                pass

        # Set up the base directory and data directory
        if getattr(sys, "frozen", False):
            base_dir = sys._MEIPASS
        else:
            base_dir = os.path.dirname(os.path.abspath(__file__))
        data_dir = os.path.join(base_dir, "data")
        os.makedirs(data_dir, exist_ok=True)

        # Define the log filename and path
        log_filename = f"participant_{participant_id}_log.txt"
        log_file_path = os.path.join(data_dir, log_filename)

        # Create a custom handler that flushes after each record
        flush_file_handler = FlushFileHandler(log_file_path, mode="w", encoding="utf-8")
        flush_file_handler.setLevel(logging.DEBUG)
        formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
        flush_file_handler.setFormatter(formatter)

        # Configure logging with the custom handler
        logging.getLogger().handlers = []  # Clear existing handlers
        logging.getLogger().addHandler(flush_file_handler)
        logging.getLogger().addHandler(logging.StreamHandler())
        logging.getLogger().setLevel(logging.DEBUG)

        logging.info("Starting main_task_flow()")
        logging.info(f"Participant ID: {participant_id}")
        logging.info(f"Selected N-back Level: {n_back_level}")

        show_overall_welcome_screen(win)
        show_welcome_screen(win, "Sequential N-back", n_back_level)
        logging.info("Welcome screen shown")

        # Familiarisation block before first Sequential N-back
        logging.info(f"Starting Sequential {n_back_level}-back PRACTICE/FAMILIARISATION round")
        try:
            familiarisation_text = (
                f"Let's start with a 1-minute practice round.\n\n"
                f"This is just for familiarisation - your responses won't be scored.\n\n"
                f"Remember:\n"
                f"- Press 'Z' if the current image matches the image from {n_back_level} steps back\n"
                f"- Press 'M' if it doesn't match\n"
                f"- No response needed for the first {n_back_level} images\n\n"
                "Press 'space' to begin the practice."
            )
            instruction_text = visual.TextStim(win, text=familiarisation_text, color="white", height=24, wrapWidth=800)
            instruction_text.draw()
            win.flip()
            event.waitKeys(keyList=["space"])

            # Calculate trials needed for 1 minute (2s per trial)
            num_practice_trials = int(60 / 2)  # 30 trials will take 1 minute
            _ = run_sequential_nback_block(
                win,
                n_back_level,
                num_images,
                target_percentage=0.5,
                display_duration=0.8,
                isi=1.0,
                num_trials=num_practice_trials,
                is_first_encounter=True,
                block_number="PRACTICE",  # Changed from numerical block number
            )

            completion_text = (
                "Practice complete!\n\n"
                "Now we'll begin the actual task.\n"
                "Your responses will be recorded from this point forward.\n\n"
                "Press 'space' to start the first block."
            )
            completion_stim = visual.TextStim(win, text=completion_text, color="white", height=24, wrapWidth=800)
            completion_stim.draw()
            win.flip()
            event.waitKeys(keyList=["space"])
        except Exception as e:
            logging.info(f"Error in Sequential N-back familiarisation: {e}")
            logging.exception("Exception occurred")

        # Collect initial subjective measures
        initial_measures = collect_subjective_measures(win)
        subjective_measures["Initial"] = initial_measures

        # Sequential N-back Task - First Block
        logging.info(f"Starting Sequential {n_back_level}-back Task - Block 1 (display_duration: 800ms, ISI: 1000ms)")
        seq1_results = None
        try:
            seq1_results = run_sequential_nback_block(
                win,
                n_back_level,
                num_images,
                target_percentage=0.5,
                display_duration=0.8,
                isi=1.0,
                num_trials=164,
                is_first_encounter=True,
                block_number=1,
            )
            save_sequential_results(participant_id, n_back_level, "Block_1", seq1_results)
        except Exception as e:
            logging.info(f"Error in Sequential N-back Task (Block 1): {e}")
            logging.exception("Exception occurred")

        # First Spatial N-back Block
        logging.info("Starting Spatial N-back Task - Block 1")
        try:
            show_transition_screen(win, "Spatial N-back")
            show_welcome_screen(win, "Spatial N-back")
            run_adaptive_nback_task(
                win,
                "Spatial N-back",
                n_back_level,
                1,
                270,
                lambda w, n, num_trials, display_duration, isi, is_first_encounter, block_number: run_spatial_nback_block(
                    w, n, num_trials, display_duration, isi, is_first_encounter, block_number=block_number
                ),
                starting_block_number=spatial_block,
            )
            spatial_block += 1
        except Exception as e:
            logging.info(f"Error in Spatial N-back Task (Block 1): {e}")
            logging.exception("Exception occurred")

        # First Dual N-back Block
        logging.info("Starting Dual N-back Task - Block 1")
        try:
            show_transition_screen(win, "Dual N-back")
            show_welcome_screen(win, "Dual N-back")
            run_adaptive_nback_task(
                win,
                "Dual N-back",
                n_back_level,
                1,
                270,
                lambda w, n, num_trials, display_duration, isi, is_first_encounter, block_number: run_dual_nback_block(
                    w, n, num_trials, display_duration, isi, is_first_encounter, block_number=block_number
                ),
                starting_block_number=dual_block,
            )
            dual_block += 1
        except Exception as e:
            logging.info(f"Error in Dual N-back Task (Block 1): {e}")
            logging.exception("Exception occurred")

        # Sequential N-back Task - Second Block
        logging.info(f"Starting Sequential {n_back_level}-back Task - Block 2 (display_duration: 800ms, ISI: 1000ms))")
        seq2_results = None
        try:
            show_transition_screen(win, "Sequential N-back")
            seq2_results = run_sequential_nback_block(
                win,
                n_back_level,
                num_images,
                target_percentage=0.5,
                display_duration=0.8,
                isi=1.0,
                num_trials=164,
                is_first_encounter=False,
                block_number=2,
            )
            save_sequential_results(participant_id, n_back_level, "Block_2", seq2_results)
        except Exception as e:
            logging.info(f"Error in Sequential N-back Task (Block 2): {e}")
            logging.exception("Exception occurred")

        induction1_measures = collect_subjective_measures(win)
        subjective_measures["Induction 1"] = induction1_measures
        show_break_screen(win, 20)

        # Dual N-back Task - Second Block
        logging.info("Starting Dual N-back Task - Block 2")
        try:
            show_transition_screen(win, "Dual N-back")
            run_adaptive_nback_task(
                win,
                "Dual N-back",
                n_back_level,
                1,
                270,
                lambda w, n, num_trials, display_duration, isi, is_first_encounter, block_number: run_dual_nback_block(
                    w, n, num_trials, display_duration, isi, is_first_encounter, block_number=block_number
                ),
                starting_block_number=dual_block,
            )
            dual_block += 1
        except Exception as e:
            logging.info(f"Error in Dual N-back Task (Block 2): {e}")
            logging.exception("Exception occurred")

        # Spatial N-back Task - Second Block
        logging.info("Starting Spatial N-back Task - Block 2")
        try:
            show_transition_screen(win, "Spatial N-back")
            run_adaptive_nback_task(
                win,
                "Spatial N-back",
                n_back_level,
                1,
                270,
                lambda w, n, num_trials, display_duration, isi, is_first_encounter, block_number: run_spatial_nback_block(
                    w, n, num_trials, display_duration, isi, is_first_encounter, block_number=block_number
                ),
                starting_block_number=spatial_block,
            )
            spatial_block += 1
        except Exception as e:
            logging.info(f"Error in Spatial N-back Task (Block 2): {e}")
            logging.exception("Exception occurred")

        # Sequential N-back Task - Third Block
        logging.info(f"Starting Sequential {n_back_level}-back Task - Block 3 (display_duration: 800ms, ISI: 1000ms)")
        seq3_results = None
        try:
            show_transition_screen(win, "Sequential N-back")
            seq3_results = run_sequential_nback_block(
                win,
                n_back_level,
                num_images,
                target_percentage=0.5,
                display_duration=0.8,
                isi=1.0,
                num_trials=164,
                is_first_encounter=False,
                block_number=3,
            )
            save_sequential_results(participant_id, n_back_level, "Block_3", seq3_results)
        except Exception as e:
            logging.info(f"Error in Sequential N-back Task (Block 3): {e}")
            logging.exception("Exception occurred")

        induction2_measures = collect_subjective_measures(win)
        subjective_measures["Induction 2"] = induction2_measures

        # Spatial N-back Task - Third Block
        logging.info("Starting Spatial N-back Task - Block 3")
        try:
            show_transition_screen(win, "Spatial N-back")
            run_adaptive_nback_task(
                win,
                "Spatial N-back",
                n_back_level,
                1,
                270,
                lambda w, n, num_trials, display_duration, isi, is_first_encounter, block_number: run_spatial_nback_block(
                    w, n, num_trials, display_duration, isi, is_first_encounter, block_number=block_number
                ),
                starting_block_number=spatial_block,
            )
            spatial_block += 1
        except Exception as e:
            logging.info(f"Error in Spatial N-back Task (Block 3): {e}")
            logging.exception("Exception occurred")

        # Dual N-back Task - Third Block
        logging.info("Starting Dual N-back Task - Block 3")
        try:
            show_transition_screen(win, "Dual N-back")
            run_adaptive_nback_task(
                win,
                "Dual N-back",
                n_back_level,
                1,
                270,
                lambda w, n, num_trials, display_duration, isi, is_first_encounter, block_number: run_dual_nback_block(
                    w, n, num_trials, display_duration, isi, is_first_encounter, block_number=block_number
                ),
                starting_block_number=dual_block,
            )
            dual_block += 1
        except Exception as e:
            logging.info(f"Error in Dual N-back Task (Block 3): {e}")
            logging.exception("Exception occurred")

        # Sequential N-back Task - Fourth Block
        logging.info(f"Starting Sequential {n_back_level}-back Task - Block 4 (display_duration: 800ms, ISI: 1000ms)")
        seq4_results = None
        try:
            show_transition_screen(win, "Sequential N-back")
            seq4_results = run_sequential_nback_block(
                win,
                n_back_level,
                num_images,
                target_percentage=0.5,
                display_duration=0.8,
                isi=1.0,
                num_trials=164,
                is_first_encounter=False,
                block_number=4,
            )
            save_sequential_results(participant_id, n_back_level, "Block_4", seq4_results)
        except Exception as e:
            logging.info(f"Error in Sequential N-back Task (Block 4): {e}")
            logging.exception("Exception occurred")

        # Collect measures after fourth Sequential block
        induction3_measures = collect_subjective_measures(win)
        subjective_measures["Induction 3"] = induction3_measures
        show_break_screen(win, 20)

        # Dual N-back Task - Fourth Block
        logging.info("Starting Dual N-back Task - Block 4")
        try:
            show_transition_screen(win, "Dual N-back")
            run_adaptive_nback_task(
                win,
                "Dual N-back",
                n_back_level,
                1,
                270,
                lambda w, n, num_trials, display_duration, isi, is_first_encounter, block_number: run_dual_nback_block(
                    w, n, num_trials, display_duration, isi, is_first_encounter, block_number=block_number
                ),
                starting_block_number=dual_block,
            )
            dual_block += 1
        except Exception as e:
            logging.info(f"Error in Dual N-back Task (Block 4): {e}")
            logging.exception("Exception occurred")

        # Spatial N-back Task - Fourth Block
        logging.info("Starting Spatial N-back Task - Block 4")
        try:
            show_transition_screen(win, "Spatial N-back")
            run_adaptive_nback_task(
                win,
                "Spatial N-back",
                n_back_level,
                1,
                270,
                lambda w, n, num_trials, display_duration, isi, is_first_encounter, block_number: run_spatial_nback_block(
                    w, n, num_trials, display_duration, isi, is_first_encounter, block_number=block_number
                ),
                starting_block_number=spatial_block,
            )
            spatial_block += 1
        except Exception as e:
            logging.info(f"Error in Spatial N-back Task (Block 4): {e}")
            logging.exception("Exception occurred")

        # Sequential N-back Task - Fifth Block
        logging.info(f"Starting Sequential {n_back_level}-back Task - Block 5 (display_duration: 800ms, ISI: 1000ms)")
        seq5_results = None
        try:
            show_transition_screen(win, "Sequential N-back")
            seq5_results = run_sequential_nback_block(
                win,
                n_back_level,
                num_images,
                target_percentage=0.5,
                display_duration=0.8,
                isi=1.0,
                num_trials=164,
                is_first_encounter=False,
                block_number=5,
            )
            save_sequential_results(participant_id, n_back_level, "Block_5", seq5_results)
        except Exception as e:
            logging.info(f"Error in Sequential N-back Task (Block 5): {e}")
            logging.exception("Exception occurred")

        post_all_measures = collect_subjective_measures(win)
        subjective_measures["Post-All"] = post_all_measures

        # Show final summary comparing all tasks
        logging.info("Showing final summary")
        try:
            show_final_summary(
                win,
                [seq1_results, seq2_results, seq3_results, seq4_results, seq5_results],
                subjective_measures,
                n_back_level,
            )
        except Exception as e:
            logging.info(f"Error in showing final summary: {e}")
            logging.exception("Exception occurred")

        # Save results to CSV
        logging.info("Saving results to CSV")
        try:
            results_filename = f"participant_{participant_id}_n{n_back_level}_results.csv"
            all_results = [
                {
                    "Participant ID": participant_id,
                    "N-back Level": n_back_level,
                    "Task": f"Sequential {n_back_level}-back",
                    "Block": 1,
                    "Results": seq1_results,
                },
                {
                    "Participant ID": participant_id,
                    "N-back Level": n_back_level,
                    "Task": f"Sequential {n_back_level}-back",
                    "Block": 2,
                    "Results": seq2_results,
                },
                {
                    "Participant ID": participant_id,
                    "N-back Level": n_back_level,
                    "Task": f"Sequential {n_back_level}-back",
                    "Block": 3,
                    "Results": seq3_results,
                },
                {
                    "Participant ID": participant_id,
                    "N-back Level": n_back_level,
                    "Task": f"Sequential {n_back_level}-back",
                    "Block": 4,
                    "Results": seq4_results,
                },
                {
                    "Participant ID": participant_id,
                    "N-back Level": n_back_level,
                    "Task": f"Sequential {n_back_level}-back",
                    "Block": 5,
                    "Results": seq5_results,
                },
            ]
            saved_file_path = save_results_to_csv(results_filename, all_results, subjective_measures)
            logging.info(f"Results and subjective measures saved to {saved_file_path}")

            final_message = visual.TextStim(
                win,
                text=f"Thank you for participating in the experiment!\n\nYour results have been saved to:\n{saved_file_path}\n\nPress 'space' to exit.",
                color="white",
                height=24,
                wrapWidth=800,
            )
            final_message.draw()
            win.flip()
            event.waitKeys(keyList=["space"])
        except Exception as e:
            logging.info(f"Error in saving results to CSV: {e}")
            logging.exception("Exception occurred")
    except Exception as e:
        logging.info(f"Error in main_task_flow: {e}")
        logging.exception("Exception occurred in main_task_flow")
    logging.info("Exiting main_task_flow()")
    win.close()
    core.quit()



if __name__ == "__main__":
    if args.dummy:
        run_dummy_session(win, n_back_level=2, num_trials=20)
    else:
        main_task_flow()

