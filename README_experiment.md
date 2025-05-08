WAND Fatigue Induction Experiment
Overview
This document provides detailed instructions for running the WAND_full_induction.py script, which implements a novel fatigue induction protocol based on the Working-memory Adaptive-fatigue with N-back Difficulty (WAND) model. The protocol induces active mental fatigue over approximately 65–70 minutes using sequential, spatial, and dual N-back tasks with adaptive difficulty, linear timing compression, and mini-distractors. For a broader overview of the WAND suite, including design principles, see the main README.md.
Requirements

Python 3.8+
PsychoPy (version 2024.2.1 or later)
SciPy

Installation
Set up a virtual environment and install dependencies as described in the main README.md. Then, install the required packages:
pip install psychopy==2024.2.1 scipy

File Structure

WAND_full_induction.py: Main script for the fatigue induction experiment.
Abstract Stimuli/apophysis/: Folder containing at least 24 complex 3D fractal PNG images generated with Apophysis software for N-back tasks (included in the repository).
data/: Output directory for results (auto-created during execution).

Practice Protocol Integration
The WAND suite includes WAND_practice_plateau.py, which calibrates a participant's N-back capacity before the fatigue induction phase. This script runs adaptive N-back blocks until performance variability is ≤7% across three out of five consecutive blocks, typically taking 25–45 minutes. A dual-threshold system requires:

Level 2: Accuracy between 65% and 82%.
Level 3: Transition from Level 2 by achieving an average accuracy above 82% for two consecutive blocks, then maintaining ≤7% variability across three out of five blocks.This classifies participants as "normal" or "high" performers. Run this script first and review its results (e.g., calibrated N-back level) in the data/ directory to set the initial difficulty for WAND_full_induction.py. For detailed instructions, see the main README.md.

Running the Script
To run the full experiment (approximately 65–70 minutes, including short breaks):
python WAND_full_induction.py

The script will:

Prompt for a Participant ID and N-back level (2 or 3, based on practice calibration).
Execute five sequential (5 minutes each), four spatial (4.5 minutes each), and four dual N-back (4.5 minutes each) blocks with adaptive difficulty and mini-distractors.
Save results per block and at the end in the data/ directory (e.g., participant_<ID>_n<level>_results.csv).

Monitor Configuration
Update the MONITOR_NAME variable in WAND_full_induction.py to match your lab’s monitor profile in PsychoPy’s Monitor Center for accurate stimulus sizing. The default is 'testMonitor'. See PsychoPy’s documentation for setup instructions.
EEG Notes
EEG triggers are implemented as placeholders. To enable, set EEG_ENABLED = True in the script and modify the send_trigger function to interface with your EEG hardware (e.g., via a parallel port). Currently, send_trigger includes a 5ms delay as a dummy operation. Future integration will target N2 and P3 ERP components to assess cognitive control decline.
Data Saving
Results are saved twice for redundancy:

After each block (e.g., participant_<ID>_n<level>_Block_1_results.csv).
At the end of the experiment (e.g., participant_<ID>_n<level>_results.csv).

This ensures data integrity if the experiment is interrupted, a design choice made after data loss during piloting.
Subjective Measures
Participants complete subjective ratings at the start and every 15 minutes during the experiment, using a 1–8 Likert scale (1 = "not at all", 8 = "extremely"):

How mentally fatigued do you feel right now?
How effortful do you find the task at this moment?
Do you currently find your mind wandering or becoming distracted?
How overwhelmed do you feel by the task demands right now?

These measures, saved in the data/ directory (e.g., participant_<ID>_subjective_<timestamp>.csv), complement behavioural data to assess active fatigue.
Testing
For testing, use the Dummy_Run.py script to verify setup and CSV logging. Run it with:
python Dummy_Run.py

Results are saved in the data/ directory (e.g., participant_dummy_n2_TestRun_<timestamp>.csv).
License
This project is licensed under the MIT License. See LICENSE.txt for details.
Citation
If you use this script in your research, please cite:Mangan, B. (2025). WAND Practice and Fatigue Induction Suite. GitHub Repository: brodie_neuro/WAND-practice-and-fatigue-induction.
