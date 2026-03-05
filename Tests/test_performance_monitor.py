"""
Tests for the WAND Performance Monitor.

Verifies that the two-tier monitoring system correctly evaluates
Sequential (d-prime + lapses) and adaptive (lapses only) blocks,
and respects configuration toggles.
"""

import sys
from unittest.mock import MagicMock

# Mock PsychoPy before any import touches it
sys.modules["psychopy"] = MagicMock()
sys.modules["psychopy.visual"] = MagicMock()
sys.modules["psychopy.core"] = MagicMock()
sys.modules["psychopy.event"] = MagicMock()
sys.modules["psychopy.gui"] = MagicMock()

import pytest

# Mock the alert sound so it doesn't beep during tests
import wand_nback.performance_monitor as pm
from wand_nback.performance_monitor import (
    BlockCheckResult,
    MonitorConfig,
    check_adaptive_block,
    check_sequential_block,
    handle_flag,
    reset_flag_count,
)

pm._play_alert_sound = MagicMock()


# ── Fixtures ──────────────────────────────────────────────────────────


@pytest.fixture(autouse=True)
def _reset_flags():
    """Reset the global flag counter before every test."""
    reset_flag_count()


@pytest.fixture
def default_config():
    return MonitorConfig(
        enabled=True,
        dprime_threshold=1.0,
        missed_response_threshold=0.20,
        action="warn_then_terminate",
    )


@pytest.fixture
def disabled_config():
    return MonitorConfig(enabled=False)


def _seq_results(dprime=2.0, correct=130, incorrect=20, lapses=2):
    """Build a minimal Sequential block results dict."""
    return {
        "Overall D-Prime": dprime,
        "Correct Responses": correct,
        "Incorrect Responses": incorrect,
        "Lapses": lapses,
    }


# ── Sequential: d-prime checks ───────────────────────────────────────


class TestSequentialDPrime:
    def test_good_dprime_not_flagged(self, default_config):
        result = check_sequential_block(_seq_results(dprime=2.07), 1, default_config)
        assert not result.flagged
        assert result.dprime == 2.07

    def test_borderline_dprime_not_flagged(self, default_config):
        result = check_sequential_block(_seq_results(dprime=1.06), 2, default_config)
        assert not result.flagged

    def test_low_dprime_flagged(self, default_config):
        result = check_sequential_block(_seq_results(dprime=0.80), 3, default_config)
        assert result.flagged
        assert result.has_dprime_flag
        assert not result.has_lapse_flag
        assert any("d'" in r for r in result.reasons)

    def test_very_low_dprime_flagged(self, default_config):
        result = check_sequential_block(_seq_results(dprime=0.30), 5, default_config)
        assert result.flagged
        assert result.dprime == 0.30

    def test_zero_dprime_flagged(self, default_config):
        result = check_sequential_block(_seq_results(dprime=0.0), 1, default_config)
        assert result.flagged

    def test_dprime_threshold_disabled(self, default_config):
        """d-prime threshold of 0 disables that criterion."""
        config = MonitorConfig(
            enabled=True, dprime_threshold=0, missed_response_threshold=1.0
        )
        result = check_sequential_block(_seq_results(dprime=0.3), 1, config)
        assert not result.flagged


# ── Sequential: lapse rate checks ────────────────────────────────────


class TestSequentialLapseRate:
    def test_no_lapses_not_flagged(self, default_config):
        result = check_sequential_block(_seq_results(lapses=0), 1, default_config)
        assert not result.flagged

    def test_low_lapses_not_flagged(self, default_config):
        # 5 lapses out of 162 = 3.1%
        result = check_sequential_block(
            _seq_results(lapses=5, correct=130, incorrect=27), 2, default_config
        )
        assert not result.flagged

    def test_high_lapses_flagged(self, default_config):
        # 35 lapses out of 166 = 21.1%
        result = check_sequential_block(
            _seq_results(dprime=2.0, lapses=35, correct=77, incorrect=54),
            5,
            default_config,
        )
        assert result.flagged
        assert result.has_lapse_flag
        assert any("Lapse" in r for r in result.reasons)

    def test_exact_threshold_not_flagged(self, default_config):
        # Exactly 20% — threshold uses > not >=
        result = check_sequential_block(
            _seq_results(dprime=2.0, lapses=20, correct=60, incorrect=20),
            1,
            default_config,
        )
        assert not result.flagged

    def test_lapse_threshold_disabled(self):
        config = MonitorConfig(
            enabled=True, dprime_threshold=0, missed_response_threshold=1.0
        )
        result = check_sequential_block(
            _seq_results(dprime=2.0, lapses=50, correct=50, incorrect=10), 1, config
        )
        assert not result.flagged


# ── Sequential: both criteria ────────────────────────────────────────


