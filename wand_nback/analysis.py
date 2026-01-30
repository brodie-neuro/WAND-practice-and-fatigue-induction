"""
wand_analysis.py

Behavioural metrics helpers for WAND.

This module contains functions for computing signal-detection and basic
performance metrics from trial-level data. It is imported by
WAND_full_induction.py and can also be reused for offline analyses.

Author
------
Brodie E. Mangan

License
-------
MIT (see LICENSE).
"""

from typing import Any, Dict, List, Optional, Tuple

from scipy.stats import norm


def calculate_A_prime(trials: List[Dict[str, Any]]) -> Optional[float]:
    """
    Compute the A′ (A-prime) nonparametric sensitivity index for a set of trials.

    Trials must contain:
      - "Is Target": bool
      - "Response": str in {"match", "non-match", "lapse"}.
    """
    if not trials:
        return None

    hits = 0
    false_alarms = 0
    misses = 0
    correct_rejections = 0

    for t in trials:
        is_target = t.get("Is Target", False)
        response = t.get("Response")
        said_match = response == "match"

        if is_target and said_match:
            hits += 1
        elif is_target and not said_match:
            misses += 1
        elif (not is_target) and said_match:
            false_alarms += 1
        elif (not is_target) and (not said_match):
            correct_rejections += 1

    total_targets = hits + misses
    total_non_targets = false_alarms + correct_rejections

    if total_targets == 0 or total_non_targets == 0:
        return None

    hit_rate = hits / total_targets
    fa_rate = false_alarms / total_non_targets

    # Clip to avoid extreme values
    hit_rate = min(max(hit_rate, 0.0001), 0.9999)
    fa_rate = min(max(fa_rate, 0.0001), 0.9999)

    if hit_rate >= fa_rate:
        a_prime = 0.5 + ((hit_rate - fa_rate) * (1 + hit_rate - fa_rate)) / (
            4 * hit_rate * (1 - fa_rate)
        )
    else:
        a_prime = 0.5 - ((fa_rate - hit_rate) * (1 + fa_rate - hit_rate)) / (
            4 * fa_rate * (1 - hit_rate)
        )

    return a_prime


def calculate_accuracy_and_rt(
    trials: List[Dict[str, Any]],
) -> Tuple[int, int, int, float, float, float]:
    """
    Compute accuracy (%), total RT, and average RT, plus counts.

    This mirrors what you currently do in run_sequential_nback_block:
      correct_responses, incorrect_responses, lapses,
      total_reaction_time, avg_rt, accuracy (%).
    """
    if not trials:
        return 0, 0, 0, 0.0, 0.0, 0.0

    total_trials = len(trials)

    correct = sum(1 for t in trials if t.get("Accuracy"))
    lapses = sum(1 for t in trials if t.get("Response") == "lapse")
    incorrect = total_trials - correct - lapses

    total_responded = correct + incorrect + lapses
    accuracy = (correct / total_responded) * 100 if total_responded else 0.0

    rts = [t["Reaction Time"] for t in trials if t.get("Reaction Time") is not None]
    total_rt = sum(rts)
    avg_rt = total_rt / len(rts) if rts else 0.0

    return correct, incorrect, lapses, total_rt, avg_rt, accuracy


def calculate_dprime(detailed_data: List[Dict[str, Any]]) -> float:
    """
    Compute d′ (d-prime) with log-linear correction.

    For full SDT metrics including criterion, use calculate_sdt_metrics().

    Trials must contain:
      - "Is Target": bool
      - "Response": str in {"match", "non-match", "lapse"}.
    """
    metrics = calculate_sdt_metrics(detailed_data)
    return metrics["d_prime"]


