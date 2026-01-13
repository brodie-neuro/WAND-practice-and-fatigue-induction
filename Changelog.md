# Changelog

All notable changes to **WAND** will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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