#!/usr/bin/env python3
"""
WAND Quicktest - Practice

Automated smoke test for the Practice script (wand_nback/practice_plateau.py).

Usage:
    python Tests/quicktest_practice.py --quicktest   # Automated (no input)
    python Tests/quicktest_practice.py               # Manual demo

Output:
    - Console: PASS/FAIL summary
    - CSV: data/seq_quicktest.csv
    - Markdown: Tests/results/quicktest_practice_report.md

Author: Brodie Mangan
Version: 1.1.3
License: MIT
"""

import argparse
import importlib
import os
import random
import sys
import time
from datetime import datetime
from typing import Tuple

# =============================================================================
# SETUP PATHS (for running from Tests/ folder)
# =============================================================================

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(SCRIPT_DIR)
RESULTS_DIR = os.path.join(SCRIPT_DIR, "results")

# Add project root to path so we can import WAND modules
sys.path.insert(0, PROJECT_DIR)

# Ensure results directory exists
os.makedirs(RESULTS_DIR, exist_ok=True)

# =============================================================================
# ARGUMENT PARSING (must happen before conditional mocking)
# =============================================================================

_parser = argparse.ArgumentParser(description="WAND Practice Quicktest")
_parser.add_argument(
    "--module", default="wand_nback.practice_plateau", help="Practice module"
)
_parser.add_argument(
    "--level", type=int, default=2, choices=[2, 3], help="N-back level"
)
_parser.add_argument("--blocks", type=int, default=2, help="Number of blocks")
_parser.add_argument("--trials", type=int, default=10, help="Trials per block")
_parser.add_argument("--pid", default="seqQuick", help="Participant ID for CSV")
_parser.add_argument("--mode", choices=["windowed", "fullscreen"], default="windowed")
_parser.add_argument(
    "--quicktest",
    action="store_true",
    help="Run automated smoke test (no human input, fast timings)",
)
_args = _parser.parse_args()

# =============================================================================
# CONDITIONAL MOCKING FOR QUICKTEST MODE
# =============================================================================

QUICKTEST_DISPLAY = 0.05
QUICKTEST_ISI = 0.05

if _args.quicktest:
    print("[QUICKTEST] Automated practice smoke test mode enabled")
    print("[QUICKTEST] Patching PsychoPy event functions...")

    from psychopy import core, event

    def mock_waitKeys(keyList=None, maxWait=float("inf"), *a, **kw):
        """Mock replacement - returns random key immediately."""
        core.wait(0.001)
        if keyList is None:
            keyList = ["space"]
        safe_keys = [k for k in keyList if k != "escape"]
        if not safe_keys:
            safe_keys = ["space"]
        return [random.choice(safe_keys)]

    def mock_getKeys(keyList=None, *a, **kw):
        """Mock replacement - 40% chance of keypress."""
        if keyList is None:
            return []
        safe_keys = [k for k in keyList if k != "escape"]
        if not safe_keys:
            return []
        if random.random() < 0.4:
            return [random.choice(safe_keys)]
        return []

    event.waitKeys = mock_waitKeys
    event.getKeys = mock_getKeys

    random.seed(12345)
    _args.blocks = 1
    _args.trials = 10
    _args.pid = "quicktest"

    print("[QUICKTEST] PsychoPy event functions patched successfully")
    print(f"[QUICKTEST] Using {_args.trials} trials with {QUICKTEST_DISPLAY}s timings")

# =============================================================================
# IMPORT PSYCHOPY (after potential mocking)
# =============================================================================

from psychopy import core, event, visual


def build_window(fullscreen: bool) -> visual.Window:
    """Create a new PsychoPy window."""
    return visual.Window(fullscr=fullscreen, color="black", units="pix")


