"""
WAND Performance Monitor — Real-Time Block-Level Safeguard

Evaluates participant performance after each completed block and
intervenes when predefined thresholds are breached.

Two-tier design:

* **Sequential N-back** (fixed difficulty):
    d-prime < threshold  OR  lapse-rate > threshold  →  flag.
* **Spatial / Dual N-back** (adaptive difficulty):
    lapse-rate > threshold only.  Accuracy is confounded by level changes.

Action modes:

* ``warn_then_terminate`` *(default)* — First flag shows a supportive,
  participant-facing encouragement message tailored to the failure type.
  Second flag terminates the session gracefully.  Fully automated, no
  experimenter decision required.  Most defensible for publications.
* ``auto_terminate`` — Immediate termination on first flag.
* ``prompt_researcher`` — Researcher-facing dialog (for piloting only).
* ``log_only`` — Log flags, never intervene.

Configuration is read from ``params.json`` under the ``performance_monitor``
key and can be overridden at runtime via the GUI launcher.

Author
------
Brodie E. Mangan

Version
-------
1.3.0

License
-------
MIT (see LICENSE).
"""

from __future__ import annotations

import logging
import platform
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from wand_nback.common import get_param, get_text

# ---------------------------------------------------------------------------
#  Configuration
# ---------------------------------------------------------------------------

# Module-level flag counter — tracks consecutive flags across blocks
_flag_count: int = 0


def reset_flag_count() -> None:
    """Reset the flag counter (call at the start of each session)."""
    global _flag_count
    _flag_count = 0


@dataclass
class MonitorConfig:
    """Runtime settings for the performance monitor."""

    enabled: bool = True
    dprime_threshold: float = 1.0
    missed_response_threshold: float = 0.20
    action: str = "warn_then_terminate"

    @classmethod
    def from_params(cls) -> "MonitorConfig":
        """Build config from ``params.json`` values."""
        section = get_param("performance_monitor", {})
        if not isinstance(section, dict):
            return cls()
        return cls(
            enabled=bool(section.get("enabled", True)),
            dprime_threshold=float(section.get("dprime_threshold", 1.0)),
            missed_response_threshold=float(section.get("missed_response_threshold", 0.20)),
            action=str(section.get("action", "warn_then_terminate")),
        )

    @classmethod
    def from_gui_config(cls, gui_config: Optional[dict]) -> "MonitorConfig":
        """Build config from GUI launcher config dict (takes priority)."""
        if gui_config and "performance_monitor" in gui_config:
            pm = gui_config["performance_monitor"]
            return cls(
                enabled=bool(pm.get("enabled", True)),
                dprime_threshold=float(pm.get("dprime_threshold", 1.0)),
                missed_response_threshold=float(pm.get("missed_response_threshold", 0.20)),
                action=str(pm.get("action", "warn_then_terminate")),
            )
        return cls.from_params()


# ---------------------------------------------------------------------------
#  Alert — audio
# ---------------------------------------------------------------------------

def _play_alert_sound(repeats: int = 1) -> None:
    """Play a brief audible ping to notify the researcher.

    Uses ``winsound`` on Windows (no dependencies).  Falls back to a
    terminal bell on other platforms.
    """
    if platform.system() == "Windows":
        try:
            import winsound
            for _ in range(repeats):
                winsound.Beep(800, 200)   # single short ping
        except Exception:
            print("\a")                    # terminal bell fallback
    else:
        print("\a")


# ---------------------------------------------------------------------------
#  Participant-facing messages
# ---------------------------------------------------------------------------

def _show_participant_warning(
    win,
    has_lapse_flag: bool,
    has_dprime_flag: bool,
    n_back_level: int = 2,
    lapse_rate: float = 0.0,
) -> None:
    """Display a supportive, non-technical encouragement message.

    The participant does not know they have been flagged. This appears
    as a natural pause in the experiment with tailored advice.

    Parameters
    ----------
    win : psychopy.visual.Window
        The experiment window.
    has_lapse_flag : bool
        Whether excessive lapses (missed responses) triggered the flag.
    has_dprime_flag : bool
        Whether low d-prime (poor discrimination) triggered the flag.
    n_back_level : int
        Current N-back level (2, 3, or 4) for accurate instructions.
    lapse_rate : float
        Proportion of missed trials in the last block (0.0 to 1.0).
    """
    from psychopy import core, event, visual

    # Format texts using the language config
    lapse_percentage = int(lapse_rate * 100) if lapse_rate else 0

    if has_lapse_flag and has_dprime_flag:
        body = get_text(
            "perf_monitor_warning_both",
            lapse_percentage=lapse_percentage,
            n_back_level=n_back_level,
        )
    elif has_lapse_flag:
        body = get_text(
            "perf_monitor_warning_lapse",
            lapse_percentage=lapse_percentage,
        )
    else:
        body = get_text(
            "perf_monitor_warning_dprime",
            n_back_level=n_back_level,
        )

    message = get_text(
        "perf_monitor_pause_prompt",
        body=body,
    )

    stim = visual.TextStim(
        win,
        text=message,
        color="white",
        height=24,
        wrapWidth=700,
        bold=False,
    )

    win.color = [-1, -1, -1]
    stim.draw()
    win.flip()

    event.waitKeys(keyList=["space"])

    # Brief blank before resuming
    win.flip()
    core.wait(0.5)


