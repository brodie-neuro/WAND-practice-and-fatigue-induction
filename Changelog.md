# Changelog

All notable changes to **WAND** will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---
## [1.1.1] - 2026-01-21

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