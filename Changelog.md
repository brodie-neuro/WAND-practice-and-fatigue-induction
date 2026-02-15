# Changelog

All notable changes to **WAND** will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---
## [1.2.0] - 2026-02-15

### Added
- **EEG Trigger Test Utility (`wand-eeg-test`)**: New command-line tool for auto-detecting and configuring EEG trigger hardware before experiments.
- **TriggerBox Support**: Auto-detection of Brain Products TriggerBox (USB serial) alongside traditional parallel port adapters.
- **Parallel Port Auto-Detection**: Scans 18 common I/O addresses for USB-to-parallel adapters (supports Delock, StarTech, generic, and PCI/PCIe cards).
- **Timing Jitter Measurement**: Run `wand-eeg-test --jitter` to send 100 test triggers and generate timing statistics for EEG methods sections.
- **Interactive Manual Address Entry**: If auto-detection fails, users can enter a custom port address from Device Manager.
- **Jitter Report Export**: Timing statistics saved to `data/eeg_jitter_report_{timestamp}.txt` with ready-to-use methods section text.

### Changed
- **Dual-Mode Trigger Support**: `full_induction.py` now supports both TriggerBox (serial) and parallel port modes, auto-configured via params.json.
- **EEG Configuration**: Added `trigger_mode`, `triggerbox_port` settings to params.json for flexible hardware support.

### Fixed
- **`wand-quicktest` Entry Point**: Fixed broken entry point referencing non-existent `main` function — now correctly calls `run_quicktest()`.
- **Missing `Tests/__init__.py`**: Added missing package init file required for `wand-quicktest` to work after pip install.
- **MANIFEST.in Paths**: Fixed three lines referencing non-existent directories (`config`, `"Abstract Stimuli"`, `Logo`) — now points to correct package paths.
- **Dual Practice Loop Indentation**: Fixed `passes` counter increment being outside the `while` loop in Dual N-back normal-speed practice (only affected direct script execution, not Block Builder).
- **Standard Execution Loop Indentation**: Fixed main experiment loop body being outside the `for cycle_num` loop in standard (non-Block Builder) execution path.
- **Duplicate `config/params.json`**: Removed unused root-level copy; all code uses `wand_nback/config/params.json`.

### Added
- **Loop Structure Tests**: Three new AST-based tests (`test_loop_structure.py`) to prevent loop indentation regressions.
- **EEG Configuration Tests**: 13 new tests (`test_eeg.py`) verifying trigger code validity, config structure, and graceful hardware failure — no EEG hardware required.

---
## [1.1.3] - 2026-02-02

### Changed
- **Tests Folder Included in Package**: The `Tests` folder is now included in pip installs, so users can run the automated test suite without cloning the repo..
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