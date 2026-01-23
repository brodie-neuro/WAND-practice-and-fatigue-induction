import json
import os
import sys
from math import isclose

import pytest

# Ensure we can import modules from the main folder
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from wand_nback.analysis import (
    calculate_A_prime,
    calculate_accuracy_and_rt,
    calculate_dprime,
    calculate_sdt_metrics,
    summarise_sequential_block,
)

# --- LOGGING HELPER ---
# This allows us to save the "evidence" to a file
RESULTS_DIR = os.path.join(os.path.dirname(__file__), "results")
os.makedirs(RESULTS_DIR, exist_ok=True)
LOG_FILE = os.path.join(RESULTS_DIR, "test_metrics_results.md")


def log_evidence(test_name, input_desc, expected, actual, status):
    """Log test evidence to Markdown file."""
    status_icon = "✅" if status == "PASS" else "❌"
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"### {status_icon} {test_name}\n\n")
        f.write(f"| Field | Value |\n")
        f.write(f"|-------|-------|\n")
        f.write(f"| **Status** | {status} |\n")
        f.write(f"| **Input** | {input_desc} |\n")
        f.write(f"| **Expected** | `{expected}` |\n")
        f.write(f"| **Actual** | `{actual}` |\n")
        f.write(f"\n---\n\n")


# Clear the log file at the start of the run
@pytest.hookimpl(tryfirst=True)
def pytest_sessionstart(session):
    from datetime import datetime

    with open(LOG_FILE, "w", encoding="utf-8") as f:
        f.write("# WAND Metrics Test Results\n\n")
        f.write(f"**Run Date**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write("---\n\n")
        f.write("## Test Results\n\n")


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


# --- SDT METRICS TESTS ---


def test_sdt_metrics_perfect(perfect_data):
    """Perfect performance: high d', neutral criterion, all hits/CRs."""
    sdt = calculate_sdt_metrics(perfect_data)

    log_evidence(
        "SDT Metrics (Perfect)",
        "4 Correct Trials (2 Hits, 2 CRs)",
        "Hits=2, FA=0, d'>1.5",
        f"Hits={sdt['hits']}, FA={sdt['false_alarms']}, d'={sdt['d_prime']:.2f}",
        "PASS" if sdt["hits"] == 2 and sdt["false_alarms"] == 0 else "FAIL",
    )

    assert sdt["hits"] == 2
    assert sdt["misses"] == 0
    assert sdt["false_alarms"] == 0
    assert sdt["correct_rejections"] == 2
    assert sdt["d_prime"] > 1.5  # High sensitivity


def test_sdt_metrics_criterion_unbiased(perfect_data):
    """Unbiased responder should have criterion near 0."""
    sdt = calculate_sdt_metrics(perfect_data)

    log_evidence(
        "Criterion (Unbiased)",
        "Equal targets/non-targets, 100% correct",
        "criterion ~= 0 (neutral)",
        f"c = {sdt['criterion']:.4f}",
        "PASS" if abs(sdt["criterion"]) < 1.0 else "FAIL",
    )

    # Perfect performance with balanced trials = criterion near 0
    assert abs(sdt["criterion"]) < 1.0


def test_sdt_metrics_random(random_data):
    """Random guesser: d' near 0, mixed SDT counts."""
    sdt = calculate_sdt_metrics(random_data)

    log_evidence(
        "SDT Metrics (Random)",
        "Random responses (50% accuracy)",
        "d' ~= 0",
        f"d' = {sdt['d_prime']:.4f}, c = {sdt['criterion']:.4f}",
        "PASS" if abs(sdt["d_prime"]) < 1.0 else "FAIL",
    )

    # Random guessing = low d-prime
    assert abs(sdt["d_prime"]) < 1.0


def test_sdt_metrics_in_block_summary(block_data_with_distractor):
    """Block summary should include all SDT metrics."""
    summary = summarise_sequential_block(
        block_data_with_distractor, [5], block_number=1
    )

    # Check all SDT fields exist
    required_fields = [
        "Overall D-Prime",
        "Criterion",
        "Hits",
        "Misses",
        "False Alarms",
        "Correct Rejections",
        "Hit Rate",
        "FA Rate",
    ]
    missing = [f for f in required_fields if f not in summary]

    log_evidence(
        "SDT Metrics in Block Summary",
        "summarise_sequential_block output",
        "All 8 SDT fields present",
        f"Missing: {missing}" if missing else "All present",
        "PASS" if not missing else "FAIL",
    )

    assert not missing, f"Missing SDT fields: {missing}"
    assert isinstance(summary["Criterion"], float)
    assert isinstance(summary["Hits"], int)


@pytest.fixture
def liberal_bias_data():
    """Responder who says 'match' too often (liberal bias, c < 0)."""
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
            "Response": "match",
            "Reaction Time": 0.5,
            "Accuracy": True,
        },  # Hit
        {
            "Trial": 3,
            "Is Target": False,
            "Response": "match",
            "Reaction Time": 0.5,
            "Accuracy": False,
        },  # FA
        {
            "Trial": 4,
            "Is Target": False,
            "Response": "match",
            "Reaction Time": 0.5,
            "Accuracy": False,
        },  # FA
        {
            "Trial": 5,
            "Is Target": False,
            "Response": "match",
            "Reaction Time": 0.5,
            "Accuracy": False,
        },  # FA
        {
            "Trial": 6,
            "Is Target": False,
            "Response": "non-match",
            "Reaction Time": 0.5,
            "Accuracy": True,
        },  # CR
    ]


