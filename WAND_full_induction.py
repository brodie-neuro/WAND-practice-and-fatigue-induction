#!/usr/bin/env python3
"""
WAND — Full Fatigue Induction

Full cognitive-fatigue induction protocol using the WAND
(Working-memory Adaptive-fatigue with N-back Difficulty) model.

Participants complete adaptive Sequential, Spatial, and Dual N-back tasks to
induce active mental fatigue, with detailed behavioural performance and
subjective measures collected throughout.

Designed for cognitive-fatigue research (EEG-compatible and behavioural-only).

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
import csv
import logging
import math
import os
import random
import sys
import time

from psychopy import core, event, visual

from wand_common import (
    create_grid,
    create_grid_lines,
    display_dual_stimulus,
    display_grid,
    draw_grid,
    generate_dual_nback_sequence,
    generate_positions_with_matches,
    get_jitter,
    get_level_color,
    get_param,
    get_text,
    install_error_hook,
    load_config,
    set_grid_lines,
)

# --------------- CLI FLAGS (dummy‑run only) ---------------

parser = argparse.ArgumentParser(add_help=False)
parser.add_argument(
    "--seed", type=int, default=None
)  # still allowed but GUI will override
parser.add_argument("--distractors", choices=["on", "off"], default=None)
parser.add_argument("--dummy", action="store_true", help="Run 20‑trial test then exit")
args, _ = parser.parse_known_args()

# placeholders – will be overwritten by the GUI wizard later
GLOBAL_SEED = args.seed  # None → random each run
DISTRACTORS_ENABLED = (args.distractors != "off") if args.distractors else True


try:
    from scipy.stats import norm
except ImportError:
    logging.error(
        "SciPy is required for d-prime calculation. Install with 'pip install scipy'."
    )
    core.quit()

# determine where this script lives on _any_ machine

if getattr(sys, "frozen", False):
    # if you’ve bundled into an executable
    base_dir = sys._MEIPASS
else:
    base_dir = os.path.dirname(os.path.abspath(__file__))

CONFIG_DIR = os.path.join(base_dir, "config")
load_config(lang="en", config_dir=CONFIG_DIR)

# === Window configuration (from params.json) ===
WIN_FULLSCR = bool(get_param("window.fullscreen", False))
WIN_SIZE = tuple(get_param("window.size", [1650, 1000]))
WIN_MONITOR = str(get_param("window.monitor", "testMonitor"))
WIN_BG = get_param("window.background_color", "black")
WIN_COLORSP = get_param("window.color_space", "rgb")
WIN_USEFBO = bool(get_param("window.use_fbo", True))

# Image folder stays as a code path (can be moved to params later if you want)
image_dir = os.path.join(base_dir, "Abstract Stimuli", "apophysis")


# === Logging Configuration ===
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


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

# Basic environment info
logging.info("Script started")
logging.debug(f"Python version: {sys.version}")
logging.debug(f"Base directory: {base_dir}")
logging.debug(f"Current working directory: {os.getcwd()}")

try:
    import psychopy

    logging.debug(f"PsychoPy version: {psychopy.__version__}")
except ImportError:
    logging.error("Failed to import PsychoPy")

# Error hook bound to this window, then grid registration
install_error_hook(win)
grid_lines = create_grid_lines(win)
set_grid_lines(grid_lines)

# Global escape key to quit cleanly
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
    image_file: visual.ImageStim(
        win, image=os.path.join(image_dir, image_file), size=(350, 350)
    )
    for image_file in image_files
}

preloaded_images_dual = {
    image_file: visual.ImageStim(
        win, image=os.path.join(image_dir, image_file), size=(100, 100)
    )
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
    Collect participant and run options via on-screen prompts.

    Parameters
    ----------
    win : psychopy.visual.Window
        The active PsychoPy window used to render prompts.

    Returns
    -------
    dict
        A dictionary with keys:
        - 'Participant ID' : str
        - 'N-back Level'   : int
        - 'Seed'           : Optional[int]
        - 'Distractors'    : bool"""
    win.mouseVisible = False
    text24 = dict(height=24, color="white", wrapWidth=900)

    # — 1 Participant ID —
    pid = ""
    while True:
        visual.TextStim(win, text=get_text("get_pid"), **text24, pos=(0, 120)).draw()
        box = visual.Rect(win, width=380, height=50, lineColor="white", pos=(0, 40))
        box.draw()
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
        prompt = get_text("get_n_level")
        visual.TextStim(win, text=prompt, **text24).draw()
        win.flip()
        key = event.waitKeys(keyList=["2", "3"])[0]
        n_level = int(key)
        break

    # — 3 Seed entry (optional) —
    seed_txt = ""
    while True:
        msg = get_text("get_seed")
        visual.TextStim(win, text=msg, **text24, pos=(0, 120)).draw()
        box = visual.Rect(win, width=380, height=50, lineColor="white", pos=(0, 40))
        box.draw()
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
        prompt = get_text("get_distractors")
        visual.TextStim(win, text=prompt, **text24).draw()
        win.flip()
        key = event.waitKeys(keyList=["y", "n"])[0]
        distractors = key == "y"
        break

    win.flip()
    return {
        "Participant ID": pid,
        "N-back Level": n_level,
        "Seed": seed_val,
        "Distractors": distractors,
    }


