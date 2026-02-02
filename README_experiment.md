WAND Fatigue Induction Experiment

## Overview
This document provides detailed instructions for running the Full Induction protocol (`wand_nback/full_induction.py`), which implements a sophisticated cognitive fatigue induction protocol based on the Working-memory Adaptive-fatigue with N-back Difficulty (WAND) model. The protocol induces active cognitive fatigue over approximately 65â€“70 minutes using sequential, spatial, and dual N-back tasks with adaptive difficulty in the default setting, linear timing compression, and mini-distractors. For a broader overview of the WAND protocol, including design principles, see the main README.md.

## Requirements

Python 3.10+ (recommended) or Python 3.8+
PsychoPy (version 2024.1.4 or later)
SciPy

## Installation

WAND is now pip-installable. The recommended installation method is:

```bash
pip install git+https://github.com/brodie-neuro/WAND-practice-and-fatigue-induction.git
```

Alternatively, clone the repository and install locally:

```bash
git clone https://github.com/brodie-neuro/WAND-practice-and-fatigue-induction.git
cd WAND-practice-and-fatigue-induction
pip install .
```

After installation, launch the GUI with: `wand-launcher`

## File Structure

- `wand_nback/launcher.py`: GUI wizard for configuring and launching experiments (recommended entry point).
- `wand_nback/full_induction.py`: Main script for the fatigue induction experiment.
- `wand_nback/practice_plateau.py`: Practice calibration script.
- `wand_nback/block_builder.py`: Visual drag-and-drop block ordering interface.
- `wand_nback/common.py`: Shared utilities and configuration loader.
- `wand_nback/analysis.py`: Signal Detection Theory metrics and analysis functions.
- `wand_nback/config/`: Directory containing `params.json` (settings) and `text_en.json` (instructions).
- `wand_nback/stimuli/apophysis/`: Folder containing 24 complex 3D fractal PNG images.
- `data/`: Output directory for results (auto-created during execution).

## Practice Protocol Integration 

Before running the main fatigue induction protocol, use wand-practice to calibrate each participantâ€™s N-back capacity. The practice script now includes:

Slow-phase (Speed-Gate): Practice begins with 60-trial blocks at slow speed (1.5Ã— longer timing) until the first block reaches â‰¥65% accuracy, then auto-switches to normal speed. This prevents early participant overwhelm and allows a gentle familiarisation.

Per-phase Speed Selection: Before each task phase (Spatial, Dual, Sequential), participants can select normal or slow timing for the first practice block.

Global Skip Key: Pressing 5 skips the remainder of any demo or practice block (useful during piloting or if a participant struggles).

Startup Wizard: At launch, the experimenter can set the RNG seed and toggle 200 ms distractor flashes (optional command-line flags are still supported).

Participant ID Prompt & Logger: The script now prompts for participant ID and saves Sequential practice block data as data/seq_<ID>.csv.

## Calibration Logic:

The N-back level is adjusted based on a rolling average of the last two blocks' accuracy:

Initial Competency: Participants must first achieve â‰¥65% accuracy on two consecutive blocks at Level 2.

Level Increase (2 â†’ 3): If the rolling average accuracy rises above 82% for two consecutive blocks, the participant advances to Level 3.

Level Decrease (3 â†’ 2): If the rolling average accuracy at Level 3 falls below 70%, the participant is moved back to Level 2.

Classification: â€œnormalâ€ or â€œhighâ€ performer, used to set initial difficulty in the induction script.

## Main Induction: Adaptive Difficulty
During the main induction protocol, the difficulty of the Spatial and Dual N-back tasks adapts based on performance. Each 4.5-minute block is divided into three sub-blocks, and the N-back level is reassessed and can change after each one. The rules are as follows:

Level Increase: If accuracy within a sub-block is â‰¥82%, the N-back level increases by 1 (up to a maximum of 4).

Level Decrease: If accuracy is â‰¤65%, the N-back level decreases by 1 (but will never go below level 2).

This creates a stable performance window between 65% and 82%, ensuring the task remains challenging but manageable to maintain a state of high cognitive load.

## Running the Script
To run the full experiment (approximately 65â€“70 minutes, including short breaks):

```bash
wand-induction
```

The script will:
Prompt for a Participant ID and N-back level (2 or 3, based on practice calibration).
Execute five sequential (5 minutes each), four spatial (4.5 minutes each), and four dual N-back (4.5 minutes each) blocks with adaptive difficulty and sub-perceptional time compression (Spatial and Dual) and mini-distractors (Sequential).
Save results per block and at the end in the data/ directory (e.g., participant_<ID>_n<level>_results.csv).

## Monitor Configuration
For accurate stimulus sizing, update the monitor settings in `config/params.json` to match your labâ€™s monitor profile (from PsychoPyâ€™s Monitor Center).

Edit the `"window"` section:
```json
"window": {
  "monitor": "myLabMonitor",
  "size": [1920, 1080],
  "fullscreen": true,
  ...
}

## EEG Notes
EEG triggers are fully configurable via `config/params.json`. Set `"eeg": {"enabled": true}` and configure your parallel port address, trigger duration, and custom trigger codes for all event types (stimulus onset, responses, distractors, block markers). See the `eeg` section in `params.json` for the complete list of configurable triggers.

## Data Saving
Results are saved twice for redundancy:

After each block (e.g., participant_<ID>_n<level>_Block_1_results.csv).
At the end of the experiment (e.g., participant_<ID>_n<level>_results.csv).

This ensures data integrity if the experiment is interrupted, a design choice made after data loss during piloting.

## Subjective Measures
Participants complete subjective ratings at the start and every 15 minutes during the experiment, using a 1â€“8 Likert scale (1 = "not at all", 8 = "extremely"):

How mentally fatigued do you feel right now?
How effortful do you find the task at this moment?
Do you currently find your mind wandering or becoming distracted?
How overwhelmed do you feel by the task demands right now?

These responses are **integrated into the main results CSV** (`participant_<ID>_n<level>_results.csv`) at the end of the experiment.

## Testing

The project includes two forms of tests:

- **User Verification**: To quickly check that your environment is set up correctly and that the script can write data, run the quicktest:

    ```bash
    wand-quicktest
    ```

- **Scientific Validation (Unit Tests)**: For validating the internal logic (e.g., Signal Detection metrics), a formal test suite is located in the `/Tests` directory. This suite uses `pytest` to feed known data patterns into the analysis engine and assert that the outputs are correct.

    To run the validation suite:
    ```bash
    python -m pytest
    ```
    *Test results are saved in `Tests/results/`.*


## License

This project is licensed under the MIT License. See LICENSE.txt for details.

## Citation

If you use this software in your research, please cite the JOSS paper.

*(A placeholder will be generated upon acceptance, but you can use this format):*
> Mangan, B. E., (2025). WAND: A Modular Software Suite for Cognitive Fatigue Research. Journal of Open Source Software, X(XX), XXXX. https://doi.org/XX.XXXXX/joss.XXXXX