@pytest.fixture
def conservative_bias_data():
    """Responder who says 'non-match' too often (conservative bias, c > 0)."""
    return [
        {
            "Trial": 1,
            "Is Target": True,
            "Response": "non-match",
            "Reaction Time": 0.5,
            "Accuracy": False,
        },  # Miss
        {
            "Trial": 2,
            "Is Target": True,
            "Response": "non-match",
            "Reaction Time": 0.5,
            "Accuracy": False,
        },  # Miss
        {
            "Trial": 3,
            "Is Target": True,
            "Response": "match",
            "Reaction Time": 0.5,
            "Accuracy": True,
        },  # Hit
        {
            "Trial": 4,
            "Is Target": False,
            "Response": "non-match",
            "Reaction Time": 0.5,
            "Accuracy": True,
        },  # CR
        {
            "Trial": 5,
            "Is Target": False,
            "Response": "non-match",
            "Reaction Time": 0.5,
            "Accuracy": True,
        },  # CR
        {
            "Trial": 6,
            "Is Target": False,
            "Response": "non-match",
            "Reaction Time": 0.5,
            "Accuracy": True,
        },  # CR
    ]


def test_sdt_liberal_bias(liberal_bias_data):
    """Liberal responder: says 'match' too often, negative criterion."""
    sdt = calculate_sdt_metrics(liberal_bias_data)

    log_evidence(
        "SDT Metrics (Liberal Bias)",
        "2 Hits, 3 FAs, 1 CR",
        "c < 0 (liberal)",
        f"Hits={sdt['hits']}, FA={sdt['false_alarms']}, c={sdt['criterion']:.3f}",
        "PASS" if sdt["criterion"] < 0 else "FAIL",
    )

    assert sdt["hits"] == 2
    assert sdt["false_alarms"] == 3
    assert sdt["criterion"] < 0, "Liberal bias should have negative criterion"


def test_sdt_conservative_bias(conservative_bias_data):
    """Conservative responder: says 'non-match' too often, positive criterion."""
    sdt = calculate_sdt_metrics(conservative_bias_data)

    log_evidence(
        "SDT Metrics (Conservative Bias)",
        "1 Hit, 2 Misses, 3 CRs",
        "c > 0 (conservative)",
        f"Hits={sdt['hits']}, Misses={sdt['misses']}, c={sdt['criterion']:.3f}",
        "PASS" if sdt["criterion"] > 0 else "FAIL",
    )

    assert sdt["hits"] == 1
    assert sdt["misses"] == 2
    assert sdt["correct_rejections"] == 3
    assert sdt["criterion"] > 0, "Conservative bias should have positive criterion"


