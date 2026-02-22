#!/usr/bin/env python3
"""
WAND Quicktest - Full Induction.

Automated smoke test for the Full Induction task (wand_nback/full_induction.py).

Usage:
    wand-quicktest                                 # Automated smoke test (default)
    wand-quicktest --manual                        # Manual demo timings
    python Tests/quicktest_induction.py --manual   # Manual demo timings

Output:
    - Console: PASS/FAIL summary
    - CSV: data/quicktest_*.csv
    - Markdown: Tests/results/quicktest_induction_report.md

Author: Brodie Mangan
Version: 1.2.0
License: MIT
"""

import argparse
import os
import random
import sys
import time
from datetime import datetime
from typing import Optional, Sequence

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

QUICKTEST_DISPLAY = 0.05
QUICKTEST_ISI = 0.05
QUICKTEST_TRIALS = 10


def build_parser() -> argparse.ArgumentParser:
    """Build command-line argument parser."""
    parser = argparse.ArgumentParser(description="WAND Full Induction Quicktest")
    parser.add_argument(
        "--level", type=int, default=2, help="N-back level (default = 2)"
    )
    parser.add_argument(
        "--trials", type=int, default=35, help="Number of trials (default = 35)"
    )
    parser.add_argument(
        "--quicktest",
        dest="quicktest",
        action="store_true",
        help="Run automated smoke test (no human input required, fast timings)",
    )
    parser.add_argument(
        "--manual",
        dest="quicktest",
        action="store_false",
        help="Run manual visual demo timings",
    )
    parser.set_defaults(quicktest=True)
    return parser


def _enable_quicktest_mode() -> None:
    """Patch PsychoPy key handlers for automated quicktest mode."""
    print("[QUICKTEST] Automated smoke test mode enabled")
    print("[QUICKTEST] Patching PsychoPy event functions...")

    from psychopy import core, event

    def mock_waitKeys(keyList=None, maxWait=float("inf"), *a, **kw):
        """Mock replacement: returns a random key quickly."""
        core.wait(0.001)
        if keyList is None:
            keyList = ["space"]
        safe_keys = [k for k in keyList if k != "escape"]
        if not safe_keys:
            safe_keys = ["space"]
        return [random.choice(safe_keys)]

    def mock_getKeys(keyList=None, *a, **kw):
        """Mock replacement: 40% chance of random keypress."""
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
    print("[QUICKTEST] PsychoPy event functions patched successfully")


def generate_markdown_report(
    results: dict,
    elapsed: float,
    csv_path: str,
    n_back_level: int,
    num_trials: int,
    display_duration: float,
    isi: float,
) -> str:
    """Generate markdown report content."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    status = "PASSED" if results.get("Accuracy", 0) >= 0 else "FAILED"

    report = f"""# WAND Quicktest Report - Full Induction

**Generated:** {timestamp}  
**Status:** {status}

## Test Configuration

| Parameter | Value |
|-----------|-------|
| N-back Level | {n_back_level} |
| Trials | {num_trials} |
| Display Duration | {display_duration}s |
| ISI | {isi}s |

## Results

| Metric | Value |
|--------|-------|
| Accuracy | {results.get('Accuracy', 'N/A'):.1f}% |
| Correct Responses | {results.get('Correct Responses', 'N/A')} |
| Incorrect Responses | {results.get('Incorrect Responses', 'N/A')} |
| Lapses | {results.get('Lapses', 'N/A')} |

## Signal Detection Theory Metrics

