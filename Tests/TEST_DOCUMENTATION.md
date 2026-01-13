# WAND Test Suite Documentation

This document explains each test in the WAND test suite. Each test is described in **plain English** (what it means for users) and **technical terms** (what it actually does).

---

## Overview

Run all tests with:
```bash
pytest Tests/ -v
```

Test results are saved to `Tests/results/` as text files.

---

## test_metrics.py - Analysis Functions

These tests verify that the statistical analysis functions produce scientifically correct results.

### test_accuracy_perfect

**Plain English**: If a participant gets every answer right, the accuracy should be 100%.

**Technical**: Calls `calculate_accuracy_and_rt()` with 4 correct trials (2 hits, 2 correct rejections). Asserts accuracy = 100.0%.

**Why it matters**: Validates the accuracy calculation is correct for perfect performance.

---

### test_dprime_perfect

**Plain English**: If a participant is performing perfectly, the d-prime (sensitivity) should be high (>1.5).

**Technical**: Calls `calculate_dprime()` with perfect hit rate and zero false alarm rate. Uses log-linear correction to avoid infinity. Asserts d' > 1.5.

**Why it matters**: D-prime is a key measure of cognitive performance. This ensures perfect performance yields high sensitivity.

---

### test_dprime_random

**Plain English**: If a participant is just guessing randomly (50% correct), d-prime should be approximately zero.

**Technical**: Calls `calculate_dprime()` with 50% hit rate and 50% false alarm rate. Asserts d' ≈ 0.0 (±0.2).

**Why it matters**: Validates that random guessing correctly yields no discriminability.

---

### test_aprime_perfect

**Plain English**: A-prime (non-parametric sensitivity) should be ~1.0 for perfect performance.

**Technical**: Calls `calculate_A_prime()` with perfect data. Asserts A' ≈ 1.0.

**Why it matters**: A' is an alternative to d-prime that doesn't assume normal distributions.

---

### test_summarise_sequential_block

**Plain English**: After a distractor appears in a block, participant accuracy typically drops. This test verifies the before/after analysis works correctly.

**Technical**: Creates a block with 100% pre-distractor accuracy and 0% post-distractor accuracy. Calls `summarise_sequential_block()` and verifies pre/post windows are calculated correctly.

**Why it matters**: This is a core measure of the fatigue induction paradigm.

---

## test_config.py - Configuration Integration

These tests verify that configuration settings from the GUI Launcher are correctly used by the experiment scripts.

### test_practice_get_gui_timing_returns_config_value

**Plain English**: When you set a custom display duration (e.g., 1.5 seconds) in the Launcher, the Practice script should actually use 1.5 seconds, not the default.

**Technical**: Sets `WAND_GUI_CONFIG` to a temp file with `sequential.display_duration=1.5`. Calls `practice.get_gui_timing()`. Asserts it returns 1.5 (config value), not 0.8 (default).

**Why it matters**: Proves the script uses YOUR settings, not just hardcoded defaults.

---

### test_practice_get_gui_timing_falls_back_to_default

**Plain English**: When there's no config file, the script should use sensible defaults.

**Technical**: Ensures `WAND_GUI_CONFIG` is not set. Calls `get_gui_timing()`. Asserts it returns the default value.

**Why it matters**: The experiment should run correctly even without the Launcher.

---

### test_practice_spatial_timing_uses_config

**Plain English**: Spatial task timing from GUI is correctly applied.

**Technical**: Same pattern as above for spatial task.

---

### test_practice_dual_timing_uses_config

**Plain English**: Dual task timing from GUI is correctly applied.

**Technical**: Same pattern as above for dual task.

---

### test_induction_timing_via_load_gui_config

**Plain English**: Full Induction script reads timing values correctly from the Launcher config.

**Technical**: Calls `load_gui_config()` and verifies the returned dict contains the correct timing values for spatial task.

**Why it matters**: Validates the config path that Full Induction uses.

---

### test_induction_sequential_timing_via_load_gui_config

**Plain English**: Sequential task timings are correctly accessible in Full Induction.

**Technical**: Verifies `config["sequential"]["display_duration"]` and `config["sequential"]["isi"]` match expected values.

---