class TestSequentialBothCriteria:
    def test_both_triggered(self, default_config):
        result = check_sequential_block(
            _seq_results(dprime=0.44, lapses=35, correct=77, incorrect=54),
            4,
            default_config,
        )
        assert result.flagged
        assert result.has_dprime_flag
        assert result.has_lapse_flag
        assert len(result.reasons) == 2

    def test_only_dprime_triggered(self, default_config):
        result = check_sequential_block(
            _seq_results(dprime=0.80, lapses=2, correct=130, incorrect=30),
            3,
            default_config,
        )
        assert result.flagged
        assert result.has_dprime_flag
        assert not result.has_lapse_flag
        assert len(result.reasons) == 1
        assert "d'" in result.reasons[0]


# ── Adaptive blocks: lapse rate only ─────────────────────────────────


class TestAdaptiveBlock:
    def test_low_lapses_not_flagged(self, default_config):
        result = check_adaptive_block(
            "Spatial N-back", 1, total_lapses=3, total_trials=90, config=default_config
        )
        assert not result.flagged

    def test_high_lapses_flagged(self, default_config):
        result = check_adaptive_block(
            "Spatial N-back", 3, total_lapses=25, total_trials=90, config=default_config
        )
        assert result.flagged
        assert result.has_lapse_flag
        assert any("Lapse" in r for r in result.reasons)

    def test_dual_high_lapses_flagged(self, default_config):
        result = check_adaptive_block(
            "Dual N-back", 2, total_lapses=20, total_trials=80, config=default_config
        )
        assert result.flagged

    def test_zero_trials_not_flagged(self, default_config):
        result = check_adaptive_block(
            "Spatial N-back", 1, total_lapses=0, total_trials=0, config=default_config
        )
        assert not result.flagged

    def test_accuracy_not_checked(self, default_config):
        """Even with an 'accuracy' concept, we only check lapses,
        so this should NOT flag just because 'accuracy' would be low."""
        # 5 lapses out of 90 = 5.5% — below threshold
        result = check_adaptive_block(
            "Spatial N-back", 1, total_lapses=5, total_trials=90, config=default_config
        )
        assert not result.flagged


# ── Monitor disabled ─────────────────────────────────────────────────


class TestMonitorDisabled:
    def test_sequential_disabled(self, disabled_config):
        result = check_sequential_block(
            _seq_results(dprime=0.1, lapses=50), 1, disabled_config
        )
        assert not result.flagged

    def test_adaptive_disabled(self, disabled_config):
        result = check_adaptive_block(
            "Spatial N-back",
            1,
            total_lapses=50,
            total_trials=60,
            config=disabled_config,
        )
        assert not result.flagged


# ── handle_flag dispatching ──────────────────────────────────────────


class TestHandleFlag:
    def test_not_flagged_returns_continue(self, default_config):
        check = BlockCheckResult(flagged=False)
        result = handle_flag(MagicMock(), "Test", 1, check, default_config)
        assert result == "continue"

    def test_log_only_returns_continue(self):
        config = MonitorConfig(enabled=True, action="log_only")
        check = BlockCheckResult(flagged=True, reasons=["d' = 0.5"])
        result = handle_flag(MagicMock(), "Test", 1, check, config)
        assert result == "continue"
        assert check.decision == "continue"

    def test_auto_terminate_returns_terminate(self):
        config = MonitorConfig(enabled=True, action="auto_terminate")
        check = BlockCheckResult(flagged=True, reasons=["d' = 0.3"])
        result = handle_flag(MagicMock(), "Test", 1, check, config)
        assert result == "terminate"
        assert check.decision == "terminate"


# ── warn_then_terminate mode ─────────────────────────────────────────


