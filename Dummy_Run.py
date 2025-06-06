#!/usr/bin/env python3
"""
WAND-Dummy-Run

Standalone runner for a short Sequential N-back check using the WAND suite.

- Loads selected functions from the main WAND induction module
- Runs a single Sequential N-back block (default: 2-back, 35 trials)
- Saves a timestamped CSV into ./data/
- Quits cleanly

Use this script to verify task logic, display settings, and data output.

Author: Brodie Mangan
Version: 1.0.0
License: MIT
Requires: PsychoPy ≥ 2024.2.1, Python 3.8+
"""

import argparse
import os
import sys
import time

# Import required functions and constants from the main induction script
from WAND_full_induction import base_dir, run_sequential_nback_block, save_results_to_csv, win


def run_dummy_sequential(n_back_level: int = 2, num_trials: int = 35) -> None:
    """
    Run a short dummy Sequential N-back block for test/demo purposes.

    This function uses the main WAND task logic to execute a brief Sequential N-back task
    using a small stimulus pool. It saves the results to a timestamped CSV file in the
    `/data/` directory and then exits cleanly.

    Args:
        n_back_level (int, optional): The N-back level to test (default = 2).
        num_trials (int, optional): Number of trials to run (default = 35).

    Side effects:
        - Runs a PsychoPy visual window task.
        - Saves a CSV file named `dummySeq_n{level}_{timestamp}.csv` to `/data/`.
        - Prints file location to console.
        - Closes the PsychoPy window and exits the script.

    Raises:
        SystemExit: Always exits after completion.
    """
    # 1. Run the block
    results = run_sequential_nback_block(
        win=win,
        n=n_back_level,
        num_images=10,
        target_percentage=0.5,
        display_duration=0.8,
        isi=1.0,
        num_trials=num_trials,
        is_first_encounter=True,
        block_number=0,
    )

    # 2. Save results
    timestamp = time.strftime("%Y%m%d-%H%M%S")
    fname = f"dummySeq_n{n_back_level}_{timestamp}.csv"
    data_row = [
        {
            "Participant ID": "dummySeq",
            "Task": f"Sequential {n_back_level}-back",
            "Block": "dummy",
            "Results": results,
        }
    ]
    csv_path = save_results_to_csv(fname, data_row)

    # 3. Notify user
    print(f"\n✅  Dummy Sequential N-back finished. CSV saved to:\n   {csv_path}\n")

    # 4. Exit
    win.close()
    sys.exit(0)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Quick dummy Sequential N‑back test")
    parser.add_argument("--level", type=int, default=2, help="N‑back level (default = 2)")
    parser.add_argument("--trials", type=int, default=35, help="Number of trials (default = 35)")
    args = parser.parse_args()

    run_dummy_sequential(n_back_level=args.level, num_trials=args.trials)
