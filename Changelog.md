# Changelog

All notable changes to **WAND** will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---
## [1.3.1] - 2026-03-29

### Added
- **Session History**: The launcher now tracks a rolling history of study names and participant IDs in `data/launcher_state.json`. On subsequent runs, `Study_Name` is a dropdown of previous studies (plus `<New Study>`) and `Participant_ID` shows previous participants for the selected study (plus `<New Participant>`).
- **Duplicate Participant Warning**: If a researcher selects or types a participant ID that has already been run in the chosen study, a warning dialog alerts them that continuing may overwrite data.
- **Duplicate Study Name Guard**: Choosing `<New Study>` and entering a name that already exists in the session history is blocked, directing the user to select it from the dropdown instead.
- **Create New Requires New Study**: Selecting `<Create New>` with an existing study name is blocked — researchers are directed to load the study's preset to add participants, or choose `<New Study>` to start a genuinely new experiment.
- **Standard Order Helper**: Added `wand_nback/block_order.py` as a single source of truth for the canonical default protocol order and default schedule generation.
- **Regression Tests**: Added coverage for locked default ordering, standard-order generation, legacy custom preset loading, create-your-own label parsing, and mode-selection back navigation.

### Changed
- **Block Builder Always Opens on Create New**: When using `<Create New>`, the Block Builder now always opens (empty, for manual placement). It is only skipped on the preset quick path (`Standard_WAND_Protocol`).
- **Standard Default Order**: `Standard_WAND_Protocol` preset now treats the default protocol as the standard order, skipping the block-order editor and going directly to confirmation.
- **Create-Your-Own Order Entry**: The launcher now labels the manual path as `Create Your Own`, and that path opens the editor empty (Start and End only) so researchers assemble the sequence directly from the pools.
- **Confirmation Summary**: Final launcher confirmation now shows the resolved block order for both standard and custom orders, with block-order mode displayed explicitly.
- **Launcher Page Numbering**: All dialog pages are now numbered sequentially (Page 1: Study Setup, Page 2: Participant, Page 3–8: configuration and launch) instead of inconsistent `X/6` or `X/8` labels.
- **Block-Order Naming Cleanup**: Launcher labels are now `Standard` and `Create Your Own`, and saved mode values are normalized to `standard` / `create_your_own` while older values still load correctly.
- **Packaged Preset Cleanup**: Removed the shipped `Custom_Builder_Test.json` preset so it is no longer exposed as a packaged option.

### Fixed
- **Preset Quick-Path Crash**: Switching from a cancelled wizard attempt to a preset no longer crashes with a `KeyError` due to stale page data.
- **Default Schedule Resolution**: Default auto-generated schedules now match the canonical standard protocol (`Breaks=[2, 4]`, `Measures=[2, 3, 4, 5]`) for the 5-cycle default configuration.
- **Legacy Custom Preset Compatibility**: Older presets containing `custom_block_order` but no explicit block-order mode now continue to load as custom-order presets.

---
## [1.3.0] - 2026-03-05

