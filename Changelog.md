# Changelog

All notable changes to **WAND** will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---
## [1.0.2] - 2025-06-12

fixed - spatial background grid to not dissapear 
grace period of 1 block added to level 3 

### Added
- **Automated Testing Suite**: Implemented a formal test suite in the `/Tests` directory using `pytest`.
- **Continuous Integration (CI)**: Added a GitHub Actions workflow to automatically run tests on every push and pull request.

### Changed
- **Modular Code Refactor**: Overhauled core script logic into modular functions to enable effective unit testing.
- **Sequential Practice Algorithm**: Updated the run_sequential_nback_until_plateau function to include a one-block, non-scored "grace period" when difficulty first increases to 3-back. This allows for participant familiarisation and prevents premature level drops.
- **Post-Experiment Summary**: Streamlined the show_final_summary screen in the main induction script to only display essential block-by-block performance metrics. Removed the redundant subjective and comparison pages for a cleaner user experience, as this data is already saved to the CSV file.
- **Docstrings** Improved docstring formatting across all scripts.
- **Documentation**: Finalized `README.md` and `CHANGELOG.md` for JOSS submission.
- **Archival**: Updated `.zenodo.json` to correct metadata for automated Zenodo releases.

### Fixed
- **Spatial Task Visuals**: Corrected a rendering issue where the background grid would disappear during the spatial n-back practice blocks.

---
## [1.0.1] - 2025-06-04

### Added
- **Participant Onboarding Gate**: A new "slow-phase" (1.5x timing) for practice tasks that auto-promotes users to normal speed.
- **Participant-ID dialog** on start-up for data logging.
- **User-Facing Verification Scripts**: Included `Dummy_Run.py` and `Dummy_Run_Practice.py` for users to quickly verify their setup.

### Changed
- **Data Logging**: Switched to a dedicated `data/seq_<PID>.csv` logger for more granular, block-by-block performance analysis.

---
## [1.0.0] – 2024-05-22

*Initial public release*