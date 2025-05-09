#!/usr/bin/env python3
"""
Standalone “dummy” runner for a short Sequential N‑back check.
* Loads the big WAND module just far enough to reuse its functions
* Runs a single Sequential block (default 20 trials)
* Saves a timestamped CSV into ./data/
* Quits.
"""
import argparse
import os
import sys
import time

# --- import ONLY the bits we need from the big script -----------------------
from WAND_full_induction import (base_dir, run_sequential_nback_block,
                                 save_results_to_csv, win)

"""
WAND-Dummy-Run

Dummy run protocol for testing the Sequential task and csv saving function 

Participants complete the Sequential N-back task, number of trials can be adjusted in the script

Requires: PsychoPy, Python 3.8+.

Author: Brodie Mangan
Version: 1.0
"""

# Licensed under the MIT License (see LICENSE file for full text)

# -----------------------------------------------------------------------------


def run_dummy_sequential(n_back_level: int = 2, num_trials: int = 35) -> None:
    """Do the tiny block, save CSV, exit."""
    # 1. run the short block
    results = run_sequential_nback_block(
        win=win,
        n=n_back_level,
        num_images=10,  # pool size – fine for a dummy
        target_percentage=0.5,
        display_duration=0.8,
        isi=1.0,
        num_trials=num_trials,
        is_first_encounter=True,
        block_number=0,
    )

    # 2. save to ./data/
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

    # 3. tell the user where the file went
    print(f"\n✅  Dummy sequential finished.  CSV saved to:\n   {csv_path}\n")

    # 4. shut PsychoPy down cleanly
    win.close()
    sys.exit(0)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Quick dummy Sequential N‑back test")
    parser.add_argument("--level", type=int, default=2, help="N‑back level (default 2)")
    parser.add_argument("--trials", type=int, default=20, help="Number of trials (default 20)")
    args = parser.parse_args()

    run_dummy_sequential(n_back_level=args.level, num_trials=args.trials)
