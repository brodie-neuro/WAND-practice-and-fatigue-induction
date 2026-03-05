#!/usr/bin/env python3
"""
WAND Quicktest - Edge Case Warnings (Auto-Terminate)

Automated test simulating a participant who makes NO RESPONSES across 2 short blocks.
This demonstrates the Performance Monitor natively stepping in:
- Block 1: Trigger 1st Flag (warn_then_terminate) -> Prints encouraging warning.
- Block 2: Trigger 2nd Flag (warn_then_terminate) -> Auto-terminates session.

Usage:
    py -3.10 Tests/quicktest_edgecase.py
"""

import os
import sys
import time

# =============================================================================
# SETUP PATHS
# =============================================================================
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(SCRIPT_DIR)
sys.path.insert(0, PROJECT_DIR)

# Import PSYCHOPY and WAND dependencies
from psychopy import core, event, visual

from wand_nback.common import load_config
from wand_nback.performance_monitor import (
    MonitorConfig,
    check_sequential_block,
    handle_flag,
    reset_flag_count,
)


def _enable_no_response_mode() -> None:
    """Patch PsychoPy key handlers to simulate a non-responsive participant."""
    print("[QUICKTEST] Simulating participant with NO RESPONSES (100% lapses)...")

    def mock_waitKeys(keyList=None, maxWait=float("inf"), *a, **kw):
        """Mock replacement: waits a bit so screens can be read, then proceeds."""
        core.wait(2.5)
        return ["space"]

    def mock_getKeys(keyList=None, *a, **kw):
        """Mock replacement: always returns no keys."""
        return []

    event.waitKeys = mock_waitKeys
    event.getKeys = mock_getKeys


def run_edgecase_test():
    _enable_no_response_mode()
    load_config()  # Load text dict for participant-facing warnings
    reset_flag_count()  # Ensure clean state

    # Configure our performance monitor explicitly
    monitor_cfg = MonitorConfig(
        enabled=True,
        dprime_threshold=1.0,
        missed_response_threshold=0.20,
        action="warn_then_terminate",
    )

    from wand_nback.full_induction import run_sequential_nback_block, win

    # We will run up to 2 blocks. The second should terminate the loop.
    for block_num in [1, 2]:
        print(f"\n--- Starting Block {block_num} ---")

        # Run a very short block (10 trials, incredibly fast display so test doesn't drag)
        results = run_sequential_nback_block(
            win=win,
            n=2,
            num_images=10,
            target_percentage=0.5,
            display_duration=0.05,
            isi=0.05,
            num_trials=10,
            is_first_encounter=(block_num == 1),
            block_number=block_num,
        )

        print(f"[Block {block_num}] Finished! Calculating Metrics...")
        print("\n=== BLOCK RESULTS ===")
        print(f"  - D-Prime (d'): {results.get('Overall D-Prime', 0.0):.3f}")
        print(f"  - Criterion (c): {results.get('Criterion', 0.0):.3f}")
        print(f"  - Hits/Misses: {results.get('Hits', 0)} / {results.get('Misses', 0)}")
        print(
            f"  - FA/CR: {results.get('False Alarms', 0)} / {results.get('Correct Rejections', 0)}"
        )
        print(f"  - Lapses: {results.get('Lapses', 0)} / 10")
        print("=====================\n")

        # Pass results to Performance Monitor
        check = check_sequential_block(results, block_num, monitor_cfg)

        if check.flagged:
            print(f"[Monitor] Flagged! Triggering handle_flag...")

            # handle_flag handles the participant alert internally and returns 'terminate' if limit reached
            decision = handle_flag(
                win, "Sequential 2-back", block_num, check, monitor_cfg, n_back_level=2
            )

            print(f"[Monitor] Decision rendered: '{decision}'")
            if decision == "terminate":
                print("\n" + "=" * 50)
                print(">>> PERFORMANCE WARNING 2: AUTO-TERMINATION <<<")
                print(">>> SESSION STOPPED SUCCESSFULLY            <<<")
                print("=" * 50 + "\n")
                # Break out of loop to mimic full_induction.py behavior
                break

    print("\nEdge Case Warning test completed successfully. Cleaning up.")
    win.close()
    core.quit()


if __name__ == "__main__":
    run_edgecase_test()