def save_results_to_csv(filename, results, subjective_measures=None, mode="w"):
    """
    Write behavioural results and optional subjective measures to a CSV file.

    Parameters
    ----------
    filename : str
        Base name of the CSV (e.g., 'participant_01_results.csv').
    results : List[dict]
        Each dict must contain:
        - 'Participant ID' : str
        - 'Task'           : str
        - 'Block'          : Union[int, str]
        - 'N-back Level'   : Optional[int]
        - 'Results'        : dict  (block metrics)
    subjective_measures : Optional[dict], optional
        Mapping of time-point labels to four scores
        [Mental Fatigue, Task Effort, Mind Wandering, Overwhelmed], by default None.
    mode : {"w","a"}, optional
        File mode: 'w' to create/overwrite, 'a' to append. Default 'w'.

    Returns
    -------
    Optional[str]
        Full path to the saved CSV on success, otherwise None.

    Notes
    -----
    - Creates a `data/` folder under the script directory if it does not exist.
    - Writes a provenance row indicating the RNG seed used.
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
                writer.writerow(
                    ["Seed Used", GLOBAL_SEED if GLOBAL_SEED is not None else "random"]
                )
                # standard behavioural header row
                writer.writerow(
                    [
                        "Participant ID",
                        "Task",
                        "Block",
                        "N-back Level",
                        "Measure",
                        "Value",
                    ]
                )
                logging.debug("Headers + seed row written")

            # ─────────────────────────────────────────────────────────
            #   behavioural results blocks
            # ─────────────────────────────────────────────────────────
            for i, result in enumerate(results):
                logging.debug(f"Processing result {i + 1}")
                try:
                    participant_id = result.get("Participant ID", "Unknown")
                    task = result.get("Task", "Unknown Task")
                    block = result.get("Block", "Unknown Block")
                    n_back_level = result.get("N-back Level", "Unknown")
                    data = result.get("Results")

                    if isinstance(data, dict):
                        # overall metrics
                        for measure in [
                            "Correct Responses",
                            "Incorrect Responses",
                            "Lapses",
                            "Accuracy",
                            "Total Reaction Time",
                            "Average Reaction Time",
                            "Overall D-Prime",
                        ]:
                            writer.writerow(
                                [
                                    participant_id,
                                    task,
                                    block,
                                    n_back_level,
                                    measure,
                                    data.get(measure, "N/A"),
                                ]
                            )

                        # pre‑ & post‑distractor metrics
                        for section in [
                            ("Pre", ["Accuracy", "Avg RT", "A-Prime"]),
                            ("Post", ["Accuracy", "Avg RT", "A-Prime"]),
                        ]:
                            prefix, keys = section
                            for k in keys:
                                col_name = f"{prefix}-Distractor {k}"
                                writer.writerow(
                                    [
                                        participant_id,
                                        task,
                                        block,
                                        n_back_level,
                                        col_name,
                                        data.get(col_name, "N/A"),
                                    ]
                                )
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
                        writer.writerow(
                            [participant_id, time_point, "Mental Fatigue", measures[0]]
                        )
                        writer.writerow(
                            [participant_id, time_point, "Task Effort", measures[1]]
                        )
                        writer.writerow(
                            [participant_id, time_point, "Mind Wandering", measures[2]]
                        )
                        writer.writerow(
                            [participant_id, time_point, "Overwhelmed", measures[3]]
                        )
                    except Exception as e:
                        logging.error(
                            f"Error saving subjective measures for {time_point}: {e}"
                        )
                        continue

        logging.info(f"Results and subjective measures saved to {full_path}")
        return full_path

    except Exception as e:
        logging.error(f"Failed to save results to {full_path}: {e}")
        # fail‑safe: display error to participant if the window exists
        try:
            error_stim = visual.TextStim(
                win,
                text=get_text("error_saving"),
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
    Save one Sequential N-back block's results to a per-participant CSV.

    Parameters
    ----------
    participant_id : str
        Unique identifier for the participant.
    n_back_level : int
        The N-back difficulty used in the block.
    block_name : str
        Label for the block (e.g., "Block_1", "First_Block").
    seq_results : dict
        The block-level results dictionary (as returned by `run_sequential_nback_block`).

    Returns
    -------
    None
    """
    results_filename = (
        f"participant_{participant_id}_n{n_back_level}_{block_name}_results.csv"
    )
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
    Display the experiment welcome screen and wait for Space.

    Parameters
    ----------
    win : psychopy.visual.Window
        The active PsychoPy window.

    Returns
    -------
    None
    """
    welcome_text = get_text("induction_welcome")
    welcome_message = visual.TextStim(
        win, text=welcome_text, color="white", height=24, wrapWidth=800
    )
    welcome_message.draw()
    win.flip()
    event.waitKeys(keyList=["space"])


def show_welcome_screen(win, task_name, n_back_level=None):
    """
    Show task-specific instructions with a 20-second auto-advance.

    Parameters
    ----------
    win : psychopy.visual.Window
        PsychoPy window.
    task_name : str
        One of "Sequential N-back", "Spatial N-back", "Dual N-back".
    n_back_level : Optional[int], optional
        Included in the text for the Sequential task, by default None.

    Returns
    -------
    None
    """
    if task_name == "Sequential N-back":
        welcome_text = get_text("induction_task_welcome_seq", n_back_level=n_back_level)
    elif task_name == "Spatial N-back":
        welcome_text = get_text("induction_task_welcome_spa")
    elif task_name == "Dual N-back":
        welcome_text = get_text("induction_task_welcome_dual")
    else:
        # Fallback for any unknown task names
        welcome_text = get_text("task_instructions_fallback")

        # Append a concise auto-advance prompt
    welcome_text += get_text("induction_task_advance_prompt")

    welcome_message = visual.TextStim(
        win, text=welcome_text, color="white", height=24, wrapWidth=800
    )
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
        timer_text = get_text("timer_remaining", seconds=time_left)
        timer_stim = visual.TextStim(
            win, text=timer_text, color="white", height=18, pos=(0, -300)
        )
        welcome_message.draw()
        timer_stim.draw()
        win.flip()
    event.clearEvents()


def show_break_screen(win, duration):
    """
    Display a timed rest screen between blocks.

    Parameters
    ----------
    win : psychopy.visual.Window
        PsychoPy window.
    duration : int
        Break length in seconds.

    Returns
    -------
    None
    """
    break_text_base = get_text("induction_break_screen", duration=duration)
    break_stim = visual.TextStim(
        win, text=break_text_base, color="white", height=24, wrapWidth=800
    )

    timer = core.CountdownTimer(duration)
    while timer.getTime() > 0:
        timer_text = get_text("timer_remaining", seconds=int(timer.getTime()))
        break_stim.text = (
            break_text_base
            + "\n\n"
            + get_text("timer_remaining", seconds=int(timer.getTime()))
        )
        break_stim.draw()
        win.flip()
        if event.getKeys(["escape"]):
            core.quit()

    event.clearEvents()


def collect_subjective_measures(win):
    """
    Administer four 1–8 Likert items: fatigue, effort, mind-wandering, overwhelmed.

    Parameters
    ----------
    win : psychopy.visual.Window
        PsychoPy window.

    Returns
    -------
    List[int]
        Four integer responses in order:
        [Mental Fatigue, Task Effort, Mind Wandering, Overwhelmed].
    """
    questions = [
        get_text("induction_subjective_q1"),
        get_text("induction_subjective_q2"),
        get_text("induction_subjective_q3"),
        get_text("induction_subjective_q4"),
    ]
    responses = []

    for question in questions:
        instruction_text = question + get_text("induction_subjective_prompt")
        instruction_stim = visual.TextStim(
            win, text=instruction_text, height=24, wrapWidth=800
        )

        response = None
        while response is None:
            instruction_stim.draw()
            win.flip()
            keys = event.getKeys(
                keyList=["1", "2", "3", "4", "5", "6", "7", "8", "escape"]
            )
            if keys:
                if "escape" in keys:
                    core.quit()
                response = int(keys[0])
        responses.append(response)

    return responses


def get_progressive_timings(task_name, block_number):
    """
    Compute block-dependent presentation and ISI durations.

    Parameters
    ----------
    task_name : str
        "Spatial N-back" or "Dual N-back" (others yield no change).
    block_number : int
        Zero-based block index (cumulative across the task).

    Returns
    -------
    Tuple[float, float]
        (presentation_time_s, isi_time_s) after applying per-block reductions.
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

    presentation_reduction = min(
        block_number * presentation_reduction_per_block, max_presentation_reduction
    )
    isi_reduction = min(block_number * isi_reduction_per_block, max_isi_reduction)

    presentation_time = base_presentation - presentation_reduction
    isi = base_isi - isi_reduction

    return presentation_time, isi


