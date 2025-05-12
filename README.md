# WAND — Working-memory Adaptive-fatigue with N-back Difficulty
### A Practice-and-Fatigue-Induction Suite

## Overview

WAND consists of three PsychoPy scripts designed to induce and measure "active" mental fatigue by targeting working memory systems. This suite provides a standardised protocol for calibrating individual N-Back Capacity (proxy for working memory capacity) and then systematically inducing cognitive fatigue.

## Task Components

| Script | Purpose | Typical Duration |
|--------|---------|------------------|
| `WAND_practice_plateau.py` | Calibrates individual working-memory capacity through adaptive difficulty until performance stabilizes (≤7% variability) | 20–45 minutes |
| `WAND_full_induction.py` | Induces mental fatigue through progressive overloading of working memory circuits via Sequential, Spatial, and Dual N-back tasks | 65-70 minutes (including breaks) |
| `Dummy_Run.py` | Lightweight script to verify sequential task logic and data logging | 3–5 minutes |

## Design Principles

| Feature | Purpose |
|---------|---------|
| **Task Modalities** | Sequential, Spatial, and Dual N-back tasks tax the same fronto-parietal networks in complementary ways |
| **Adaptive Difficulty** | Automatic level adjustment and linear timing compression maintain optimal challenge for each participant |
| **Mini-distractors** | Brief (180–220ms) visual disruptions probe inhibitory failure (13× per 164 trial block); compare A′/RT pre- vs post-distractor |
| **Practice Plateau** | Ensures performance stability (≤7% variability over 3-5 blocks) to distinguish fatigue effects from learning |
| **Balanced Target:Lure Ratio** | 50:50 ratio prevents response bias and ensures d′/A′ metrics reflect true sensitivity |
| **Enhanced Engagement** | Lapse-cue system and color-coded N-levels prevent disengagement and maintain motivation |

## Task Algorithms

### 1. Sequential N-back
- Image list of N = 24 abstract PNGs
- Sequence of 164 trials per block
- Targets ≈ 50% of eligible positions, never > 2 in a row
- If n == 3, 30% of non-target slots copy the 2-back item (misleading lure)

### 2. Spatial N-back
- 12-position radial grid (clock face)
- Timing compression applied per block:
  - Presentation = 1.00s − 0.03s·block (min 0.85s)
  - ISI = 1.00s − 0.05s·block (min 0.775s)

### 3. Dual N-back
- 3 × 3 grid + image overlay
- Same timing equation as Spatial but ISI starts at 1.2s

## Key Features for Fatigue Induction

| Feature | Effect |
|---------|--------|
| **Adaptive N-back** | Increases/decreases difficulty (↑n at ≥82% accuracy, ↓n at ≤65%) to maintain 70-80% performance range |
| **Timing compression** | -30ms presentation and -50ms ISI per block (capped at -150ms) forces sustained vigilance |
| **Grey background grid** | 100px spacing, 20% opacity creates irrelevant visual texture participants must actively ignore |
| **Mini-distractor flashes** | 180–220ms white square on 12-16 trial jitter causes inhibitory processes |
| **Misleading trials** | 30% of trials in 3-back match 2-back item to probe proactive vs reactive control |

## Subjective Measurements

During the fatigue induction phase, participants complete brief self-report assessments approximately every 15 minutes:

- Perceived mental fatigue
- Task effort
- Mind wandering
- Task overwhelm

Responses are collected using 1–8 Likert scales and stored alongside behavioral data in the `/data/` directory.

## Installation

WAND requires Python 3.8.x:

```bash
# Create and activate virtual environment
python -m venv venv

# Windows
venv\Scripts\activate
# macOS / Linux
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

## Running the Scripts

```bash
# Quick start with fresh RNG and distractors ON
python WAND_practice_plateau.py

# Fully reproducible run, no distractors
python WAND_practice_plateau.py --seed 1234 --distractors off
```

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
| `requirements.txt` | Runtime dependencies |
| `requirements_dev.txt` | Development dependencies |
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
├── Sequential_test_logger.py
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

## Citation

If you use WAND in a publication, please cite:

```
Mangan B., 2025. Working-memory Adaptive-fatigue with N-back Difficulty (WAND) – Practice-and-Induction Suite.
DOI: pending
```

---

*WAND: Working-memory Adaptive-fatigue with N-back Difficulty*