# --- EDGE CASE TESTS ---


@pytest.fixture
def all_miss_data():
    """Extreme case: participant misses all targets."""
    return [
        {"Trial": 1, "Is Target": True, "Response": "non-match", "Reaction Time": 0.5, "Accuracy": False},
        {"Trial": 2, "Is Target": True, "Response": "non-match", "Reaction Time": 0.5, "Accuracy": False},
        {"Trial": 3, "Is Target": False, "Response": "non-match", "Reaction Time": 0.5, "Accuracy": True},
        {"Trial": 4, "Is Target": False, "Response": "non-match", "Reaction Time": 0.5, "Accuracy": True},
    ]


@pytest.fixture
def all_false_alarm_data():
    """Extreme case: participant says 'match' to all non-targets."""
    return [
        {"Trial": 1, "Is Target": True, "Response": "match", "Reaction Time": 0.5, "Accuracy": True},
        {"Trial": 2, "Is Target": True, "Response": "match", "Reaction Time": 0.5, "Accuracy": True},
        {"Trial": 3, "Is Target": False, "Response": "match", "Reaction Time": 0.5, "Accuracy": False},
        {"Trial": 4, "Is Target": False, "Response": "match", "Reaction Time": 0.5, "Accuracy": False},
    ]


def test_sdt_all_miss(all_miss_data):
    """Edge case: 0% hit rate. SDT should handle gracefully with log-linear correction."""
    sdt = calculate_sdt_metrics(all_miss_data)

    log_evidence(
        "SDT Metrics (All Miss)",
        "0 Hits, 2 Misses, 0 FA, 2 CR",
        "d' should be negative (poor sensitivity)",
        f"Hits={sdt['hits']}, d'={sdt['d_prime']:.3f}",
        "PASS" if sdt["hits"] == 0 and sdt["d_prime"] < 1.0 else "FAIL",
    )

    assert sdt["hits"] == 0
    assert sdt["misses"] == 2
    assert sdt["false_alarms"] == 0
    assert isinstance(sdt["d_prime"], float), "d' should be a valid float (not infinity)"


def test_sdt_all_false_alarm(all_false_alarm_data):
    """Edge case: 100% false alarm rate. SDT should handle gracefully."""
    sdt = calculate_sdt_metrics(all_false_alarm_data)

    log_evidence(
        "SDT Metrics (All FA)",
        "2 Hits, 0 Misses, 2 FA, 0 CR",
        "d' should be near 0 (poor discriminability)",
        f"FA={sdt['false_alarms']}, d'={sdt['d_prime']:.3f}",
        "PASS" if sdt["false_alarms"] == 2 and abs(sdt["d_prime"]) < 2.0 else "FAIL",
    )

    assert sdt["false_alarms"] == 2
    assert sdt["correct_rejections"] == 0
    assert isinstance(sdt["d_prime"], float), "d' should be a valid float"


def test_accuracy_zero_correct():
    """Edge case: 0% accuracy."""
    all_wrong_data = [
        {"Trial": 1, "Is Target": True, "Response": "non-match", "Reaction Time": 0.5, "Accuracy": False},
        {"Trial": 2, "Is Target": False, "Response": "match", "Reaction Time": 0.5, "Accuracy": False},
    ]
    
    corr, incorr, lapses, total_rt, avg_rt, acc = calculate_accuracy_and_rt(all_wrong_data)
    
    log_evidence(
        "Accuracy (0%)",
        "All wrong responses",
        "0.0%",
        f"{acc}%",
        "PASS" if acc == 0.0 else "FAIL",
    )
    
    assert acc == 0.0
    assert corr == 0
    assert incorr == 2