def calculate_A_prime(trials):
    """
    Compute the A′ (A-prime) nonparametric sensitivity index.

    Parameters
    ----------
    trials : List[dict]
        Trial dicts with at least 'Is Target' (bool) and 'Response' (str) keys.
        'Response' is one of {'match', 'non-match', 'lapse'}.

    Returns
    -------
    Optional[float]
        A′ value in [0,1], or None if it cannot be computed (e.g., no targets).

    Notes
    -----
    Hit/false-alarm rates are clipped to avoid pathological extremes.
    """
    hits = sum(
        1 for trial in trials if trial["Is Target"] and trial["Response"] == "match"
    )
    false_alarms = sum(
        1 for trial in trials if not trial["Is Target"] and trial["Response"] == "match"
    )
    misses = sum(
        1 for trial in trials if trial["Is Target"] and trial["Response"] != "match"
    )
    correct_rejections = sum(
        1 for trial in trials if not trial["Is Target"] and trial["Response"] != "match"
    )

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
        A_prime = 0.5 + (
            (hit_rate - false_alarm_rate) * (1 + hit_rate - false_alarm_rate)
        ) / (4 * hit_rate * (1 - false_alarm_rate))
    else:
        A_prime = 0.5 - (
            (false_alarm_rate - hit_rate) * (1 + false_alarm_rate - hit_rate)
        ) / (4 * false_alarm_rate * (1 - hit_rate))

    return A_prime


def calculate_accuracy_and_rt(trials):
    """
    Compute accuracy (%), total RT, and average RT from trial data.

    Parameters
    ----------
    trials : List[dict]
        Trial dicts including 'Accuracy' (bool) and 'Reaction Time' (Optional[float]).

    Returns
    -------
    Tuple[float, float, float]
        (accuracy_percent, total_rt, average_rt)
    """
    total_trials = len(trials)
    correct = sum(1 for trial in trials if trial["Accuracy"])
    accuracy = (correct / total_trials) * 100 if total_trials > 0 else 0.0
    reaction_times = [
        trial["Reaction Time"] for trial in trials if trial["Reaction Time"] is not None
    ]
    total_rt = sum(reaction_times)
    avg_rt = total_rt / len(reaction_times) if reaction_times else 0.0
    return accuracy, total_rt, avg_rt


