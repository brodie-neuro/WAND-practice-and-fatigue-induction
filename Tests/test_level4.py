"""
Tests for Level 4/5 N-back support.

Covers:
- Promotion logic (2->3->4, demotions)
- Plateau detection with level 4
- Color scheme for levels 2-5
- Max blocks cap increase to 18
"""

import json
import os
import sys

import pytest

# Ensure the package is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


# =============================================================================
# check_level_change tests
# =============================================================================


class TestCheckLevelChange:
    """Tests for `check_level_change` promotion/demotion logic."""

    @pytest.fixture(autouse=True)
    def _import(self):
        """Import the function under test, skipping if PsychoPy unavailable."""
        try:
            from wand_nback.practice_plateau import check_level_change

            self.check_level_change = check_level_change
        except Exception:
            pytest.skip("practice_plateau import requires PsychoPy environment")

    # --- Promotion ---

    def test_promote_2_to_3(self):
        """Two blocks at >=82% on level 2 should promote to 3."""
        results = [
            (1, 2, 85.0, 0.5),
            (2, 2, 90.0, 0.5),
        ]
        assert self.check_level_change(results, 2, window_size=2) == 3

    def test_promote_3_to_4(self):
        """Two blocks at >=82% on level 3 should promote to 4."""
        results = [
            (1, 3, 85.0, 0.5),
            (2, 3, 88.0, 0.5),
        ]
        assert self.check_level_change(results, 3, window_size=2) == 4

    def test_no_promote_4_stays_at_4(self):
        """Level 4 at >=82% should NOT promote further (no level 5 in practice)."""
        results = [
            (1, 4, 90.0, 0.5),
            (2, 4, 95.0, 0.5),
        ]
        assert self.check_level_change(results, 4, window_size=2) == 4

    # --- Demotion ---

    def test_demote_4_to_3(self):
        """Two blocks at <70% on level 4 should demote to 3."""
        results = [
            (1, 4, 60.0, 0.5),
            (2, 4, 65.0, 0.5),
        ]
        assert self.check_level_change(results, 4, window_size=2) == 3

    def test_demote_3_to_2(self):
        """Two blocks at <70% on level 3 should demote to 2."""
        results = [
            (1, 3, 55.0, 0.5),
            (2, 3, 60.0, 0.5),
        ]
        assert self.check_level_change(results, 3, window_size=2) == 2

    # --- Hold steady ---

    def test_hold_at_3_between_thresholds(self):
        """Rolling avg between 70% and 82% on level 3 should hold."""
        results = [
            (1, 3, 75.0, 0.5),
            (2, 3, 78.0, 0.5),
        ]
        assert self.check_level_change(results, 3, window_size=2) == 3

    def test_hold_at_4_between_thresholds(self):
        """Rolling avg between 70% and 82% on level 4 should hold."""
        results = [
            (1, 4, 75.0, 0.5),
            (2, 4, 78.0, 0.5),
        ]
        assert self.check_level_change(results, 4, window_size=2) == 4

    def test_insufficient_blocks_returns_current(self):
        """Less than window_size blocks should return current level."""
        results = [(1, 3, 90.0, 0.5)]
        assert self.check_level_change(results, 3, window_size=2) == 3

    # --- Full promotion chain ---

    def test_full_chain_2_to_3_to_4(self):
        """Simulate a full 2->3->4 promotion chain."""
        results = []

        # Two strong blocks at level 2
        results.append((1, 2, 85.0, 0.5))
        results.append((2, 2, 88.0, 0.5))
        new_level = self.check_level_change(results, 2, window_size=2)
        assert new_level == 3

        # Two strong blocks at level 3
        results.append((3, 3, 84.0, 0.5))
        results.append((4, 3, 86.0, 0.5))
        new_level = self.check_level_change(results, 3, window_size=2)
        assert new_level == 4

        # Stable at level 4 (no further promotion)
        results.append((5, 4, 90.0, 0.5))
        results.append((6, 4, 92.0, 0.5))
        new_level = self.check_level_change(results, 4, window_size=2)
        assert new_level == 4


# =============================================================================
# check_plateau tests with level 4
# =============================================================================


