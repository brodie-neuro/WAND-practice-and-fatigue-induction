WAND Fatigue Induction Experiment
Description
This script implements the Working-memory Adaptive-fatigue with N-back Difficulty (WAND) model for cognitive fatigue induction. It includes Sequential, Spatial, and Dual N-back tasks with adaptive difficulty and subjective measures.
Requirements

Python 3.8+
PsychoPy (version 2021.2.3 or later)
SciPy

Installation
pip install psychopy==2021.2.3 scipy

File Structure

wand_fatigue.py: Main experiment script
Abstract Stimuli/apophysis/: Folder containing PNG images (included in the repository)
data/: Output directory for results (auto-created)

Running the Script
python wand_fatigue.py

Monitor Configuration

Update MONITOR_NAME in the script to match your lab's monitor profile in PsychoPy's monitor center for accurate stimulus sizing. Default is 'testMonitor'.

EEG Notes

EEG triggers are placeholders. To enable, set EEG_ENABLED = True in the script and implement the send_trigger function with your hardware.

Data Saving

Results are saved twice: once per block and once at the end. This redundancy ensures data integrity in case of interruptions, a design choice made after data loss occurred during piloting on a computer.

Testing

To run in windowed mode for testing, set FULLSCREEN = False in the experiment settings at the top of the script.

For a quick dummy session (default 20 trials), launch with:

python wand_fatigue.py --test --level 2 --trials 20

where --level sets the N-back difficulty and --trials specifies the number of dummy trials.

License

Creative Commons Attribution 4.0 International (CC BY 4.0)