class TestWarnThenTerminate:
    def test_first_flag_continues(self):
        config = MonitorConfig(enabled=True, action="warn_then_terminate")
        check = BlockCheckResult(
            flagged=True, reasons=["d' = 0.8"], has_dprime_flag=True
        )
        result = handle_flag(MagicMock(), "Sequential 2-back", 3, check, config)
        assert result == "continue"
        assert check.decision == "continue"

    def test_second_flag_terminates(self):
        config = MonitorConfig(enabled=True, action="warn_then_terminate")
        win = MagicMock()

        # First flag — warning
        check1 = BlockCheckResult(
            flagged=True, reasons=["d' = 0.8"], has_dprime_flag=True
        )
        result1 = handle_flag(win, "Sequential 2-back", 3, check1, config)
        assert result1 == "continue"

        # Second flag — terminate
        check2 = BlockCheckResult(
            flagged=True, reasons=["d' = 0.44"], has_dprime_flag=True
        )
        result2 = handle_flag(win, "Sequential 2-back", 4, check2, config)
        assert result2 == "terminate"
        assert check2.decision == "terminate"

    def test_third_flag_also_terminates(self):
        """If somehow we get past the second flag, third still terminates."""
        config = MonitorConfig(enabled=True, action="warn_then_terminate")
        win = MagicMock()

        for i in range(3):
            check = BlockCheckResult(
                flagged=True, reasons=["d' = 0.5"], has_dprime_flag=True
            )
            result = handle_flag(win, "Test", i + 1, check, config)

        assert result == "terminate"

    def test_lapse_flag_shows_lapse_message(self):
        """First flag with lapse should set has_lapse_flag."""
        config = MonitorConfig(enabled=True, action="warn_then_terminate")
        check = BlockCheckResult(
            flagged=True,
            reasons=["Lapse rate = 25%"],
            has_lapse_flag=True,
            has_dprime_flag=False,
        )
        result = handle_flag(MagicMock(), "Spatial N-back", 2, check, config)
        assert result == "continue"  # First flag = warning

    def test_flag_counter_resets(self):
        config = MonitorConfig(enabled=True, action="warn_then_terminate")
        win = MagicMock()

        # First flag — warning
        check1 = BlockCheckResult(
            flagged=True, reasons=["d' = 0.8"], has_dprime_flag=True
        )
        handle_flag(win, "Test", 1, check1, config)

        # Reset
        reset_flag_count()

        # Next flag should be first again — warning, not terminate
        check2 = BlockCheckResult(
            flagged=True, reasons=["d' = 0.7"], has_dprime_flag=True
        )
        result = handle_flag(win, "Test", 2, check2, config)
        assert result == "continue"


# ── Pilot 1 regression: verify correct flagging per block ────────────


class TestPilot1Regression:
    """Replay pilot1 data through the monitor to verify expected behavior."""

    def test_block1_passes(self, default_config):
        res = _seq_results(dprime=2.07, correct=139, incorrect=23, lapses=0)
        check = check_sequential_block(res, 1, default_config)
        assert not check.flagged

    def test_block2_passes(self, default_config):
        res = _seq_results(dprime=1.06, correct=111, incorrect=46, lapses=5)
        check = check_sequential_block(res, 2, default_config)
        assert not check.flagged

    def test_block3_flags_dprime(self, default_config):
        res = _seq_results(dprime=0.80, correct=104, incorrect=53, lapses=5)
        check = check_sequential_block(res, 3, default_config)
        assert check.flagged
        assert check.has_dprime_flag
        assert not check.has_lapse_flag
        assert any("d'" in r for r in check.reasons)
        # Lapse rate = 5/162 = 3.1% — should NOT trigger lapse criterion
        assert len(check.reasons) == 1

    def test_block4_flags_dprime(self, default_config):
        res = _seq_results(dprime=0.44, correct=88, incorrect=57, lapses=17)
        check = check_sequential_block(res, 4, default_config)
        assert check.flagged
        # Lapse rate = 17/162 = 10.5% — still below 20%
        assert check.has_dprime_flag
        assert not check.has_lapse_flag

    def test_block5_flags_dprime(self, default_config):
        res = _seq_results(dprime=0.30, correct=77, incorrect=54, lapses=31)
        check = check_sequential_block(res, 5, default_config)
        assert check.flagged
        assert check.has_dprime_flag
        # 31 / (77+54+31) = 31/162 = 19.1% which is < 20%, so only d' triggers
        assert not check.has_lapse_flag

    def test_pilot1_warn_then_terminate_flow(self, default_config):
        """Simulate pilot1 blocks through the full warn_then_terminate flow."""
        win = MagicMock()

        # Block 1: passes
        res1 = _seq_results(dprime=2.07, correct=139, incorrect=23, lapses=0)
        check1 = check_sequential_block(res1, 1, default_config)
        assert not check1.flagged

        # Block 2: passes
        res2 = _seq_results(dprime=1.06, correct=111, incorrect=46, lapses=5)
        check2 = check_sequential_block(res2, 2, default_config)
        assert not check2.flagged

        # Block 3: flagged (d'=0.80) — first flag → warning, continue
        res3 = _seq_results(dprime=0.80, correct=104, incorrect=53, lapses=5)
        check3 = check_sequential_block(res3, 3, default_config)
        assert check3.flagged
        decision3 = handle_flag(win, "Sequential 2-back", 3, check3, default_config)
        assert decision3 == "continue"

        # Block 4: flagged (d'=0.44) — second flag → TERMINATE
        res4 = _seq_results(dprime=0.44, correct=88, incorrect=57, lapses=17)
        check4 = check_sequential_block(res4, 4, default_config)
        assert check4.flagged
        decision4 = handle_flag(win, "Sequential 2-back", 4, check4, default_config)
        assert decision4 == "terminate"