class TestCheckPlateauLevel4:
    """Tests for `check_plateau` with level 4 blocks."""

    @pytest.fixture(autouse=True)
    def _import(self):
        try:
            from wand_nback.practice_plateau import check_plateau

            self.check_plateau = check_plateau
        except Exception:
            pytest.skip("practice_plateau import requires PsychoPy environment")

    def test_plateau_at_level_4(self):
        """Three stable level-4 blocks should trigger plateau."""
        results = [
            (1, 4, 80.0, 0.5),
            (2, 4, 82.0, 0.5),
            (3, 4, 81.0, 0.5),
        ]
        assert self.check_plateau(results, variance_threshold=7) is True

    def test_no_plateau_mixed_levels_3_and_4(self):
        """Mixed levels should NOT plateau."""
        results = [
            (1, 3, 80.0, 0.5),
            (2, 4, 82.0, 0.5),
            (3, 4, 81.0, 0.5),
        ]
        assert self.check_plateau(results, variance_threshold=7) is False

    def test_no_plateau_high_variance_level_4(self):
        """High variance at level 4 should NOT plateau."""
        results = [
            (1, 4, 60.0, 0.5),
            (2, 4, 90.0, 0.5),
            (3, 4, 65.0, 0.5),
        ]
        assert self.check_plateau(results, variance_threshold=7) is False


# =============================================================================
# Color scheme tests
# =============================================================================


class TestLevelColors:
    """Tests for `get_level_color` with levels 2-5."""

    @pytest.fixture(autouse=True)
    def _import(self):
        try:
            from wand_nback.common import get_level_color, load_config

            self.get_level_color = get_level_color
            config_dir = os.path.join(
                os.path.dirname(__file__), "..", "wand_nback", "config"
            )
            load_config(lang="en", config_dir=config_dir)
        except Exception:
            pytest.skip("common import requires PsychoPy environment")

    def test_level_2_has_color(self):
        color = self.get_level_color(2)
        assert color is not None and color != "white"

    def test_level_3_has_color(self):
        color = self.get_level_color(3)
        assert color is not None and color != "white"

    def test_level_4_has_color(self):
        color = self.get_level_color(4)
        assert color is not None and color != "white"

    def test_level_5_has_color(self):
        color = self.get_level_color(5)
        assert color is not None and color != "white"

    def test_all_colors_distinct(self):
        """All level colors must be distinguishable."""
        colors = [self.get_level_color(n) for n in [2, 3, 4, 5]]
        assert len(set(colors)) == 4, f"Colors not all distinct: {colors}"

    def test_level_none_returns_default(self):
        color = self.get_level_color(None)
        assert color == "white"


# =============================================================================
# Max blocks cap test
# =============================================================================


class TestMaxBlocksCap:
    """Verify max_blocks has been increased to 18."""

    def test_max_blocks_is_18(self):
        """The practice-to-plateau loop should allow up to 18 blocks."""
        import ast

        pp_path = os.path.join(
            os.path.dirname(__file__),
            "..",
            "wand_nback",
            "practice_plateau.py",
        )
        with open(pp_path, "r", encoding="utf-8") as f:
            source = f.read()

        # Find "max_blocks = <value>" assignment
        tree = ast.parse(source)
        max_blocks_values = []
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Assign)
                and len(node.targets) == 1
                and isinstance(node.targets[0], ast.Name)
                and node.targets[0].id == "max_blocks"
                and isinstance(node.value, ast.Constant)
            ):
                max_blocks_values.append(node.value.value)

        assert (
            18 in max_blocks_values
        ), f"max_blocks should be 18 but found: {max_blocks_values}"


# =============================================================================
# params.json schema test
# =============================================================================


class TestParamsJsonColors:
    """Verify params.json has colors for all levels."""

    def test_params_has_level_5_color(self):
        params_path = os.path.join(
            os.path.dirname(__file__),
            "..",
            "wand_nback",
            "config",
            "params.json",
        )
        with open(params_path, "r", encoding="utf-8") as f:
            params = json.load(f)

        levels = params.get("colors", {}).get("levels", {})
        for lvl in ["2", "3", "4", "5"]:
            assert lvl in levels, f"Level {lvl} missing from colors.levels"
            assert levels[lvl] != "", f"Level {lvl} color is empty"


# =============================================================================
# text_en.json schema test
# =============================================================================


class TestTextPrompts:
    """Verify text strings mention level 4."""

    def test_practice_prompt_mentions_4(self):
        text_path = os.path.join(
            os.path.dirname(__file__),
            "..",
            "wand_nback",
            "config",
            "text_en.json",
        )
        with open(text_path, "r", encoding="utf-8") as f:
            text = json.load(f)

        assert (
            "4" in text["practice_seq_start_level"]
        ), "Practice prompt should mention level 4"
        assert "4" in text["get_n_level"], "Induction prompt should mention level 4"