def calculate_dprime(detailed_data):
    """
    Compute d′ (d-prime) using the log-linear correction.

    Parameters
    ----------
    detailed_data : List[dict]
        Trial dicts with 'Is Target' (bool) and 'Response' (str).

    Returns
    -------
    float
        d′ value (0.0 if undefined or if all responses are lapses).

    Notes
    -----
    Applies the log-linear correction:
    (hits+0.5)/(targets+1), (FA+0.5)/(non-targets+1) before z-scoring.
    """
    if not detailed_data or all(
        trial["Response"] == "lapse" for trial in detailed_data
    ):
        return 0.0

    hits = sum(
        1
        for trial in detailed_data
        if trial["Is Target"] and trial["Response"] == "match"
    )
    false_alarms = sum(
        1
        for trial in detailed_data
        if not trial["Is Target"] and trial["Response"] == "match"
    )
    misses = sum(
        1
        for trial in detailed_data
        if trial["Is Target"] and trial["Response"] != "match"
    )
    correct_rejections = sum(
        1
        for trial in detailed_data
        if not trial["Is Target"] and trial["Response"] != "match"
    )

    total_targets = hits + misses
    total_non_targets = false_alarms + correct_rejections

    # Adjust hits and false alarms to avoid extreme values
    hit_rate = hits / total_targets if total_targets > 0 else 0
    fa_rate = false_alarms / total_non_targets if total_non_targets > 0 else 0

    # Apply the log-linear correction to avoid infinite z-scores
    adjusted_hit_rate = (hits + 0.5) / (total_targets + 1)
    adjusted_fa_rate = (false_alarms + 0.5) / (total_non_targets + 1)

    try:
        d_prime = norm.ppf(adjusted_hit_rate) - norm.ppf(adjusted_fa_rate)
    except ValueError:
        d_prime = 0.0

    return d_prime


def show_summary(win, task_name, *results):
    """
    Display a 10-second (or Space-to-advance) block summary screen.

    Parameters
    ----------
    win : psychopy.visual.Window
        PsychoPy window.
    task_name : str
        Name to display in the header.
    *results
        Tuple: (correct, incorrect, lapses, total_rt, reaction_times, detailed_data, accuracy)

    Returns
    -------
    None
    """
    (
        correct_responses,
        incorrect_responses,
        lapses,
        total_reaction_time,
        reaction_times,
        detailed_data,
        accuracy,
    ) = results
    total_responses = correct_responses + incorrect_responses + lapses
    avg_reaction_time = (
        total_reaction_time / len(reaction_times) if reaction_times else 0
    )
    d_prime = calculate_dprime(detailed_data)

    summary_text = get_text(
        "induction_summary_block",
        task_name=task_name,
        correct_responses=correct_responses,
        incorrect_responses=incorrect_responses,
        lapses=lapses,
        accuracy=accuracy,
        avg_reaction_time=avg_reaction_time,
        total_reaction_time=total_reaction_time,
        d_prime=d_prime,
    )

    summary_message = visual.TextStim(
        win, text=summary_text, color="white", height=24, wrapWidth=800
    )
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


def generate_image_sequence_with_matches(
    num_trials, n, target_percentage=0.5, skip_responses=1
):
    """
    Generate a sequence of images with true N-back targets (and 3-back lures).

    Parameters
    ----------
    num_trials : int
        Total sequence length (including initial non-response trials).
    n : int
        N-back distance (2 or 3).
    target_percentage : float, optional
        Proportion of eligible trials (i.e., after the first `n`) that should be
        true N-back matches. Default is 0.5.
    skip_responses : int, optional
        Number of initial trials without response requirements. Default is 1, but
        the task typically uses `n`.

    Returns
    -------
    Tuple[List[str], List[int]]
        (sequence, yes_positions) where `sequence` is a list of image filenames
        and `yes_positions` are indices of true n-back matches.

    Notes
    -----
    - For n==3, 30% of non-target positions become (n-1) lures.
    - Attempts to avoid unintended n- or 2-back repeats on non-target trials.
    """
    # Start with a fresh copy of the image list and shuffle it
    available_images = image_files.copy()
    random.shuffle(available_images)

    sequence = []
    max_consecutive_matches = int(get_param("sequential.max_consecutive_matches", 2))
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
                if img not in sequence[-n:]
                and (len(sequence) < 2 or img != sequence[-2])
            ]

            if not non_matching_images:
                # If no suitable non-matching images, fallback to whatever is available
                non_matching_images = available_images

            chosen_image = random.choice(non_matching_images)
            sequence.append(chosen_image)
            available_images.remove(chosen_image)
            consecutive_count = 0

    return sequence, yes_positions


def display_image(
    win, image_file, level_indicator, feedback_text=None, task="sequential"
):
    """
    Draw background grid, level text, and a central image; optional feedback.

    Parameters
    ----------
    win : psychopy.visual.Window
        PsychoPy window.
    image_file : str
        Key into the appropriate preloaded image dict.
    level_indicator : psychopy.visual.TextStim
        The “Level: N-back” text stimulus to draw.
    feedback_text : Optional[str], optional
        Short message drawn above the image if provided. Default None.
    task : {"sequential","dual"}
        Selects the preloaded image dictionary and default image size.

    Returns
    -------
    None
    """
    # Select the correct preloaded images based on the task
    if task == "sequential":
        image_stim = preloaded_images_sequential[image_file]
    elif task == "dual":
        image_stim = preloaded_images_dual[image_file]
    else:
        raise ValueError("Invalid task type. Choose 'sequential' or 'dual'.")

    # Ensure consistent size and position
    image_stim.size = (
        (350, 350) if task == "sequential" else (100, 100)
    )  # Default sizes for each task
    image_stim.pos = (0, 0)  # Always center for sequential

    # Draw the grid and level indicator first
    draw_grid()
    level_indicator.draw()

    # Draw the main image
    image_stim.draw()

    # Optionally, draw feedback text
    if feedback_text:
        feedback_message = visual.TextStim(
            win,
            text=feedback_text,
            color="orange",
            height=24,
            pos=(0, image_stim.size[1] / 2 + 50),
            units="pix",
        )
        feedback_message.draw()

    # Flip the display
    win.flip()


