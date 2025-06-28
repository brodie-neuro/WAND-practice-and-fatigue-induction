# WAND — Working-memory Adaptive-fatigue with N-back Difficulty
*Current release: v1.0.2 – see CHANGELOG for details*  
### A Practice-and-Fatigue-Induction Suite

## Overview

WAND consists of Four PsychoPy scripts designed to induce and measure "active" mental fatigue by targeting working memory systems. This suite provides a standardised protocol for calibrating individual N-Back Capacity (proxy for working memory capacity) and then systematically inducing cognitive fatigue.

## Task Components

| Script | Purpose | Typical Duration |
|--------|---------|------------------|
| `WAND_practice_plateau.py` | Calibrates individual N-Back capacity (a proxy for working memory capacity) through adaptive difficulty until performance stabilises (≤7% variability) | 20–60 minutes |
| `WAND_full_induction.py` | Induces mental fatigue through progressive loading of non-verbal working memory circuits via Sequential, Spatial, and Dual N-back tasks | 65-70 minutes (including breaks) |
| `Dummy_Run.py` | Lightweight script to verify sequential task logic and data logging | 3–5 minutes |
| `Dummy_Run_Practice.py` | Lightweight script to verify sequential task functionality and data logging |2-3 minutes |

New in v1.0.2

This version introduces several key fixes and methodological improvements alongside preparations for our JOSS submission.

- **Improved Practice Algorithm**: The sequential practice task now includes a one-block "grace period" when difficulty increases to 3-back, ensuring a fairer assessment of participant performance.
- **Streamlined Experiment Summary**: The final summary screen has been updated to only show essential block-by-block metrics for a cleaner post-experiment experience.
- **Bug Fix**: Corrected a visual bug where the background grid would disappear during the spatial n-back task.
- **Automated Testing**: A formal test suite and Continuous Integration (CI) have been implemented to ensure code reliability.
**Docstrings** Improved docstring formatting across all scripts.

New in v1.0.1 

Slow-phase on-ramp (1.5 × timings) lets low-performers find rhythm before normal speed

Participant-ID dialog  →  per-block CSV logger (data/seq_<PID>.csv)

## Design Principles

| Feature | Purpose |
|---------|---------|
| **Task Modalities** | Sequential, Spatial, and Dual N-back tasks tax the same fronto-parietal networks in complementary ways |
| **Adaptive Difficulty** | Automatic level adjustment within block, and linear timing compression maintain high-level difficulty for each participant *Spatial and Dual only* |
| **Mini-distractors** | Brief (200ms) visual disruptions probe inhibitory failure (13× per 164 trial block); compare A′/RT pre- vs post-distractor |
| **Practice Plateau** | Ensures performance stability (≤7% variability over 3 consecutive blocks) to distinguish fatigue effects from learning |
| **Balanced Target:Lure Ratio** | 50:50 ratio prevents response bias and ensures d′/A′ metrics reflect true sensitivity |
| **Enhanced Engagement** | Lapse-cue system and colour-coded N-levels reduce disengagement and maintain motivation |

## Task Algorithms

### 1. Sequential N-back
- Image list of N = 24 abstract PNGs
- Sequence of 164 trials per block
- Baseline timings: 0.80 s presentation, 1.00 s ISI
- Targets ≈ 50% of eligible positions, never > 2 in a row
- If n == 3, 30% of non-target slots copy the 2-back item (misleading lure)

### 2. Spatial N-back
- 12-position radial grid (clock face)
- Timing compression applied per block:
  - Presentation = 1.00s − 0.03s·block (min 0.85s)
  - ISI = 1.00s − 0.05s·block (min 0.775s)

### 3. Dual N-back
- 3 × 3 grid + image overlay
- Timing compression per normal‑speed block (same slope as Spatial) presentation = 1.00 s − 0.03 s·block       - (min 0.85 s)ISI = 1.20 s − 0.05 s·block   (min 1.05 s)

## Key Features for Fatigue Induction

| Feature | Effect |
|---------|--------|
| **Adaptive N-back** | Dynamically adjusts N-back level to maintain a challenging but manageable performance load. See README_experiment.md for specific thresholds. |
| **Timing compression** | -30ms presentation and -50ms ISI per block forces sustained vigilance |
| **Grey background grid** | 100px spacing, 20% opacity creates irrelevant visual texture participants must actively ignore |
| **Mini-distractor flashes** | 200 ms white square inserted pseudo-randomly throughout each block (max 13 per block, minimum 6 trials apart) |
| **Misleading trials** | 30% of trials in 3-back match 2-back item to probe proactive vs reactive control |

