#!/usr/bin/env python3
"""
WAND-Practice-SeqQuick

Run *blocks* × *trials* Sequential N-back practice blocks, log each block
with `log_seq_block`, show a brief summary, then quit.

The script first imports the full practice module.  If that module has
already created `practice.win`, the same window is re-used; otherwise one
new PsychoPy window is opened.  No duplicate window can appear.

Typical use
-----------
# default: 2 blocks × 10 trials, 2-back, windowed
python seq_quick.py

# 3 blocks × 12 trials, 3-back, fullscreen
python seq_quick.py --blocks 3 --trials 12 --level 3 --mode fullscreen
"""

import argparse
import importlib
import os
import time
from typing import List, Tuple

from psychopy import core, event, visual


# ──────────────────────────────────────────────────────────────
#  Helper functions
# ──────────────────────────────────────────────────────────────
def build_window(fullscreen: bool) -> visual.Window:
    """
    Create a new PsychoPy window.

    Args:
        fullscreen (bool): If ``True`` open a full-screen window;
            otherwise a resizable window.

    Returns:
        visual.Window: The created window.
    """
    return visual.Window(fullscr=fullscreen, color="black", units="pix")


def run_block(
    practice,
    n_level: int,
    num_trials: int,
    block_no: int,
) -> Tuple[float, int, int, float]:
    """
    Execute one Sequential N-back block and write a CSV row.

    Args:
        practice (module): Already imported practice module.
        n_level (int): N-back level; 2 or 3.
        num_trials (int): Trials in this block.
        block_no (int): Counter used in the CSV file.

    Returns:
        tuple:
            accuracy (float): Percent correct;
            errors (int): Wrong key presses;
            lapses (int): Missed responses;
            avg_rt (float): Mean reaction time in seconds.
    """
    accuracy, errors, lapses, avg_rt = practice.run_sequential_nback_practice(
        n=n_level,
        num_trials=num_trials,
        display_duration=0.8,
        isi=1.0,
    )
    practice.log_seq_block(n_level, block_no, accuracy, errors, lapses)
    return accuracy, errors, lapses, avg_rt


def show_summary(
    win: visual.Window,
    block_no: int,
    total_blocks: int,
    n_level: int,
    num_trials: int,
    accuracy: float,
    errors: int,
    lapses: int,
    avg_rt: float,
) -> None:
    """Displays an on-screen summary of the most recently completed block.

    Presents key performance metrics such as accuracy, errors, lapses, and
    mean reaction time. The screen waits for a key press before proceeding.

    Args:
        win (visual.Window): The PsychoPy window to draw the summary on.
        block_no (int): The index of the block that just finished (1-based).
        total_blocks (int): The total number of blocks scheduled for the run.
        n_level (int): The N-back level of the completed block.
        num_trials (int): The number of trials in the completed block.
        accuracy (float): The accuracy percentage for the block.
        errors (int): The total number of incorrect key presses.
        lapses (int): The total number of missed responses.
        avg_rt (float): The mean reaction time for correct responses in seconds.
    """
    prompt = "continue" if block_no < total_blocks else "quit"
    txt = (
        f"Block {block_no}/{total_blocks}   |   {n_level}-back   |   "
        f"{num_trials} trials\n\n"
        f"Accuracy: {accuracy:.1f}%\n"
        f"Errors:   {errors}\n"
        f"Lapses:   {lapses}\n"
        f"Mean RT:  {avg_rt:.2f} s\n\n"
        f"Press any key to {prompt}"
    )
    visual.TextStim(win, text=txt, color="white", height=24, wrapWidth=800).draw()
    win.flip()
    event.waitKeys()


# ──────────────────────────────────────────────────────────────
#  Main routine
# ──────────────────────────────────────────────────────────────
def main() -> None:
    """Parses command-line arguments and runs a series of Sequential N-back blocks.

    This function serves as the main entry point. It handles:
    1.  Parsing all command-line arguments.
    2.  Importing the specified practice module.
    3.  Setting up the PsychoPy window and necessary global variables.
    4.  Looping through the requested number of blocks.
    5.  Displaying a summary after each block.
    6.  Ensuring a clean exit and printing a confirmation message with the
        path to the saved data.
    """
    parser = argparse.ArgumentParser(
        description="Run quick Sequential N-back smoke test"
    )
    parser.add_argument(
        "--module", default="WAND_practice_plateau", help="Practice module to import"
    )
    parser.add_argument(
        "--level", type=int, default=2, choices=[2, 3], help="N-back level"
    )
    parser.add_argument("--blocks", type=int, default=2, help="Number of blocks")
    parser.add_argument("--trials", type=int, default=10, help="Trials per block")
    parser.add_argument(
        "--pid", default="seqQuick", help="Participant ID used in the CSV"
    )
    parser.add_argument(
        "--mode",
        choices=["windowed", "fullscreen"],
        default="windowed",
        help="Display mode",
    )
    args = parser.parse_args()

    # 1; import the practice module
    practice = importlib.import_module(args.module)

    # 2; set up logging globals
    practice.PARTICIPANT_ID = args.pid
    practice.CSV_PATH = os.path.join(
        practice.data_dir, f"seq_{practice.PARTICIPANT_ID}.csv"
    )
    practice._last_logged_level = None

    # 3; window handling; reuse if already present
    if hasattr(practice, "win") and practice.win:
        win = practice.win  # reuse existing window
    else:
        win = build_window(fullscreen=(args.mode == "fullscreen"))
        practice.win = win
        practice.grid_lines = practice.create_grid_lines(practice.win)

    # 4; disable distractors for a smoke test
    practice.DISTRACTORS_ENABLED = False

    # 5; run the requested blocks
    for block_no in range(1, args.blocks + 1):
        acc, errs, lapses, rt = run_block(
            practice,
            n_level=args.level,
            num_trials=args.trials,
            block_no=block_no,
        )
        show_summary(
            win, block_no, args.blocks, args.level, args.trials, acc, errs, lapses, rt
        )

    # 6; clean exit
    win.close()
    core.quit()
    stamp = time.strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{stamp}] {args.blocks} rows saved to {practice.CSV_PATH}")


if __name__ == "__main__":
    main()