def calculate_sequential_nback_summary(results_dict, n_level):
    """
    Summarise a Sequential N-back block results dict into key metrics.

    Parameters
    ----------
    results_dict : dict
        Dictionary returned by `run_sequential_nback_block`.
    n_level : int
        N-back difficulty level used.

    Returns
    -------
    dict
        A compact summary with:
        'N-back Level', 'Total Correct Responses', 'Total Incorrect Responses',
        'Total Lapses', 'Overall Accuracy (%)', 'Average Reaction Time (s)',
        'Total Trials', 'D-Prime'.
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
    Run one Sequential N-back block and collect accuracy/RT/d′ metrics.

    Parameters
    ----------
    win : psychopy.visual.Window
        PsychoPy window.
    n : int
        N-back distance.
    num_images : int
        Number of distinct images available for sampling.
    target_percentage : float, optional
        Fraction of eligible trials that are true targets. Default 0.5.
    display_duration : float, optional
        Stimulus on-screen time (s). Default 0.8.
    isi : float, optional
        Base inter-stimulus interval (s). Jitter is applied. Default 1.0.
    provide_feedback : bool, optional
        If True, draw trial-wise feedback. Default False.
    num_trials : Optional[int], optional
        Override total trials (otherwise uses generated sequence length).
    is_first_encounter : bool, optional
        If True, show “no response” guidance for the first `n` trials. Default True.
    block_number : Union[int, str], optional
        Block index or label (for logging). Default 1.

    Returns
    -------
    dict
        Block summary with keys:
        'Block Number', 'Correct Responses', 'Incorrect Responses', 'Lapses',
        'Accuracy', 'Total Reaction Time', 'Average Reaction Time',
        'Reaction Times', 'Detailed Data',
        'Pre-Distractor Accuracy', 'Pre-Distractor Avg RT', 'Pre-Distractor A-Prime',
        'Post-Distractor Accuracy', 'Post-Distractor Avg RT', 'Post-Distractor A-Prime',
        'Overall D-Prime'.
    """
    # Number of initial trials without required responses
    skip_responses = n

    # Generate the image sequence and target positions
    num_images_to_generate = (
        max(num_images, num_trials) if num_trials is not None else num_images
    )
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
    fixation_cross = visual.TextStim(
        win, text="+", color="white", height=32, units="pix", pos=(0, 0)
    )
    margin_x, margin_y = 350, 150
    level_indicator = visual.TextStim(
        win,
        text=get_text("level_label", n=n),
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

    if DISTRACTORS_ENABLED and LATEST_DISTRACTOR - EARLIEST_DISTRACTOR + 1 >= 1:
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
        logging.info(
            f"Block {block_number}: Distractor positions → {distractor_trials}"
        )
    else:
        distractor_trials = []
        logging.info(f"Block {block_number}: Distractors disabled")

    # ─────────────────────────────────────────────────────────────
    #  First‑block notice (for the initial n non‑response trials)
    # ─────────────────────────────────────────────────────────────
    if is_first_encounter:
        msg = get_text("no_response_needed", n=n)
        feedback_text = visual.TextStim(
            win, text=msg, color="white", height=24, units="pix"
        )
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
            feedback_text = get_text("lapse_feedback")
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
            if (
                (i + 1) in distractor_trials
                and not distractor_displayed
                and isi_timer.getTime() >= jittered / 2 - 0.1
            ):
                draw_grid()
                fixation_cross.draw()
                level_indicator.draw()
                sq = visual.Rect(
                    win, width=100, height=100, fillColor="white", units="pix"
                )
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
        "Average Reaction Time": (
            (total_reaction_time / len(reaction_times)) if reaction_times else 0.0
        ),
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
    Notify the participant of the next task; auto-advance after 5 s or Space.

    Parameters
    ----------
    win : psychopy.visual.Window
        PsychoPy window.
    next_task_name : str
        Name of the upcoming task.

    Returns
    -------
    None
    """
    transition_text = get_text(
        "induction_transition_screen", next_task_name=next_task_name
    )
    transition_message = visual.TextStim(
        win, text=transition_text, color="white", height=24, wrapWidth=750
    )
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


def show_level_change_screen(
    win, task_name, old_level, new_level, is_first_block=False
):
    """
    Announce a change (or continuation) in N-back level for the next block.

    Parameters
    ----------
    win : psychopy.visual.Window
        PsychoPy window.
    task_name : str
        Task label ("Sequential", "Spatial", or "Dual").
    old_level : int
        Previous N-back level.
    new_level : int
        Updated N-back level.
    is_first_block : bool, optional
        Whether this is the first block of the task. Default False.

    Returns
    -------
    None
    """
    # determine phrasing of the level change
    if new_level > old_level:
        change_text = f"increasing from {old_level}-back to {new_level}-back"
    elif new_level < old_level:
        change_text = f"decreasing from {old_level}-back to {new_level}-back"
    else:
        change_text = f"continuing at {old_level}-back"

    # first‐trial notice
    feedback_text = get_text("no_response_needed", n=new_level)

    # status indicators
    seed_status = (
        f"Seed: fixed ({GLOBAL_SEED})" if GLOBAL_SEED is not None else "Seed: random"
    )
    dist_status = "Distractors: ON" if DISTRACTORS_ENABLED else "Distractors: OFF"

    # assemble full on‐screen message
    message = get_text(
        "induction_level_change",
        change_text=change_text,
        new_level=new_level,
        feedback_text=feedback_text,
        seed_status=seed_status,
        dist_status=dist_status,
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
    Log positions of true N-back matches for debugging.

    Parameters
    ----------
    sequence : Sequence
        Stimulus sequence. For dual tasks, a list of (pos, image) pairs.
    n : int
        N-back distance.
    is_dual : bool, optional
        Set True for dual (position+image) matching. Default False.

    Returns
    -------
    None
    """
    if is_dual:
        match_positions = [
            i
            for i in range(n, len(sequence))
            if sequence[i][0] == sequence[i - n][0]
            and sequence[i][1] == sequence[i - n][1]
        ]
    else:
        match_positions = [
            i for i in range(n, len(sequence)) if sequence[i] == sequence[i - n]
        ]

    response_positions = [i - (n - 1) for i in match_positions]

    logging.debug(f"Sequence: {[pos[0] if is_dual else pos for pos in sequence]}")
    logging.debug(f"Positive target positions: {response_positions}")


def adjust_nback_level(
    current_level, accuracy, increase_threshold=82, decrease_threshold=65, max_level=4
):
    """
    Update the N-back level based on accuracy with hysteresis thresholds.

    Parameters
    ----------
    current_level : int
        Current N-back level.
    accuracy : float
        Block accuracy in percent.
    increase_threshold : int, optional
        Accuracy required to increase difficulty. Default 82.
    decrease_threshold : int, optional
        Accuracy threshold to reduce difficulty. Default 65.
    max_level : int, optional
        Maximum allowed N-back level. Default 4.

    Returns
    -------
    int
        New N-back level (bounded to [2, max_level]).
    """
    if accuracy >= increase_threshold and current_level < max_level:
        return current_level + 1
    elif accuracy <= decrease_threshold and current_level > 2:
        return max(2, current_level - 1)  # Ensures level never goes below 2
    else:
        return current_level


def display_spatial_stimulus(win, n_level, highlight_pos=None, feedback_text=None):
    """
    Draw the spatial grid (with optional highlight) and optional feedback.

    Parameters
    ----------
    win : psychopy.visual.Window
        PsychoPy window.
    n_level : int
        Current N-back level (sets grid colour).
    highlight_pos : Optional[int], optional
        Index 0..11 of the radial grid to fill. Default None.
    feedback_text : Optional[str], optional
        Message drawn above the grid in orange. Default None.

    Returns
    -------
    None
    """
    display_grid(
        win,
        highlight_pos=highlight_pos,
        highlight=(highlight_pos is not None),
        n_level=n_level,
    )
    if feedback_text:
        feedback_stim = visual.TextStim(
            win, text=feedback_text, color="orange", height=24, pos=(0, 300)
        )
        feedback_stim.draw()


def run_spatial_nback_block(
    win,
    n,
    num_trials,
    display_duration=1.0,
    isi=1.0,
    is_first_encounter=True,
    block_number=0,
):
    """
    Run one block of the Spatial N-back task on a 12-position radial grid.

    Args:
        win (psychopy.visual.Window): Active PsychoPy window.
        n (int): N-back distance.
        num_trials (int): Number of trials in this block.
        display_duration (float): On-screen time for each stimulus (seconds), jittered.
        isi (float): Base inter-stimulus interval (seconds), jittered.
        is_first_encounter (bool): If True, shows the initial “no response needed” prompt.
        block_number (int): Zero-based block index for logging/messages.

    Returns:
        int: Updated N-back level after performance is evaluated.

    Notes:
        - Draws the grid each trial, highlights the target position,
          and collects responses during the ISI window.
        - Accuracy and lapses from this block determine the next N level.
    """
    positions = generate_positions_with_matches(num_trials, n)
    logging.info(
        f"Block {block_number + 1} timings - Presentation: {display_duration * 1000}ms, ISI: {isi * 1000}ms"
    )

    nback_queue = []
    correct_responses = 0
    incorrect_responses = 0
    lapses = 0
    total_reaction_time = 0
    reaction_times = []
    responses = []
    last_lapse = False

    if is_first_encounter:
        initial_feedback = get_text("no_response_needed", n=n)
        feedback_text = visual.TextStim(
            win, text=initial_feedback, color=get_level_color(n), height=24, pos=(0, 0)
        )
        feedback_text.draw()
        win.flip()
        core.wait(2.0)
        win.flip()
        core.wait(0.5)

    for i, pos in enumerate(positions):
        feedback_text = None
        if last_lapse:
            feedback_text = get_text("lapse_feedback")
            last_lapse = False

        is_target = len(nback_queue) >= n and pos == nback_queue[0]

        # Use the new helper to draw stimulus and optional feedback
        display_spatial_stimulus(win, n, highlight_pos=pos, feedback_text=feedback_text)
        win.flip()
        core.wait(get_jitter(display_duration))

        # Show fixation cross during ISI
        display_spatial_stimulus(win, n)
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
                response = "z" in keys

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
            last_lapse = True

        nback_queue.append(pos)
        if len(nback_queue) > n:
            nback_queue.pop(0)

        event.clearEvents()

    total_responses = correct_responses + incorrect_responses + lapses
    accuracy = (correct_responses / total_responses) * 100 if total_responses > 0 else 0

    return n


def run_dual_nback_block(
    win,
    n,
    num_trials,
    display_duration=1.0,
    isi=1.2,
    is_first_encounter=True,
    block_number=0,
):
    """
    Run one Dual N-back block on a 3×3 grid with image overlays.

    Parameters
    ----------
    win : psychopy.visual.Window
        PsychoPy window.
    n : int
        N-back distance.
    num_trials : int
        Number of trials to present.
    display_duration : float, optional
        Stimulus on-screen time (s), jittered. Default 1.0.
    isi : float, optional
        Base inter-stimulus interval (s), jittered. Default 1.2.
    is_first_encounter : bool, optional
        If True, shows an initial “no response” screen. Default True.
    block_number : int, optional
        Zero-based block index for logging. Default 0.

    Returns
    -------
    int
        Updated N-back level after applying `adjust_nback_level`.

    Notes
    -----
    Draws a grid + outline each trial, highlights the target cell, overlays the
    image, and collects responses during ISI.
    """
    # Add this line here
    logging.info(
        f"Dual N-back Block {block_number + 1} timings - Presentation: {display_duration * 1000}ms, ISI: {isi * 1000}ms"
    )

    positions, images = generate_dual_nback_sequence(num_trials, 3, n, image_files)
    nback_queue = []
    correct_responses = 0
    incorrect_responses = 0
    lapses = 0
    total_reaction_time = 0
    reaction_times = []

    # Create visual elements
    grid, outline = create_grid(win, 3)
    fixation_cross = visual.TextStim(win, text="+", color="white", height=32)
    level_text = visual.TextStim(
        win,
        text=get_text("level_label", n=n),
        color="white",
        height=24,
        pos=(-450, 350),
    )

    # Show initial instructions if first encounter
    if is_first_encounter:
        initial_feedback = get_text("no_response_needed", n=n)
        feedback_text = visual.TextStim(
            win, text=initial_feedback, color=get_level_color(n), height=24, pos=(0, 0)
        )

        # IMPORTANT: Do NOT draw the grid or lines here. Just show the text.
        feedback_text.draw()
        win.flip()
        core.wait(2)  # Wait for 2 seconds (or however long you need)

        # Clear the screen again (blank background) before starting actual trials
        win.flip()
        core.wait(0.5)

    last_lapse = False  # Initialize the flag

    for i, (pos, img) in enumerate(zip(positions, images)):
        # Check the flag at the start of the trial
        if last_lapse:
            lapse_feedback = get_text("lapse_feedback")
            last_lapse = False
        else:
            lapse_feedback = None

        if i >= num_trials:
            break

        is_target = (
            len(nback_queue) >= n
            and pos == nback_queue[-n][0]
            and img == nback_queue[-n][1]
        )

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
            lapse_feedback_stim = visual.TextStim(
                win, text=lapse_feedback, color="orange", height=24, pos=(0, 400)
            )
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

        # Only set the flag to True if a lapse occurs
        if response is None and i >= n:
            lapses += 1
            last_lapse = True

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
    win,
    task_name,
    initial_n,
    num_blocks,
    target_duration,
    run_block_function,
    starting_block_number=0,
):
    """
    Run an adaptive N-back task composed of several sub-blocks.

    Parameters
    ----------
    win : psychopy.visual.Window
        PsychoPy window.
    task_name : str
        Task label (e.g., "Spatial N-back", "Dual N-back").
    initial_n : int
        Starting N-back level.
    num_blocks : int
        Number of main blocks.
    target_duration : float
        Total duration for the whole task (seconds).
    run_block_function : Callable
        Function with signature:
        `(win, n, num_trials, display_duration, isi, is_first_encounter, block_number) -> int`
        returning the (possibly updated) N-back level.
    starting_block_number : int, optional
        Offset for progressive timing across tasks. Default 0.

    Returns
    -------
    None

    Notes
    -----
    Splits each block into 3 sub-blocks computed from `target_duration/num_blocks`.
    """
    n_level = initial_n
    # Loop through main blocks
    for block in range(num_blocks):
        cumulative_block_number = starting_block_number + block
        logging.info(
            f"\nStarting block {cumulative_block_number + 1} of {task_name} with n-back level: {n_level}"
        )

        # Get adjusted timings for the current block
        display_duration, isi = get_progressive_timings(
            task_name, cumulative_block_number
        )

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
                show_level_change_screen(
                    win,
                    task_name,
                    initial_n,
                    n_level,
                    is_first_block=is_first_encounter,
                )
                initial_n = n_level  # Update initial_n to the new level