def _show_termination_message(win) -> None:
    """Display a kind, graceful end-of-session message.

    The participant does not know the session has been terminated early.
    """
    from psychopy import core, event, visual

    message = (
        "Thank you for your effort on this task.\n\n"
        "This part of the study is now complete.\n\n"
        "The researcher will be with you shortly."
    )

    stim = visual.TextStim(
        win,
        text=message,
        color="white",
        height=26,
        wrapWidth=700,
        bold=False,
    )

    win.color = [-1, -1, -1]
    stim.draw()
    win.flip()

    # Wait for researcher to come in and press a key
    event.waitKeys(keyList=["space", "return", "escape"])

    win.flip()
    core.wait(0.3)


# ---------------------------------------------------------------------------
#  Researcher-facing prompt (for piloting only)
# ---------------------------------------------------------------------------

def _show_researcher_prompt(
    win,
    task_name: str,
    block_number: int,
    reasons: List[str],
) -> str:
    """Display an on-screen alert and wait for the researcher's decision.

    Parameters
    ----------
    win : psychopy.visual.Window
        The experiment window.
    task_name : str
        E.g. "Sequential 2-back", "Spatial N-back".
    block_number : int
        Which block triggered the alert.
    reasons : list[str]
        Human-readable lines describing each breach.

    Returns
    -------
    str
        ``"continue"`` or ``"terminate"``.
    """
    from psychopy import core, event, visual

    reason_text = "\n".join(f"  • {r}" for r in reasons)

    message = (
        "⚠  PERFORMANCE MONITOR — RESEARCHER ONLY  ⚠\n\n"
        f"Task: {task_name}   |   Block: {block_number}\n\n"
        f"Triggered criteria:\n{reason_text}\n\n"
        "─────────────────────────────────────────────\n"
        "Press  C  to CONTINUE the experiment\n"
        "Press  E  to END the induction early\n"
        "─────────────────────────────────────────────"
    )

    alert_stim = visual.TextStim(
        win,
        text=message,
        color="red",
        height=22,
        wrapWidth=800,
        bold=True,
    )

    # Flash background to catch attention
    for _ in range(3):
        win.color = [0.6, -1, -1]  # dark red flash
        alert_stim.draw()
        win.flip()
        core.wait(0.15)
        win.color = [-1, -1, -1]   # back to black
        alert_stim.draw()
        win.flip()
        core.wait(0.15)

    # Steady display — wait for researcher input
    win.color = [-1, -1, -1]
    alert_stim.draw()
    win.flip()

    keys = event.waitKeys(keyList=["c", "e"])
    decision = "terminate" if "e" in keys else "continue"

    # Restore window
    win.flip()
    core.wait(0.3)

    return decision


# ---------------------------------------------------------------------------
#  Core evaluation
# ---------------------------------------------------------------------------

@dataclass
class BlockCheckResult:
    """Result of a single block performance check."""

    flagged: bool = False
    reasons: List[str] = field(default_factory=list)
    dprime: Optional[float] = None
    lapse_rate: Optional[float] = None
    lapse_count: int = 0
    has_lapse_flag: bool = False
    has_dprime_flag: bool = False
    decision: Optional[str] = None  # "continue" | "terminate" | None


def check_sequential_block(
    block_results: Dict[str, Any],
    block_number: int,
    config: MonitorConfig,
) -> BlockCheckResult:
    """Evaluate a completed Sequential N-back block.

    Parameters
    ----------
    block_results : dict
        The dict returned by ``summarise_sequential_block``.
    block_number : int
        Block index (for logging).
    config : MonitorConfig
        Current monitor settings.

    Returns
    -------
    BlockCheckResult
    """
    result = BlockCheckResult()

    if not config.enabled:
        return result

    # --- D-prime ---
    dprime = block_results.get("Overall D-Prime", 0.0)
    result.dprime = dprime

    if config.dprime_threshold > 0 and dprime < config.dprime_threshold:
        result.flagged = True
        result.has_dprime_flag = True
        result.reasons.append(
            f"d' = {dprime:.2f}  (below threshold of {config.dprime_threshold:.1f})"
        )

    # --- Lapse rate ---
    lapses = block_results.get("Lapses", 0)
    correct = block_results.get("Correct Responses", 0)
    incorrect = block_results.get("Incorrect Responses", 0)
    total = correct + incorrect + lapses

    if total > 0:
        lapse_rate = lapses / total
        result.lapse_rate = lapse_rate
        result.lapse_count = lapses

        if config.missed_response_threshold < 1.0 and lapse_rate > config.missed_response_threshold:
            result.flagged = True
            result.has_lapse_flag = True
            result.reasons.append(
                f"Lapse rate = {lapse_rate:.1%} ({lapses}/{total})  "
                f"(above threshold of {config.missed_response_threshold:.0%})"
            )

    if result.flagged:
        logging.warning(
            f"[PERF MONITOR] Sequential Block {block_number} FLAGGED: "
            + "; ".join(result.reasons)
        )

    return result