def run_block(
    practice,
    n_level: int,
    num_trials: int,
    block_no: int,
    display_duration: float = 0.8,
    isi: float = 1.0,
) -> Tuple[float, int, int, float]:
    """Execute one Sequential N-back block and write a CSV row."""
    accuracy, errors, lapses, avg_rt = practice.run_sequential_nback_practice(
        n=n_level,
        num_trials=num_trials,
        display_duration=display_duration,
        isi=isi,
    )
    practice.log_seq_block(n_level, block_no, accuracy, errors, lapses)
    return accuracy, errors, lapses, avg_rt


def generate_markdown_report(
    accuracy: float,
    errors: int,
    lapses: int,
    avg_rt: float,
    elapsed: float,
    csv_path: str,
) -> str:
    """Generate markdown report content."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    status = "PASSED"

    report = f"""# WAND Quicktest Report - Practice

**Generated:** {timestamp}  
**Status:** {status}

## Test Configuration

| Parameter | Value |
|-----------|-------|
| N-back Level | {_args.level} |
| Trials | {_args.trials} |
| Blocks | {_args.blocks} |
| Display Duration | {QUICKTEST_DISPLAY}s |
| ISI | {QUICKTEST_ISI}s |

## Results

| Metric | Value |
|--------|-------|
| Accuracy | {accuracy:.1f}% |
| Errors | {errors} |
| Lapses | {lapses} |
| Avg RT | {avg_rt:.3f}s |

## Execution

| Metric | Value |
|--------|-------|
| Time Elapsed | {elapsed:.2f}s |
| CSV Output | `{csv_path}` |

## Conclusion

Your WAND Practice installation is working correctly.
"""
    return report


def main() -> None:
    """Run the practice quicktest."""
    start_time = time.time()
    args = _args

    # Import the practice module
    practice = importlib.import_module(args.module)

    # Set up logging globals
    practice.PARTICIPANT_ID = args.pid
    practice.CSV_PATH = os.path.join(
        practice.data_dir, f"seq_{practice.PARTICIPANT_ID}.csv"
    )
    practice._last_logged_level = None

    # Window handling
    if hasattr(practice, "win") and practice.win:
        win = practice.win
    else:
        win = build_window(fullscreen=(args.mode == "fullscreen"))
        practice.win = win
        practice.grid_lines = practice.create_grid_lines(practice.win)

    # Disable distractors for smoke test
    practice.DISTRACTORS_ENABLED = False

    # Set timing based on quicktest mode
    if args.quicktest:
        display_dur = QUICKTEST_DISPLAY
        isi = QUICKTEST_ISI
    else:
        display_dur = 0.8
        isi = 1.0

    # Run the blocks
    all_results = []
    for block_no in range(1, args.blocks + 1):
        acc, errs, lapses, rt = run_block(
            practice,
            n_level=args.level,
            num_trials=args.trials,
            block_no=block_no,
            display_duration=display_dur,
            isi=isi,
        )
        all_results.append((acc, errs, lapses, rt))

    # Clean exit
    win.close()

    elapsed = time.time() - start_time

    # Output summary
    if args.quicktest:
        acc, errs, lapses, rt = all_results[0]
        print("\n" + "=" * 60)
        print("QUICKTEST PASSED")
        print("=" * 60)
        print(f"\nResults:")
        print(f"  - Accuracy: {acc:.1f}%")
        print(f"  - Errors: {errs}")
        print(f"  - Lapses: {lapses}")
        print(f"  - Avg RT: {rt:.3f}s")
        print(f"\n  - Time elapsed: {elapsed:.2f}s")
        print(f"  - CSV saved to: {practice.CSV_PATH}")

        # Generate and save markdown report
        report = generate_markdown_report(
            acc, errs, lapses, rt, elapsed, practice.CSV_PATH
        )
        report_path = os.path.join(RESULTS_DIR, "quicktest_practice_report.md")
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(report)
        print(f"  - Report saved to: {report_path}")

        print("\nYour WAND Practice installation is working correctly!\n")
    else:
        stamp = time.strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{stamp}] {args.blocks} rows saved to {practice.CSV_PATH}")

    core.quit()


if __name__ == "__main__":
    main()