## Subjective Measurements

During the fatigue induction phase, participants complete brief self-report assessments approximately every 15 minutes:

- Perceived mental fatigue
- Task effort
- Mind wandering
- Task overwhelm

Responses are collected using 1–8 Likert scales and stored alongside behavioral data in the `/data/` directory.

## Installation

It is highly recommended to install WAND and its dependencies in a Python virtual environment.

1.  **Clone the Repository:**
    ```bash
    git clone https://github.com/brodie-neuro/WAND-practice-and-fatigue-induction.git
    cd WAND-practice-and-fatigue-induction
    ```

2.  **Create and Activate a Virtual Environment:**
    ```bash
    # Create the environment
    python -m venv .venv

    # Activate it (run this command each time you work on the project)
    # On Windows:
    .venv\Scripts\activate
    # On macOS/Linux:
    source .venv/bin/activate
    ```

3.  **Install All Dependencies:**
    This command reads the `requirements.txt` file and installs the exact package versions needed to run the experiment.
    ```bash
    pip install -r requirements.txt
    ```

## Usage

Once the installation is complete, you can run the main experiment script from your terminal:

```bash
python WAND_practice_plateau.py
## Post-installation check:

- Run `Dummy_Run.py` to verify the environment is configured correctly and dependencies are working before launching a full experiment.
- Ensure a `data/` folder exists in the project root. This is where output files (performance and subjective ratings) are saved. The script will attempt to create this if it does not exist, but you may create it manually.

## Running the Scripts

```bash
# Quick start with fresh RNG and distractors ON
python WAND_practice_plateau.py

# Fully reproducible run, no distractors
python WAND_full_induction.py --seed 1234 --distractors off

# Test run and saving confirmation 
python Dummy_Run.py

```
### Testing

This project uses the pytest framework for automated testing. The tests are located in the /Tests directory and are automatically run on every push and pull request using GitHub Actions.

Running Tests Manually

To run the test suite locally after installation, navigate to the repository's root directory and run the following command:

Bash

python -m pytest
This will discover and run all tests in the Tests/ directory and report the results.

### Hot-keys During an Experiment

| Key | Effect |
|-----|--------|
| Esc | Emergency abort → closes window, exits Python |
| 5 | Skip remainder of current demo/block and jump to the next stage |

## File Structure

| File | Description |
|------|-------------|
| `WAND_practice_plateau.py` | Practice protocol for pre-fatigue calibration via adaptive N-back loops |
| `WAND_full_induction.py` | Full fatigue induction sequence with escalating task load |
| `Dummy_Run.py` | Quick verification script for sequential N-back logic and CSV output |
 `Dummy_Run_Practice.py`| Quick verification script for sequential N-back logic and CSV output |
| `requirements.txt` | Runtime dependencies |
| `README.md` | Project overview and usage instructions |
| `README_experiment.md` | Detailed documentation on experimental design and implementation |
| `LICENSE.txt` | MIT License |
| `Abstract Stimuli/apophysis/` | PNG image stimuli for N-back tasks |

## Stimuli Setup

This suite requires image files located in the "Abstract Stimuli/apophysis" folder. Ensure:

- The folder is in the same directory as the script
- It contains at least 24 PNG files

Repository structure should be:
```
/
├── WAND_practice_plateau.py
├── WAND_full_induction.py
├── Dummy_Run.py
├── Dummy_Run_Practice.py
├── requirements.txt
├── requirements_dev.txt
├── README.md
├── README_experiment.md
├── LICENSE.txt
├── Abstract Stimuli/
│   └── apophysis/
│       ├── apophysis1.png
│       ├── apophysis2.png
│       └── ...
```

### Non-Verbal Cognitive Processing

The WAND suite employs a carefully curated set of 24 complex 3D fractal shapes generated using Apophysis software. These stimuli are not arbitrary visual elements, but a strategically designed cognitive tool with specific implications:

- **Minimised Verbal Encoding**: Shapes are deliberately complex and abstract, making them difficult to verbalise
- **Targeted Neural Activation**: Primarily engages right-hemisphere frontoparietal networks
- **Reduced Linguistic Interference**: Limits phonological loop activation
- **Visuospatial Working Memory Focus**: Ensures tasks target non-verbal cognitive circuits

This approach addresses a critical methodological challenge in cognitive fatigue research: preventing participants from masking performance declines through verbal processing strategies.

---

*WAND: Working-memory Adaptive-fatigue with N-back Difficulty*