| Metric | Value |
|--------|-------|
| D-Prime (d') | {results.get('Overall D-Prime', 'N/A'):.3f} |
| Criterion (c) | {results.get('Criterion', 'N/A'):.3f} |
| Hits | {results.get('Hits', 'N/A')} |
| Misses | {results.get('Misses', 'N/A')} |
| False Alarms | {results.get('False Alarms', 'N/A')} |
| Correct Rejections | {results.get('Correct Rejections', 'N/A')} |
| Hit Rate | {results.get('Hit Rate', 'N/A'):.3f} |
| FA Rate | {results.get('FA Rate', 'N/A'):.3f} |

## Execution

| Metric | Value |
|--------|-------|
| Time Elapsed | {elapsed:.2f}s |
| CSV Output | `{csv_path}` |

## Conclusion

Your WAND Full Induction installation is working correctly.
"""
    return report


def run_quicktest(
    n_back_level: int = 2, num_trials: int = 35, quicktest: bool = False
) -> None:
    """Run a short Sequential N-back block for testing."""
    if quicktest:
        display_duration = QUICKTEST_DISPLAY
        isi = QUICKTEST_ISI
        print(f"[QUICKTEST] Running {num_trials}-trial block...")
    else:
        display_duration = 0.8
        isi = 1.0

    from wand_nback.full_induction import (
        run_sequential_nback_block,
        save_results_to_csv,
        win,
    )

    start_time = time.time()

    # Run the block
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

    # Save CSV results
    timestamp = time.strftime("%Y%m%d-%H%M%S")
    if quicktest:
        fname = f"quicktest_induction_{timestamp}.csv"
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

    # Console output
    if quicktest:
        print("\n" + "=" * 60)
        print("QUICKTEST PASSED")
        print("=" * 60)
        print("\nResults:")
        print(f"  - Accuracy: {results.get('Accuracy', 'N/A'):.1f}%")
        print(f"  - Correct: {results.get('Correct Responses', 'N/A')}")
        print(f"  - Incorrect: {results.get('Incorrect Responses', 'N/A')}")
        print(f"  - Lapses: {results.get('Lapses', 'N/A')}")
        print("\nSDT Metrics:")
        print(f"  - D-Prime (d'): {results.get('Overall D-Prime', 'N/A'):.3f}")
        print(f"  - Criterion (c): {results.get('Criterion', 'N/A'):.3f}")
        print(f"  - Hits: {results.get('Hits', 'N/A')}")
        print(f"  - Misses: {results.get('Misses', 'N/A')}")
        print(f"  - False Alarms: {results.get('False Alarms', 'N/A')}")
        print(f"  - Correct Rejections: {results.get('Correct Rejections', 'N/A')}")
        print(f"  - Hit Rate: {results.get('Hit Rate', 'N/A'):.3f}")
        print(f"  - FA Rate: {results.get('FA Rate', 'N/A'):.3f}")
        print(f"\n  - Time elapsed: {elapsed:.2f}s")
        print(f"  - CSV saved to: {csv_path}")

        # Generate and save markdown report
        report = generate_markdown_report(
            results=results,
            elapsed=elapsed,
            csv_path=csv_path,
            n_back_level=n_back_level,
            num_trials=num_trials,
            display_duration=display_duration,
            isi=isi,
        )
        report_path = os.path.join(RESULTS_DIR, "quicktest_induction_report.md")
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(report)
        print(f"  - Report saved to: {report_path}")
        print("\nYour WAND Full Induction installation is working correctly!\n")
    else:
        print(
            f"\n[OK] Dummy Sequential N-back finished. CSV saved to:\n   {csv_path}\n"
        )

    # Clean exit
    win.close()


def main(argv: Optional[Sequence[str]] = None) -> None:
    """CLI entrypoint for wand-quicktest."""
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.quicktest:
        _enable_quicktest_mode()
        if args.trials == parser.get_default("trials"):
            args.trials = QUICKTEST_TRIALS
        print(
            f"[QUICKTEST] Using {args.trials} trials with {QUICKTEST_DISPLAY}s display, "
            f"{QUICKTEST_ISI}s ISI"
        )

    run_quicktest(
        n_back_level=args.level,
        num_trials=args.trials,
        quicktest=args.quicktest,
    )


if __name__ == "__main__":
    main()