### test_induction_dual_timing_via_load_gui_config

**Plain English**: Dual task timings are correctly accessible in Full Induction.

**Technical**: Same verification for dual task timings.

---

### test_load_gui_config_returns_none_without_env

**Plain English**: When no config file exists, the function returns None (not an error).

**Technical**: Clears `WAND_GUI_CONFIG` env var. Asserts `load_gui_config()` returns `None`.

**Why it matters**: Ensures graceful fallback when running without Launcher.

---

### test_practice_fallback_to_default_timing

**Plain English**: Without a config file, Practice uses sensible default timings.

**Technical**: With no config, calls `get_gui_timing()` and asserts it returns the default (0.8s).

---

## test_block_builder.py - Block Generation

These tests verify that the block builder generates the correct experiment structure.

### test_block_counts_default

**Plain English**: If you configure 5 Sequential blocks, 4 Spatial blocks, and 4 Dual blocks, that's exactly what gets generated.

**Technical**: Creates MockBlockBuilder with specific counts. Asserts generated blocks match expected counts.

---

### test_block_ordering_standard

**Plain English**: In standard mode, Spatial tasks run before Dual tasks.

**Technical**: Sets `counterbalance_spatial_dual=False`. Asserts first Spatial block index < first Dual block index.

---

### test_block_ordering_counterbalanced

**Plain English**: In counterbalanced mode, Dual tasks run before Spatial tasks.

**Technical**: Sets `counterbalance_spatial_dual=True`. Asserts first Dual block index < first Spatial block index.

---

### test_breaks_insertion

**Plain English**: If you schedule breaks at positions 2 and 4, there should be exactly 2 break blocks.

**Technical**: Sets `breaks_schedule=[2, 4]`. Counts blocks with `type="break"`. Asserts count == 2.

---

### test_disabled_tasks

**Plain English**: If you disable Sequential and Spatial, only Dual blocks should be generated.

**Technical**: Sets `sequential_enabled=False`, `spatial_enabled=False`. Asserts SEQ=0, SPA=0, DUAL=4.

---

### test_start_block_exists

**Plain English**: Every experiment should have a "Start" block.

**Technical**: Asserts at least one block has `label="Start"`.

---

### test_end_block_exists

**Plain English**: Every experiment should have an "End" block.

**Technical**: Asserts at least one block has `label="End"`.

---

## test_script.py - Data Logging

These tests verify that experiment data is correctly saved to CSV files.

### test_log_seq_block_writes_csv

**Plain English**: When a block finishes, the data is saved to a CSV file with correct values.

**Technical**: Calls `log_seq_block()` with known values. Reads the CSV file. Asserts the logged data matches input.

**Why it matters**: Without correct data logging, the experiment is useless.

---

## test_launcher_logic.py - Launcher Configuration

These tests verify that the Launcher correctly saves and passes configuration.

> **Note**: These tests currently verify that config VALUES are readable. The actual application of some settings (like fullscreen) requires additional fixes.

### test_load_gui_config_returns_dict

**Plain English**: When a config file exists, we can read it.

**Technical**: Sets env var, calls `load_gui_config()`, asserts return type is dict.

---

### test_fullscreen_setting / test_n_back_level_setting / test_rng_seed_setting

**Plain English**: The fullscreen toggle, n-back level, and RNG seed from the Launcher are saved and readable.

**Technical**: Reads specific keys from the loaded config and verifies values.

---

### test_sequential_timings / test_spatial_timings / test_dual_timings

**Plain English**: Task-specific timing settings are saved and readable.

**Technical**: Verifies nested timing values in config dict.

---

### test_participant_id / test_task_mode

**Plain English**: Participant ID and task mode from the Launcher are saved correctly.

**Technical**: Simple key verification in config dict.

---

## Summary

| File | Tests | What It Validates |
|------|-------|-------------------|
| `test_metrics.py` | 5 | Statistical analysis correctness |
| `test_config.py` | 9 | Config values are actually USED |
| `test_block_builder.py` | 7 | Block structure generation |
| `test_script.py` | 3 | CSV data logging |
| `test_launcher_logic.py` | 10 | Launcher config saving |

**Total: 34 tests** covering the core functionality of WAND.
