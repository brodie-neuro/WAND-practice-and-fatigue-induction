# Changelog

All notable changes to **WAND** will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---
## [1.0.4] - 2025-12-07

### Added
- **Centralised behavioural analysis module**:  
  `wand_analysis.py` now contains all Sequential N-back metrics (accuracy, average RT, A′, d′, and pre/post distractor window calculations).  
  The induction script now delegates all metric computation to this module.
- **Automated Verification Suite**:
  Added `Tests/test_metrics.py` to scientifically verify output calculations via unit testing.
- Tests verify d', A', and Accuracy against known "perfect" and "random" datasets.
- Generates a human-readable evidence log (`Tests/test_results_detailed.txt`) to demonstrate calculation validity without requiring a simulated GUI run.

### Changed
- **Extensive code deduplication and refactoring** (addresses reviewer feedback):
    - **UI prompts**: Replaced all ad-hoc text input and choice loops with shared helpers  
      `prompt_text_input()` and `prompt_choice()` in `wand_common.py`.  
      Used consistently for Participant ID, RNG seed, distractor toggles, etc.
    - **Unified text-screen system**:  
      Welcome screens, instruction screens, break screens, summaries, and transitions are now built on a shared `show_text_screen()` helper.
    - **Response loop unification**:  
      All Spatial, Dual, and Sequential tasks now use a single centralised `collect_trial_response()` function built on `check_response_keys()`, eliminating duplicated per-frame polling and timing logic.
    - **Sequence generation merged**:  
      Sequential image generation is now handled by a single `generate_sequential_image_sequence()` function in `wand_common.py`.

- **Sequential N-back logic standardised**:
    - Removed old **n−1 misleading lure patterns** from 3-back.  
    - Both 2-back and 3-back now follow a unified structure:  
      - ~50% target probability  
      - Maximum 2 consecutive matches  
    - Ensures **d′ and A′ comparability across N levels**.

- **Practical installation improvements** (Reviewer 2):
    - README now explicitly includes **both** `python` **and** `py` commands for Windows.  
    - Added instructions to upgrade pip inside the virtual environment  
      (`python -m pip install --upgrade pip` or `py -m pip install --upgrade pip`)  
      to prevent build failures for `cryptography`, `opencv-python`, and `PyQt6`.

- **Neutral, non-competitive practice framing**:
    - Practice instructions rewritten to emphasise calibration and rhythm rather than performance.  
    - Per-block practice feedback now uses qualitative, neutral wording instead of numeric accuracy.  
    - Removes encouragement of compensatory “score chasing”, preserving fatigue-induction validity.

- **Sequential practice target rate updated**:  
  Raised from **0.4 → 0.5** to align practice with main induction design and with the scientific description in the documentation.

- **Display configuration hardened**:  
  Window background colour is now explicitly set to RGB `[-1, -1, -1]` in `params.json`.  
  Prevents white-on-white rendering issues reported by reviewer.

### Fixed
- 
**Sequential Practice Logic Conflict**:  
  Resolved an edge case in `WAND_practice_plateau.py` where a participant achieving high stability *and* high accuracy simultaneously would trigger the plateau exit condition instead of the intended difficulty promotion. The logic now prioritizes level promotion over plateau termination.
  **Miscellaneous text visibility issues**:
    - Forced explicit black background resolves systems where `"black"` is interpreted inconsistently by PsychoPy.

### Removed
- **Legacy on-screen scoreboards**:
    - `show_summary()` and `show_final_summary()` removed from the main task flow.  
      (These previously showed accuracy/d′ during the experiment.)
    - Participants now receive only neutral instructional text; all metrics are saved to CSV.

- **Obsolete inline metric helpers**:
    - Old versions of `calculate_accuracy_and_rt`, `calculate_dprime`, `calculate_A_prime`,  
      and `calculate_sequential_nback_summary` in `WAND_full_induction.py` have been deprecated  
      in favour of the centralised analysis module.

---

---
## [1.0.3] - 2025-10-03
### Added
- `wand_common.py` shared module centralising utilities (grid drawing, jitter, colour mapping, error hook, sequence generators). Both `WAND_full_induction.py` and `WAND_practice_plateau.py` import from this module.

### Changed
- **External configuration**: Most participant-facing text and key parameters are now in `config/text_en.json` and `config/params.json` to satisfy reviewer feedback and improve maintainability.
- **Sequential N-back**: Clarified target generation to keep ~50% targets among eligible trials with a maximum of two consecutive matches.
- **Sequential practice (slow mode)**: Slow-mode block length set to 60 trials to match other tasks.
- **Docs**: README streamlined and task descriptions clarified.

### Fixed
- Minor logging wording in dual-task notes (no functional impact).

### Removed
- Small cleanup of unused variables / redundant lines across scripts for clarity.


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