import json
import os
import sys
from math import isclose

import pytest

# Ensure we can import modules from the main folder
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from wand_analysis import (
    calculate_A_prime,
    calculate_accuracy_and_rt,
    calculate_dprime,
    summarise_sequential_block,
)

# --- LOGGING HELPER ---
# This allows us to save the "evidence" to a file
LOG_FILE = "test_results_detailed.txt"


def log_evidence(test_name, input_desc, expected, actual, status):
    with open(LOG_FILE, "a") as f:
        f.write(f"TEST: {test_name}\n")
        f.write(f"  INPUT:    {input_desc}\n")
        f.write(f"  EXPECTED: {expected}\n")
        f.write(f"  ACTUAL:   {actual}\n")
        f.write(f"  STATUS:   {status}\n")
        f.write("-" * 50 + "\n")


# Clear the log file at the start of the run
@pytest.hookimpl(tryfirst=True)
def pytest_sessionstart(session):
    with open(LOG_FILE, "w") as f:
        f.write("=== WAND BEHAVIOURAL METRICS TEST EVIDENCE ===\n\n")


# --- TEST DATA FIXTURES ---


@pytest.fixture
def perfect_data():
    """Returns a list of trials where the user got everything 100% right."""
    return [
        {
            "Trial": 1,
            "Is Target": True,
            "Response": "match",
            "Reaction Time": 0.5,
            "Accuracy": True,
        },
        {
            "Trial": 2,
            "Is Target": True,
            "Response": "match",
            "Reaction Time": 0.5,
            "Accuracy": True,
        },
        {
            "Trial": 3,
            "Is Target": False,
            "Response": "non-match",
            "Reaction Time": 0.5,
            "Accuracy": True,
        },
        {
            "Trial": 4,
            "Is Target": False,
            "Response": "non-match",
            "Reaction Time": 0.5,
            "Accuracy": True,
        },
    ]


@pytest.fixture
def random_data():
    """Returns data behaving like a random guesser (50% accuracy)."""
    return [
        {
            "Trial": 1,
            "Is Target": True,
            "Response": "match",
            "Reaction Time": 0.5,
            "Accuracy": True,
        },  # Hit
        {
            "Trial": 2,
            "Is Target": True,
            "Response": "non-match",
            "Reaction Time": 0.5,
            "Accuracy": False,
        },  # Miss
        {
            "Trial": 3,
            "Is Target": False,
            "Response": "match",
            "Reaction Time": 0.5,
            "Accuracy": False,
        },  # False Alarm
        {
            "Trial": 4,
            "Is Target": False,
            "Response": "non-match",
            "Reaction Time": 0.5,
            "Accuracy": True,
        },
        # Correct Rejection
    ]


@pytest.fixture
def block_data_with_distractor():
    """
    Constructs a 10-trial block with a distractor at Trial 5.

    Structure:
    - Trials 1-4: Perfect performance (Pre-Distractor)
    - Trial 5: DISTRACTOR (Not scored directly, but creates the boundary)
    - Trials 6-9: Random performance (Post-Distractor)
    - Trial 10: Perfect
    """
    trials = []

    # 1. Pre-Distractor (Trials 2,3,4 are the window): ALL CORRECT
    for i in range(1, 5):
        trials.append(
            {
                "Trial": i,
                "Is Target": False,
                "Response": "non-match",
                "Reaction Time": 0.4,
                "Accuracy": True,
            }
        )

    # 2. Post-Distractor (Trials 6,7,8 are the window): ALL WRONG (Lapses/Errors) for clarity
    for i in range(5, 9):
        # Making them all lapses/errors to verify the metrics drop
        trials.append(
            {
                "Trial": i,
                "Is Target": True,
                "Response": "non-match",
                "Reaction Time": 0.8,
                "Accuracy": False,
            }
        )

    return trials


# --- THE TESTS ---


def test_accuracy_perfect(perfect_data):
    """If user is perfect, accuracy should be 100%."""
    corr, incorr, lapses, total_rt, avg_rt, acc = calculate_accuracy_and_rt(
        perfect_data
    )

    log_evidence(
        "Accuracy (Perfect)",
        "4 Correct Trials",
        "100.0%",
        f"{acc}%",
        "PASS" if acc == 100.0 else "FAIL",
    )

    assert acc == 100.0
    assert corr == 4


def test_dprime_perfect(perfect_data):
    """Perfect performance should yield high d-prime."""
    d_prime = calculate_dprime(perfect_data)

    log_evidence(
        "d-Prime (Perfect)",
        "4 Correct Trials",
        "> 1.5 (Log-linear corrected)",
        f"{d_prime:.4f}",
        "PASS" if d_prime > 1.5 else "FAIL",
    )

    assert d_prime > 1.5


def test_dprime_random(random_data):
    """Random guessing should yield d-prime approx 0."""
    d_prime = calculate_dprime(random_data)

    log_evidence(
        "d-Prime (Random)",
        "50% Accuracy (Random)",
        "~0.0",
        f"{d_prime:.4f}",
        "PASS" if isclose(d_prime, 0.0, abs_tol=0.2) else "FAIL",
    )

    assert isclose(d_prime, 0.0, abs_tol=0.2)


def test_aprime_perfect(perfect_data):
    """A-prime should be approx 1.0 for perfect performance."""
    a_prime = calculate_A_prime(perfect_data)

    log_evidence(
        "A-Prime (Perfect)",
        "4 Correct Trials",
        "1.0",
        f"{a_prime}",
        "PASS" if isclose(a_prime, 1.0, abs_tol=0.001) else "FAIL",
    )

    # Use isclose because calculate_A_prime clips hit_rate to 0.9999
    assert isclose(a_prime, 1.0, abs_tol=0.001)


def test_summarise_sequential_block(block_data_with_distractor):
    """
    Test the PRE and POST distractor logic.
    Distractor at Trial 5.
    Pre-window (2,3,4) = Perfect (Acc 100%, RT 0.4)
    Post-window (6,7,8) = All Wrong (Acc 0%, RT 0.8)
    """
    distractor_trials = [5]

    # Run the summariser
    summary = summarise_sequential_block(
        block_data_with_distractor, distractor_trials, block_number=1
    )

    # Check Pre-Distractor (Should be Perfect)
    pre_acc = summary["Pre-Distractor Accuracy"]
    pre_rt = summary["Pre-Distractor Avg RT"]

    log_evidence(
        "Pre-Distractor Logic",
        "Trials 2,3,4 (Perfect)",
        "Acc=100%, RT=0.4",
        f"Acc={pre_acc}%, RT={pre_rt}",
        "PASS" if pre_acc == 100.0 else "FAIL",
    )

    assert pre_acc == 100.0
    assert isclose(pre_rt, 0.4, abs_tol=0.0001)  # <--- CHANGED THIS

    # Check Post-Distractor (Should be 0%)
    post_acc = summary["Post-Distractor Accuracy"]
    post_rt = summary["Post-Distractor Avg RT"]

    log_evidence(
        "Post-Distractor Logic",
        "Trials 6,7,8 (All Wrong)",
        "Acc=0%, RT=0.8",
        f"Acc={post_acc}%, RT={post_rt}",
        "PASS" if post_acc == 0.0 else "FAIL",
    )

    assert post_acc == 0.0
    assert isclose(post_rt, 0.8, abs_tol=0.0001)
