#!/usr/bin/env python3
"""
WAND-Dummy-Run

Standalone runner for a short Sequential N-back check using the WAND suite.

- Loads selected functions from the main WAND induction module
- Runs a single Sequential N-back block (default: 2-back, 35 trials)
- Saves a timestamped CSV into ./data/
- Quits cleanly

Use this script to verify task logic, display settings, and data output.

Quicktest Mode (--quicktest):
- Mocks keyboard input (no human interaction required)
- Uses fast timings (0.05s display, 0.05s ISI)
- Runs 10 trials in ~5 seconds
- Verifies PsychoPy installation works without crashing

Author: Brodie Mangan
Version: 1.1.0
License: MIT
Requires: PsychoPy ≥ 2024.2.1, Python 3.8+
"""

import argparse
import os
import random
import sys
import time

# =============================================================================
# ARGUMENT PARSING (must happen before conditional mocking)
# =============================================================================

parser = argparse.ArgumentParser(description="Quick dummy Sequential N‑back test")
parser.add_argument("--level", type=int, default=2, help="N‑back level (default = 2)")
parser.add_argument(
    "--trials", type=int, default=35, help="Number of trials (default = 35)"
)
parser.add_argument(
    "--quicktest",
    action="store_true",
    help="Run automated smoke test (no human input required, fast timings)",
)
args = parser.parse_args()

# =============================================================================
# CONDITIONAL MOCKING FOR QUICKTEST MODE
# =============================================================================
# This MUST happen before importing WAND modules which import psychopy

QUICKTEST_DISPLAY = 0.05
QUICKTEST_ISI = 0.05

if args.quicktest:
    print("[QUICKTEST] Automated smoke test mode enabled")
    print("[QUICKTEST] Patching PsychoPy event functions...")

    from psychopy import core, event

    _original_waitKeys = event.waitKeys
    _original_getKeys = event.getKeys

    def mock_waitKeys(keyList=None, maxWait=float("inf"), *args, **kwargs):
        """
        Mock replacement for event.waitKeys.
        Returns a random key from keyList immediately without waiting.
        """
        core.wait(0.001)

        if keyList is None:
            keyList = ["space"]

        safe_keys = [k for k in keyList if k != "escape"]
        if not safe_keys:
            safe_keys = ["space"]

        return [random.choice(safe_keys)]

    def mock_getKeys(keyList=None, *args, **kwargs):
        """
        Mock replacement for event.getKeys.
        Simulates ~40% chance of a keypress (realistic response rate).
        """
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
    args.trials = 10

    print("[QUICKTEST] PsychoPy event functions patched successfully")
    print(
        f"[QUICKTEST] Using {args.trials} trials with {QUICKTEST_DISPLAY}s display, {QUICKTEST_ISI}s ISI"
    )

# =============================================================================
# IMPORT WAND MODULES (after potential mocking)
# =============================================================================

from WAND_full_induction import (
    base_dir,
    run_sequential_nback_block,
    save_results_to_csv,
    win,
)


def run_dummy_sequential(
    n_back_level: int = 2, num_trials: int = 35, quicktest: bool = False
) -> None:
    """
    Run a short dummy Sequential N-back block for test/demo purposes.

    This function uses the main WAND task logic to execute a brief Sequential N-back task
    using a small stimulus pool. It saves the results to a timestamped CSV file in the
    `/data/` directory and then exits cleanly.

    Args:
        n_back_level (int, optional): The N-back level to test (default = 2).
        num_trials (int, optional): Number of trials to run (default = 35).
        quicktest (bool, optional): If True, use fast timings for automated testing.

    Side effects:
        - Runs a PsychoPy visual window task.
        - Saves a CSV file named `dummySeq_n{level}_{timestamp}.csv` to `/data/`.
        - Prints file location to console.
        - Closes the PsychoPy window and exits the script.

    Raises:
        SystemExit: Always exits after completion.
    """
    if quicktest:
        display_duration = QUICKTEST_DISPLAY
        isi = QUICKTEST_ISI
        print(f"[QUICKTEST] Running {num_trials}-trial block...")
    else:
        display_duration = 0.8
        isi = 1.0

    start_time = time.time()

    # 1. Run the block
    results = run_sequential_nback_block(
        win=win,
        n=n_back_level,
        num_images=10,
        target_percentage=0.5,
        display_duration=display_duration,
        isi=isi,
        num_trials=num_trials,
        is_first_encounter=True,
        block_number=0,
    )

    # 2. Save results
    timestamp = time.strftime("%Y%m%d-%H%M%S")

    if quicktest:
        fname = f"quicktest_{timestamp}.csv"
        participant_id = "quicktest"
        block_name = "quicktest"
    else:
        fname = f"dummySeq_n{n_back_level}_{timestamp}.csv"
        participant_id = "dummySeq"
        block_name = "dummy"

    data_row = [
        {
            "Participant ID": participant_id,
            "Task": f"Sequential {n_back_level}-back",
            "Block": block_name,
            "N-back Level": n_back_level,
            "Results": results,
        }
    ]
    csv_path = save_results_to_csv(fname, data_row)

    elapsed = time.time() - start_time

    # 3. Notify user
    if quicktest:
        print("\n" + "=" * 60)
        print("QUICKTEST PASSED")
        print("=" * 60)
        print(f"\nResults:")
        print(f"  - Accuracy: {results.get('Accuracy', 'N/A'):.1f}%")
        print(f"  - Correct: {results.get('Correct Responses', 'N/A')}")
        print(f"  - Incorrect: {results.get('Incorrect Responses', 'N/A')}")
        print(f"  - Lapses: {results.get('Lapses', 'N/A')}")
        print(f"  - D-Prime: {results.get('Overall D-Prime', 'N/A'):.3f}")
        print(f"\n  - Time elapsed: {elapsed:.2f}s")
        print(f"  - CSV saved to: {csv_path}")
        print("\nYour WAND installation is working correctly!\n")
    else:
        print(f"\n✅  Dummy Sequential N-back finished. CSV saved to:\n   {csv_path}\n")

    # 4. Exit
    win.close()
    sys.exit(0)


if __name__ == "__main__":
    run_dummy_sequential(
        n_back_level=args.level, num_trials=args.trials, quicktest=args.quicktest
    )