def check_adaptive_block(
    task_name: str,
    block_number: int,
    total_lapses: int,
    total_trials: int,
    config: MonitorConfig,
) -> BlockCheckResult:
    """Evaluate a completed Spatial or Dual N-back block (lapse rate only).

    Parameters
    ----------
    task_name : str
        "Spatial N-back" or "Dual N-back".
    block_number : int
        Block index.
    total_lapses : int
        Cumulative lapses across all sub-blocks of this main block.
    total_trials : int
        Cumulative scorable trials across all sub-blocks.
    config : MonitorConfig
        Current monitor settings.

    Returns
    -------
    BlockCheckResult
    """
    result = BlockCheckResult()

    if not config.enabled:
        return result

    if total_trials <= 0:
        return result

    lapse_rate = total_lapses / total_trials
    result.lapse_rate = lapse_rate
    result.lapse_count = total_lapses

    if config.missed_response_threshold < 1.0 and lapse_rate > config.missed_response_threshold:
        result.flagged = True
        result.has_lapse_flag = True
        result.reasons.append(
            f"Lapse rate = {lapse_rate:.1%} ({total_lapses}/{total_trials})  "
            f"(above threshold of {config.missed_response_threshold:.0%})"
        )
        logging.warning(
            f"[PERF MONITOR] {task_name} Block {block_number} FLAGGED: "
            + "; ".join(result.reasons)
        )

    return result


# ---------------------------------------------------------------------------
#  Dispatcher — evaluate, alert, return decision
# ---------------------------------------------------------------------------

def handle_flag(
    win,
    task_name: str,
    block_number: int,
    check_result: BlockCheckResult,
    config: MonitorConfig,
    n_back_level: int = 2,
) -> str:
    """If a block was flagged, execute the configured action.

    Parameters
    ----------
    win : psychopy.visual.Window
        Experiment window (needed for visual prompt).
    task_name : str
        Task label for the alert message.
    block_number : int
        Block number for the alert message.
    check_result : BlockCheckResult
        The evaluation result.
    config : MonitorConfig
        Current settings.
    n_back_level : int
        Current N-back level for participant-facing messages.

    Returns
    -------
    str
        ``"continue"`` or ``"terminate"``.
    """
    global _flag_count

    if not check_result.flagged:
        return "continue"

    _flag_count += 1

    # --- Log always ---
    logging.warning(
        f"[PERF MONITOR] Flag #{_flag_count} on {task_name} Block {block_number}: "
        + "; ".join(check_result.reasons)
    )

    # --- Action ---
    if config.action == "log_only":
        check_result.decision = "continue"
        return "continue"

    if config.action == "auto_terminate":
        logging.warning(
            f"[PERF MONITOR] Auto-terminating induction after {task_name} Block {block_number}"
        )
        _play_alert_sound(repeats=3)
        _show_termination_message(win)
        check_result.decision = "terminate"
        return "terminate"

    if config.action == "warn_then_terminate":
        if _flag_count == 1:
            # First flag: supportive participant message, continue
            logging.info(
                f"[PERF MONITOR] Warning #{_flag_count}: showing participant encouragement"
            )
            _play_alert_sound(repeats=2)
            _show_participant_warning(
                win,
                has_lapse_flag=check_result.has_lapse_flag,
                has_dprime_flag=check_result.has_dprime_flag,
                n_back_level=n_back_level,
                lapse_rate=check_result.lapse_rate or 0.0,
            )
            check_result.decision = "continue"
            return "continue"
        else:
            # Second or subsequent flag: terminate
            logging.warning(
                f"[PERF MONITOR] Flag #{_flag_count}: terminating induction after "
                f"{task_name} Block {block_number}"
            )
            _play_alert_sound(repeats=3)
            _show_termination_message(win)
            check_result.decision = "terminate"
            return "terminate"

    # Default: prompt_researcher (for piloting)
    _play_alert_sound(repeats=3)
    decision = _show_researcher_prompt(win, task_name, block_number, check_result.reasons)
    check_result.decision = decision

    logging.info(
        f"[PERF MONITOR] Researcher decision after {task_name} Block {block_number}: {decision}"
    )

    return decision