def show_final_summary(win, seq_nbacks, subjective_measures, n_back_level):
    """
    Paginate and display essential metrics for each Sequential block.

    Parameters
    ----------
    win : psychopy.visual.Window
        PsychoPy window.
    seq_nbacks : List[dict]
        List of results dicts returned by `run_sequential_nback_block`.
    subjective_measures : dict
        Preserved for compatibility; not used in this view.
    n_back_level : int
        N-back level used in the final blocks (for the header text).

    Returns
    -------
    None

    Notes
    -----
    Controls:
    - Space : next page (finish on last page)
    - Backspace : previous page
    - Escape : exit early
    """
    logging.debug("Debug: Entering streamlined show_final_summary")

    # Create a list of summary dictionaries from the results of each sequential block
    summaries = []
    for idx, seq_result in enumerate(seq_nbacks, 1):
        if seq_result:
            summary_data = {
                "Task Name": f"Sequential {n_back_level}-back (Block {idx})",
                "Correct Responses": seq_result.get("Correct Responses", "N/A"),
                "Incorrect Responses": seq_result.get("Incorrect Responses", "N/A"),
                "Lapses": seq_result.get("Lapses", "N/A"),
                "Accuracy": seq_result.get("Accuracy", 0),
                "Average Reaction Time": seq_result.get("Average Reaction Time", 0),
                "D-Prime": seq_result.get("Overall D-Prime", 0),
            }
            summaries.append(summary_data)

    if not summaries:
        logging.warning(
            "No valid sequential block results to display in the final summary."
        )
        return

    # Loop through the summary pages
    current_page = 0
    while True:
        summary = summaries[current_page]

        # Build the text for the current page
        if current_page == len(summaries) - 1:
            controls_text = get_text("induction_final_summary_controls_finish")
        else:
            controls_text = get_text("induction_final_summary_controls_continue")

        full_text = get_text(
            "induction_final_summary_page",
            task_name=summary["Task Name"],
            correct_responses=summary["Correct Responses"],
            incorrect_responses=summary["Incorrect Responses"],
            lapses=summary["Lapses"],
            accuracy=summary["Accuracy"],
            avg_rt=summary["Average Reaction Time"],
            d_prime=summary["D-Prime"],
            current_page=current_page + 1,
            total_pages=len(summaries),
            controls_text=controls_text,
        )

        # Display the summary
        summary_stim = visual.TextStim(
            win, text=full_text, color="white", height=24, wrapWidth=900
        )
        summary_stim.draw()
        win.flip()

        # Wait for key press
        keys = event.waitKeys(keyList=["space", "backspace", "escape"])

        if "space" in keys:
            current_page += 1
            if current_page >= len(summaries):
                break  # Exit loop after the last page
        elif "backspace" in keys:
            current_page = max(0, current_page - 1)  # Go back, but not before page 0
        elif "escape" in keys:
            break  # Exit the summary view early

    logging.debug("Debug: Exiting show_final_summary")