### Added
- **Performance Monitor Core (`wand_nback/performance_monitor.py`)**: Real-time block-level edge-case checks with task-specific criteria (Sequential: d' + lapse rate; Spatial/Dual: lapse rate only).
- **Launcher Edge Case Warnings Page**: Dedicated GUI settings for monitor enable, thresholds, and action mode (`warn_then_terminate`, `auto_terminate`, `log_only`).
- **Performance Monitor Tests**: New `Tests/test_performance_monitor.py` coverage for monitor criteria and action modes.

### Changed
- **Preset Quick-Launch Flow**: Loading a preset now preserves preset task mode/schedules and skips setup dialogs (including Block Builder and mode-selection), proceeding directly to confirmation.
- **Preset Compatibility**: Presets are merged with launcher defaults at load time so older/incomplete presets still run with current expected fields.
- **Quicktest Trial Count**: Automated induction quicktest default increased from 10 to 20 trials for more stable non-zero metrics.

### Fixed
- **Adaptive Monitor Termination Wiring**: `run_adaptive_nback_task()` terminate decisions now propagate correctly through main induction loops (custom-order and cycle-based flows).
- **Monitor Session State**: Performance-monitor flag counter now resets at session start.
- **Quicktest Skip-Key Contamination**: Automated quicktests now explicitly exclude admin keys `Esc` and `5` from mocked keypress pools to prevent accidental block skip/abort.

---
## [1.2.0] - 2026-02-22

### Added
- **EEG Test Utility (`wand-eeg-test`)**: New command-line utility to auto-detect trigger hardware (TriggerBox and parallel port), send test triggers, and measure timing jitter.
- **EEG Read-back Verification**: Parallel port initialisation now writes test patterns and reads them back to confirm hardware is physically present. Prevents false positives on empty addresses (e.g., `0x378` on Windows).
- **Loop Structure Tests (`Tests/test_loop_structure.py`)**: AST-based tests to catch indentation bugs in the main experiment loop.
- **EEG Code Tests (`Tests/test_eeg.py`)**: Tests to verify EEG trigger code structure and config format without requiring hardware.

### Fixed
- **`wand-quicktest` Entrypoint**: The `main()` function now correctly parses CLI arguments and passes `--quicktest` flag through to `run_quicktest()`. Previously, running `wand-quicktest --quicktest` would silently fall through to the manual test mode.
- **Main Experiment Loop Indentation**: Fixed critical indentation bug in `full_induction.py` where the task execution code (Sequential, Spatial, Dual blocks) was outside the `for cycle_num` loop body, causing only one iteration to execute.

### Changed
- **EEG config (`params.json`)**: Added `trigger_mode` and `parallel_port_address` fields for the new auto-detection system.

---
## [1.1.3] - 2026-02-02

### Changed
- **Tests Folder Included in Package**: The `Tests` folder is now included in pip installs, so users can run the automated test suite without cloning the repo (per reviewer feedback).
- **`wand-quicktest` Now Uses Automated Test**: Entry point now runs `Tests/quicktest_induction.py` - faster (~3 seconds) and consistent with CI tests.

### Fixed
- **Quicktest Import Paths**: Fixed broken imports in `quicktest_induction.py` and `quicktest_practice.py` to use new `wand_nback.*` module paths.

### Added
- **JOSS Paper Citations**: Added validation study reference (Mangan, Kourtis & Tomaz, under review) and theoretical framework citation (Mangan & Kourtis, 2025).

---
## [1.1.2] - 2026-01-23

### Added
- **`wand-quicktest` Entry Point**: New console command for quick visual verification without the GUI launcher.


## [1.1.1] - 2026-01-23

### Added 
- **Block Builder True Custom Order**: Blocks now execute in the exact sequence defined in Block Builder (previously used fixed cycle-based order)
- **Terminal Block Sequence Logging**: Full Induction now prints the complete block sequence before execution starts
- **Custom Block Order Test Suite**: 14 new tests in `test_custom_block_order.py` covering edge cases (empty sequences, events before tasks, alternating patterns, etc.)
- **Import Verification Tests**: 6 new tests in `test_imports.py` to catch module import errors
- **Detailed Tooltips**: Task Timings page now includes hover tooltips explaining block duration behaviour and time compression
- **Block Duration Documentation**: README clarifies Sequential duration varies with timing (164 trials × timing), Spatial/Dual fixed at 270 seconds
- **Loading Message**: Confirmation screen indicates PsychoPy window will appear shortly

### Changed
- **Preset Renaming**: Default preset renamed to `Standard_WAND_Protocol.json` for clarity
- **Config Handling**: GUI settings passed via environment variable instead of writing to `params.json`
- **Block Builder Layout**: Main sequence now wraps to multiple rows instead of extending horizontally
- **Duration Calculation**: Now uses actual timing values instead of hardcoded 5 min/block
- **Duration Display**: Shows as "X min Y sec" for better resolution on short experiments

### Fixed
- **Stimuli Path**: Fixed `Abstract Stimuli/apophysis` → `stimuli/apophysis` path error
- **Module Import**: Fixed `from wand_analysis` → `from wand_nback.analysis`


---
## [1.1.0] - 2026-01-13

### Added
- **pip-installable Package**: WAND is now a Python package installable via `pip install git+https://github.com/brodie-neuro/WAND-practice-and-fatigue-induction.git`
- **GUI Launcher (`WAND_Launcher.py`)**: A professional multi-page graphical wizard for configuring experiments.
- **Block Builder**: Visual drag-and-drop interface for customising experiment block order, with new pool-based interface.
- **EEG Trigger Configuration**: EEG/neuroimaging triggers are now fully configurable via `config/params.json`.
- **Full SDT Metrics in CSV**: Added Hits, Misses, False Alarms, Correct Rejections, Hit Rate, FA Rate, and **Criterion (c)**.
- **Optional Demo Viewing**: Participants can choose to watch or skip the demo (Press 'D' or Space).
- **Practice Status Logging**: Real-time console logging for speed profiles and block completion status.
- **Emergency Quit Keys (Full Induction)**: Added `Escape` and `5` key support.
- **Test Suite Documentation**: Created `Tests/TEST_DOCUMENTATION.md` and added Markdown reporting to all tests.
- **New Tests**: Added `Tests/test_block_builder.py`, `Tests/test_launcher_logic.py`, and 6 new SDT tests in `test_metrics.py`.

### Changed
- **Researcher Prompts**: Explicitly labeled N-back level selection screens as `[RESEARCHER ONLY]`.

---
## [1.0.4] - 2025-12-07

### Added
- **Centralised behavioural analysis module**:  
  `wand_analysis.py` now contains all Sequential N-back metrics (accuracy, average RT, A′, d′, and pre/post distractor window calculations).  
  The induction script now delegates all metric computation to this module.
- **Automated Verification Suite**:
  Added `Tests/test_metrics.py` to scientifically verify output calculations via unit testing.

### Changed
- **Config Handling**: Migrated hardcoded parameters to `config/params.json` and `config/text_en.json` (partial).

---
## [1.0.3] - 2025-11-20

### Added
- **Dual N-back Task**: Implementation of simultaneous auditory-sequential and visual-spatial N-back.
- **Spatial N-back Grid**: Radial 12-position grid layout with jittered timing.
- **Fractal Set**: Added 24 new `Abstract Stimuli` generated via Apophysis.

### Fixed
- **Audio Lag**: Pre-loaded sound stimuli to reduce latency <= 10ms.

---
## [1.0.2] - 2025-10-15

### Added
- **Sequential N-back**: Core logic for letter-based N-back (2-back, 3-back).
- **Practice Protocol**: Adaptive difficulty plateau system (`WAND_practice_plateau.py`).

### Changed
- **Stimulus Timing**: Adjusted default ISI to 2.5s based on pilot feedback.
