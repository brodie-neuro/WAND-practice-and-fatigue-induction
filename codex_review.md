# WAND Performance Monitor & Quicktest Refinement: Codex Review

**Date:** 2026-02-28  
**Scope:** Fixes to automated tests, implementation of the Performance Monitor (Edge Case Warnings), GUI logic refinements, and test suite mocking.

## 1. Quicktest Bug Fix ("5" Key Skip Logic)
During the initial work on the automated `wand-quicktest` suite, an issue was discovered where the automated keystroke simulation (mocking `event.getKeys` and `event.waitKeys`) was inadvertently pressing the `5` key. 
- In the main induction loops (`full_induction.py` and `practice_plateau.py`), pressing `5` is a hardcoded researcher interrupt used to instantly skip the current block.
- Because `quicktest` was randomly pressing `5`, blocks were aborting prematurely, leading to zero-division errors, truncated data, and test failures.
- **Resolution:** Modified the `_enable_quicktest_mode()` mock in `Tests/quicktest_induction.py` and `Tests/quicktest_practice.py` to explicitly exclude `"5"` and `"escape"` from the pool of randomly selected keys during automated smoke tests. This stabilized the automated test generation.

## 2. Performance Monitor ("Edge Case Warnings") Implementation
The Performance Monitor was fully developed to serve as a real-time, block-level safeguard against participant disengagement (e.g., repeatedly missing targets or just pressing buttons randomly).

### 2.1 Core Logic (`wand_nback/performance_monitor.py`)
- **Two-Tier System:**
  - **Sequential N-back (Fixed Difficulty):** Checks both D-Prime (accuracy relative to false alarms) against a threshold (default `1.0`) and Lapse Rate (missed responses) against a threshold (default `20%`).
  - **Adaptive N-back (Spatial/Dual):** Checks *only* the Lapse Rate against the threshold. D-Prime is ignored here because adaptive tasks naturally push participants to a failure point by design, confounding accuracy metrics.
- **Action Paradigm (`warn_then_terminate`):**
  - Designed fully automated standard operating logic to avoid experimenter bias.
  - **Flag #1:** Triggers a full-screen, participant-facing pause message dynamically localized via `wand_nback/config/text_en.json`. The message encourages the participant without alerting them that they are failing.
  - **Flag #2:** Triggers immediate, automated termination of the experiment session.
- **Auditory Alert (`_play_alert_sound`):** Added a system ping (`winsound.Beep` on Windows) to audibly notify the researcher in the lab if a participant receives a warning or termination.

### 2.2 GUI Launcher Integration & Settings (`launcher.py`)
- **Page 4/5 Addition:** Added a dedicated "Edge Case Warnings" page into the PySide GUI flow.
- Exposed thresholds for `Lapse Rate` and `D-Prime`.
- **Standardized Actions:** Removed the manual `prompt_researcher` option from the GUI to heavily enforce fully automated, objective termination metrics across the lab. Available options are now `warn_then_terminate`, `auto_terminate`, and `log_only`.
- **Workflow Optimization (Preset Bypassing):** Modified the `launcher.py` page-stepping logic. If a user selects a preset on Page 1 (e.g., `Standard_WAND_Protocol.json`), the launcher bypasses the "Block Builder" and "Edge Case Warnings" pages entirely, advancing directly to the "Mode Selection" page. This allows researchers to quickly launch standard procedures without repeatedly clicking through setup menus.

## 3. Wiring the Monitor to the Induction Loop
- Updated `wand_nback/full_induction.py` to directly instantiate its `MonitorConfig` using the dictionary returned by the GUI (`MonitorConfig.from_gui_config(load_gui_config())`), rather than relying on static defaults in `params.json`.
- Injected `check_sequential_block` and `check_adaptive_block` functions at the end of their respective trial loops to dynamically check performance and invoke `handle_flag`. When `handle_flag` returns `"terminate"`, the main induction loop `break`s, gracefully saving whatever data was collected.

## 4. End-to-End Testing & Mocking
To rigorously prove the new logic without needing humans to sit through an hour of shapes:
- **Test Presets:** Generated a `Quick_Fail_Demo.json` preset with hyper-fast timings and minimal trials to visibly trigger the UI warnings in real-time.
- **Automated Edge Case Test (`Tests/quicktest_edgecase.py`):** Created a CLI test script that intentionally mocks the PsychoPy `event.getKeys` interface to return *no input* (100% lapses). The script proves that `handle_flag` accurately throws a warning on Block 1 and auto-terminates on Block 2, printing detailed SDT/lapse metrics to standard output.
- **Muting Test Beeps:** Modified `Tests/test_performance_monitor.py` to mock out `_play_alert_sound()` using `MagicMock()`. Because the pytest suite checks edge cases in milliseconds, the `winsound.Beep` call was triggering a rapid flurry of obnoxious system dings. It is now safely silenced during CI execution.

## 5. Artifacts and File Touches
- `Tests/quicktest_induction.py`
- `Tests/quicktest_practice.py`
- `Tests/test_performance_monitor.py`
- `Tests/quicktest_edgecase.py` (NEW)
- `wand_nback/launcher.py`
- `wand_nback/performance_monitor.py`
- `wand_nback/full_induction.py`
- `wand_nback/config/presets/Quick_Fail_Demo.json` (NEW)
