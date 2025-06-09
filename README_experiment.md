WAND Fatigue Induction Experiment

## Overview
This document provides detailed instructions for running the WAND_full_induction.py script, which implements a novel fatigue induction protocol based on the Working-memory Adaptive-fatigue with N-back Difficulty (WAND) model. The protocol induces active mental fatigue over approximately 65–70 minutes using sequential, spatial, and dual N-back tasks with adaptive difficulty, linear timing compression, and mini-distractors. For a broader overview of the WAND suite, including design principles, see the main README.md.

## Requirements

Python 3.8.X
PsychoPy (version 2024.1.4 or later)
SciPy

## Installation

For a reproducible environment, it is highly recommended to use a virtual environment. Follow the setup and installation instructions in the main `README.md` file, which uses the `requirements.txt` file to install all necessary dependencies.

## File Structure

WAND_full_induction.py: Main script for the fatigue induction experiment.
Abstract Stimuli/apophysis/: Folder containing at least 24 complex 3D fractal PNG images generated with Apophysis software for N-back tasks (included in the repository).
data/: Output directory for results (auto-created during execution).

## Practice Protocol Integration 

Before running the main fatigue induction protocol, use WAND_practice_plateau.py to calibrate each participant’s N-back capacity. The practice script now includes:

Slow-phase (Speed-Gate): Practice begins with 60-trial blocks at slow speed (1.5× longer timing) until the first block reaches ≥65% accuracy, then auto-switches to normal speed. This prevents early participant overwhelm and allows a gentle familiarisation.

Per-phase Speed Selection: Before each task phase (Spatial, Dual, Sequential), participants can select normal or slow timing for the first practice block.

Global Skip Key: Pressing 5 skips the remainder of any demo or practice block (useful during piloting or if a participant struggles).

Startup Wizard: At launch, the experimenter can set the RNG seed and toggle 200 ms distractor flashes (optional command-line flags are still supported).

Participant ID Prompt & Logger: The script now prompts for participant ID and saves Sequential practice block data as data/seq_<ID>.csv.

## Calibration Logic:

Adaptive N-back blocks continue until accuracy variance is ≤7% across three out of five consecutive blocks.

Start at Level 2 (2-back): Require two consecutive blocks ≥65% accuracy.

If accuracy rises above 82% for two consecutive blocks, advance to Level 3 (3-back).

Classification: “normal” or “high” performer, used to set initial difficulty in the induction script.

After running the practice protocol, review the /data/ outputs. Enter the recommended N-back level (2 or 3) when prompted by WAND_full_induction.py.

## Running the Script
To run the full experiment (approximately 65–70 minutes, including short breaks):
python WAND_full_induction.py

The script will:

Prompt for a Participant ID and N-back level (2 or 3, based on practice calibration).
Execute five sequential (5 minutes each), four spatial (4.5 minutes each), and four dual N-back (4.5 minutes each) blocks with adaptive difficulty and sub-perceptional time compression (Spatial and Dual) and mini-distractors (Sequential).
Save results per block and at the end in the data/ directory (e.g., participant_<ID>_n<level>_results.csv).

## Monitor Configuration
Update the MONITOR_NAME variable in WAND_full_induction.py to match your lab’s monitor profile in PsychoPy’s Monitor Center for accurate stimulus sizing. The default is 'testMonitor'. See PsychoPy’s documentation for setup instructions.

## EEG Notes
EEG triggers are implemented as placeholders. To enable, set EEG_ENABLED = True in the script and modify the send_trigger function to interface with your EEG hardware (e.g., via a parallel port). Currently, send_trigger includes a 5ms delay as a dummy operation. Future integration will target N2 and P3 ERP components to assess cognitive control decline.

## Data Saving
Results are saved twice for redundancy:

After each block (e.g., participant_<ID>_n<level>_Block_1_results.csv).
At the end of the experiment (e.g., participant_<ID>_n<level>_results.csv).

This ensures data integrity if the experiment is interrupted, a design choice made after data loss during piloting.

## Subjective Measures
Participants complete subjective ratings at the start and every 15 minutes during the experiment, using a 1–8 Likert scale (1 = "not at all", 8 = "extremely"):

How mentally fatigued do you feel right now?
How effortful do you find the task at this moment?
Do you currently find your mind wandering or becoming distracted?
How overwhelmed do you feel by the task demands right now?

These measures, saved in the data/ directory (e.g., participant_<ID>_subjective_<timestamp>.csv), complement behavioural data to assess active fatigue.

## Testing

The project includes two forms of tests:

- **User Verification**: To quickly check that your environment is set up correctly and that the script can write data, run the lightweight dummy script:

    ```bash
    python Dummy_Run.py
    ```

- **Formal Test Suite**: For development and validation, a formal test suite using `pytest` is located in the `/Tests` directory. These tests validate the internal logic of the software. To run them, execute the following command from the project's root directory:

    ```bash
    python -m pytest
    ```


## License

This project is licensed under the MIT License. See LICENSE.txt for details.

## Citation

If you use this software in your research, please cite the JOSS paper.

*(A placeholder will be generated upon acceptance, but you can use this format):*
> Mangan, B. E., (2025). WAND: A Modular Software Suite for Cognitive Fatigue Research. Journal of Open Source Software, X(XX), XXXX. https://doi.org/XX.XXXXX/joss.XXXXX