def calculate_sdt_metrics(detailed_data: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Compute all Signal Detection Theory metrics with log-linear correction.

    Returns a dictionary containing:
      - hits, misses, false_alarms, correct_rejections (raw counts)
      - hit_rate, fa_rate (corrected rates)
      - d_prime (sensitivity)
      - criterion (response bias, c)

    Trials must contain:
      - "Is Target": bool
      - "Response": str in {"match", "non-match", "lapse"}.
    """
    result = {
        "hits": 0,
        "misses": 0,
        "false_alarms": 0,
        "correct_rejections": 0,
        "hit_rate": 0.0,
        "fa_rate": 0.0,
        "d_prime": 0.0,
        "criterion": 0.0,
    }

    if not detailed_data:
        return result

    hits = 0
    false_alarms = 0
    misses = 0
    correct_rejections = 0

    for t in detailed_data:
        is_target = t.get("Is Target", False)
        response = t.get("Response")
        said_match = response == "match"

        if is_target and said_match:
            hits += 1
        elif is_target and not said_match:
            misses += 1
        elif (not is_target) and said_match:
            false_alarms += 1
        elif (not is_target) and (not said_match):
            correct_rejections += 1

    total_targets = hits + misses
    total_non_targets = false_alarms + correct_rejections

    result["hits"] = hits
    result["misses"] = misses
    result["false_alarms"] = false_alarms
    result["correct_rejections"] = correct_rejections

    if total_targets == 0 or total_non_targets == 0:
        return result

    # Log-linear correction
    hit_rate = (hits + 0.5) / (total_targets + 1)
    fa_rate = (false_alarms + 0.5) / (total_non_targets + 1)

    result["hit_rate"] = hit_rate
    result["fa_rate"] = fa_rate

    try:
        z_hit = norm.ppf(hit_rate)
        z_fa = norm.ppf(fa_rate)
        d_prime = z_hit - z_fa
        criterion = -0.5 * (z_hit + z_fa)
        result["d_prime"] = d_prime
        result["criterion"] = criterion
    except ValueError:
        pass

    return result


def _window_metrics(
    trials: List[Dict[str, Any]],
) -> Tuple[Optional[float], Optional[float], Optional[float]]:
    """
    Internal helper: accuracy, avg RT, A′ for a subset of trials.

    Returns (accuracy_percent, avg_rt, a_prime) or (None, None, None) if no trials.
    """
    if not trials:
        return None, None, None

    _, _, _, _, avg_rt, accuracy = calculate_accuracy_and_rt(trials)
    a_prime = calculate_A_prime(trials)
    return accuracy, avg_rt, a_prime


def summarise_sequential_block(
    detailed_data: List[Dict[str, Any]],
    distractor_trials: List[int],
    block_number: int,
) -> Dict[str, Any]:
    """
    Compute all block-level metrics for a Sequential N-back block.

    This replicates the logic that used to live at the end of
    run_sequential_nback_block in WAND_full_induction.py:
      - global accuracy, total RT, average RT
      - pre/post distractor accuracy, RT, A′
      - overall d′
    """
    total_trials = len(detailed_data)

    # Overall counts and RT
    (
        correct_responses,
        incorrect_responses,
        lapses,
        total_rt,
        avg_rt,
        accuracy,
    ) = calculate_accuracy_and_rt(detailed_data)

    # Pre / post distractor windows
    pre_indices: set[int] = set()
    post_indices: set[int] = set()

    for d in distractor_trials:
        # 3 trials before the distractor
        for j in range(d - 3, d):
            if 1 <= j <= total_trials:
                pre_indices.add(j)
        # 3 trials after the distractor
        for j in range(d + 1, d + 4):
            if 1 <= j <= total_trials:
                post_indices.add(j)

    pre_data = [t for t in detailed_data if t["Trial"] in pre_indices]
    post_data = [t for t in detailed_data if t["Trial"] in post_indices]

    pre_acc, pre_rt, pre_ap = _window_metrics(pre_data)
    post_acc, post_rt, post_ap = _window_metrics(post_data)

    # This matches your original "reaction_times" list
    reaction_times = [
        t["Reaction Time"] for t in detailed_data if t.get("Reaction Time") is not None
    ]

    # Get full SDT metrics (d', criterion, hits, FA, etc.)
    sdt = calculate_sdt_metrics(detailed_data)

    return {
        "Block Number": block_number,
        "Correct Responses": correct_responses,
        "Incorrect Responses": incorrect_responses,
        "Lapses": lapses,
        "Accuracy": accuracy,
        "Total Reaction Time": total_rt,
        "Average Reaction Time": avg_rt,
        "Reaction Times": reaction_times,
        "Detailed Data": detailed_data,
        "Pre-Distractor Accuracy": pre_acc if pre_acc is not None else "N/A",
        "Pre-Distractor Avg RT": pre_rt if pre_rt is not None else "N/A",
        "Pre-Distractor A-Prime": pre_ap if pre_ap is not None else "N/A",
        "Post-Distractor Accuracy": post_acc if post_acc is not None else "N/A",
        "Post-Distractor Avg RT": post_rt if post_rt is not None else "N/A",
        "Post-Distractor A-Prime": post_ap if post_ap is not None else "N/A",
        # Full SDT metrics for criterion analysis
        "Overall D-Prime": sdt["d_prime"],
        "Criterion": sdt["criterion"],
        "Hits": sdt["hits"],
        "Misses": sdt["misses"],
        "False Alarms": sdt["false_alarms"],
        "Correct Rejections": sdt["correct_rejections"],
        "Hit Rate": sdt["hit_rate"],
        "FA Rate": sdt["fa_rate"],
    }