def run_dummy_session(win, n_back_level=2, num_trials=20):
    """
    Run a short (default 20-trial) sequential N-back to verify the setup.

    Parameters
    ----------
    win : psychopy.visual.Window
        PsychoPy window.
    n_back_level : int, optional
        Which N-back to test. Default 2.
    num_trials : int, optional
        Number of trials to run. Default 20.

    Returns
    -------
    None

    Side Effects
    ------------
    - Creates `./data/` if needed.
    - Saves a timestamped CSV: `participant_dummy_n{level}_TestRun_{YYYYMMDD-HHMMSS}.csv`.
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
        text=get_text("dummy_run_instructions"),
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
    Orchestrate the full WAND induction: setup, tasks, measures, and export.

    Responsibilities
    ----------------
    - Gather participant info (ID, N-level, seed, distractors).
    - Run practice, sequential, spatial, and dual phases with transitions.
    - Collect periodic subjective measures.
    - Save per-block and final results to CSV.
    - Display a concise final summary.
    - Handle logging and error conditions.

    Returns
    -------
    None
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
        logging.info(
            f"Starting Sequential {n_back_level}-back PRACTICE/FAMILIARISATION round"
        )
        try:
            familiarisation_text = get_text(
                "induction_practice_intro", n_back_level=n_back_level
            )
            instruction_text = visual.TextStim(
                win, text=familiarisation_text, color="white", height=24, wrapWidth=800
            )
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
            completion_text = get_text("induction_practice_complete")
            completion_stim = visual.TextStim(
                win, text=completion_text, color="white", height=24, wrapWidth=800
            )
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
        logging.info(
            f"Starting Sequential {n_back_level}-back Task - Block 1 (display_duration: 800ms, ISI: 1000ms)"
        )
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
            save_sequential_results(
                participant_id, n_back_level, "Block_1", seq1_results
            )
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
                    w,
                    n,
                    num_trials,
                    display_duration,
                    isi,
                    is_first_encounter,
                    block_number=block_number,
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
                    w,
                    n,
                    num_trials,
                    display_duration,
                    isi,
                    is_first_encounter,
                    block_number=block_number,
                ),
                starting_block_number=dual_block,
            )
            dual_block += 1
        except Exception as e:
            logging.info(f"Error in Dual N-back Task (Block 1): {e}")
            logging.exception("Exception occurred")

        # Sequential N-back Task - Second Block
        logging.info(
            f"Starting Sequential {n_back_level}-back Task - Block 2 (display_duration: 800ms, ISI: 1000ms))"
        )
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
            save_sequential_results(
                participant_id, n_back_level, "Block_2", seq2_results
            )
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
                    w,
                    n,
                    num_trials,
                    display_duration,
                    isi,
                    is_first_encounter,
                    block_number=block_number,
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
                    w,
                    n,
                    num_trials,
                    display_duration,
                    isi,
                    is_first_encounter,
                    block_number=block_number,
                ),
                starting_block_number=spatial_block,
            )
            spatial_block += 1
        except Exception as e:
            logging.info(f"Error in Spatial N-back Task (Block 2): {e}")
            logging.exception("Exception occurred")

        # Sequential N-back Task - Third Block
        logging.info(
            f"Starting Sequential {n_back_level}-back Task - Block 3 (display_duration: 800ms, ISI: 1000ms)"
        )
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
            save_sequential_results(
                participant_id, n_back_level, "Block_3", seq3_results
            )
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
                    w,
                    n,
                    num_trials,
                    display_duration,
                    isi,
                    is_first_encounter,
                    block_number=block_number,
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
                    w,
                    n,
                    num_trials,
                    display_duration,
                    isi,
                    is_first_encounter,
                    block_number=block_number,
                ),
                starting_block_number=dual_block,
            )
            dual_block += 1
        except Exception as e:
            logging.info(f"Error in Dual N-back Task (Block 3): {e}")
            logging.exception("Exception occurred")

        # Sequential N-back Task - Fourth Block
        logging.info(
            f"Starting Sequential {n_back_level}-back Task - Block 4 (display_duration: 800ms, ISI: 1000ms)"
        )
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
            save_sequential_results(
                participant_id, n_back_level, "Block_4", seq4_results
            )
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
                    w,
                    n,
                    num_trials,
                    display_duration,
                    isi,
                    is_first_encounter,
                    block_number=block_number,
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
                    w,
                    n,
                    num_trials,
                    display_duration,
                    isi,
                    is_first_encounter,
                    block_number=block_number,
                ),
                starting_block_number=spatial_block,
            )
            spatial_block += 1
        except Exception as e:
            logging.info(f"Error in Spatial N-back Task (Block 4): {e}")
            logging.exception("Exception occurred")

        # Sequential N-back Task - Fifth Block
        logging.info(
            f"Starting Sequential {n_back_level}-back Task - Block 5 (display_duration: 800ms, ISI: 1000ms)"
        )
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
            save_sequential_results(
                participant_id, n_back_level, "Block_5", seq5_results
            )
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
            results_filename = (
                f"participant_{participant_id}_n{n_back_level}_results.csv"
            )
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
            saved_file_path = save_results_to_csv(
                results_filename, all_results, subjective_measures
            )
            logging.info(f"Results and subjective measures saved to {saved_file_path}")

            final_message = visual.TextStim(
                win,
                text=get_text(
                    "induction_final_message", saved_file_path=saved_file_path
                ),
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
