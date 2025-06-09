# Changelog

All notable changes to **WAND** will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---
## [1.0.1] – 2025-06-09

### Added
- **Automated Testing Suite**: Implemented a formal test suite in the `/Tests` directory using `pytest` to validate core script logic.
- **Continuous Integration (CI)**: Added a GitHub Actions workflow to automatically run the test suite on every push and pull request.
- **Participant Onboarding Gate**: A new "slow-phase" (1.5x timing) for practice tasks auto-promotes users to normal speed after achieving ≥65% accuracy, aiding initial learning.
- **User-Facing Verification Scripts**: Included `Dummy_Run.py` and `Dummy_Run_Practice.py` for users to quickly verify their setup.

### Changed
- **Modular Code Refactor**: Overhauled core script logic into modular functions to enable effective unit testing.
- **Data Logging**: The initial Participant-ID dialog now configures a dedicated `data/seq_<PID>.csv` logger for more granular, block-by-block performance analysis.

---
## [1.0.0] – 2025-22-05

*Initial public release*