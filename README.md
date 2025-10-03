# WAND — Working-memory Adaptive-fatigue with N-back Difficulty
*Current release: v1.0.3 — see `CHANGELOG.md` for details*

### A Practice and Fatigue Induction Suite

## Overview

WAND is a set of PsychoPy scripts that calibrate N-back capacity and then induce active cognitive fatigue by sustained loading of non-verbal working memory. The suite provides a standardised protocol you can reuse and configure through external JSON files.

## Task Components

| Script                     | Purpose                                                                                     | Typical Duration |
|---------------------------|---------------------------------------------------------------------------------------------|------------------|
| `WAND_practice_plateau.py`| Calibrates individual N-back capacity through adaptive difficulty until performance stabilises (≤ 7 percent variability) | 20–60 minutes |
| `WAND_full_induction.py`  | Induces cognitive fatigue with Sequential, Spatial, and Dual N-back tasks                   | 65–70 minutes including breaks |
| `Dummy_Run.py`            | Lightweight script to verify sequential task logic and CSV logging                          | 3–5 minutes |
| `Dummy_Run_Practice.py`   | Lightweight script to verify sequential task functionality and CSV logging                  | 2–3 minutes |

## What is new in v1.0.3

- Shared utilities module. Common routines live in `wand_common.py` and are imported by the main scripts. This removes duplication and keeps behaviour consistent.
- External configuration. Parameters and participant-facing text are in `config/params.json` and `config/text_en.json`. You can adjust the experiment without editing Python.
- Sequential target generation. Targets are generated at approximately 50 percent of eligible trials with a cap of two consecutive matches.
- Documentation polish. Docstrings and README wording aligned across scripts.
- Sequential practice slow-mode. Increased from 20 to 60 trials instead of 90 so slow-mode block duration matches the others.

See `CHANGELOG.md` for earlier versions.

## Design Principles

| Feature                     | Purpose |
|----------------------------|---------|
| Task modalities            | Sequential, Spatial, and Dual N-back tasks tax the same fronto parietal networks in complementary ways |
| Adaptive difficulty        | Automatic level adjustment and linear timing compression maintain appropriate challenge for Spatial and Dual |
| Mini distractors           | Brief 200 ms visual flashes probe inhibitory control and vigilance within blocks |
| Practice plateau           | Requires stability ≤ 7 percent variability over three consecutive blocks to separate fatigue from learning |
| Balanced target ratio      | 50 to 50 target to non-target prevents response bias and supports sensitivity metrics |
| Engagement supports        | Lapse cues and colour coded N levels help maintain attention without confounding the tasks |

## Task Algorithms

### 1. Sequential N-back
- 24 abstract PNG images
- 164 trials per full block
- Baseline timings: 0.80 s presentation, 1.00 s ISI
- Targets at approximately 50 percent of eligible positions, never more than 2 in a row

### 2. Spatial N-back
- 12 position radial grid (clock face)
- Timing compression per normal speed block  
  - Presentation: 1.00 s minus 0.03 s times block number, minimum 0.85 s  
  - ISI: 1.00 s minus 0.05 s times block number, minimum 0.775 s

### 3. Dual N-back
- 3 by 3 grid with image overlay
- Timing compression per normal speed block  
  - Presentation: 1.00 s minus 0.03 s times block number, minimum 0.85 s  
  - ISI: 1.20 s minus 0.05 s times block number, minimum 1.05 s

## Key Features for Fatigue Induction

| Feature                | Effect |
|-----------------------|--------|
| Adaptive N-back       | Maintains a challenging but manageable load. Thresholds are documented in `README_experiment.md`. |
| Timing compression    | Per block reduction of presentation and ISI forces sustained vigilance |
| Background grid       | 100 px spacing and 20 percent opacity grey texture that must be ignored to increase control demands |
| Mini distractors      | 200 ms white square inserted pseudo randomly, with spacing constraints |

## Subjective Measurements

During the induction phase, participants complete brief self reports roughly every 15 minutes:
- Perceived mental fatigue
- Task effort
- Mind wandering
- Task overwhelm

Responses use 1 to 8 Likert scales and are saved alongside behavioural data in `./data/`.

## Installation

Use a Python virtual environment.

1. Clone the repository
```bash
git clone https://github.com/brodie-neuro/WAND-practice-and-fatigue-induction.git
cd WAND-practice-and-fatigue-induction
```

2. Create and activate a virtual environment
```bash
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS or Linux
source .venv/bin/activate
```

3. Install dependencies
```bash
pip install -r requirements.txt
```
Tested on Windows, Python 3.8. See `requirements.txt` for pins.

## Usage

Once installation is complete:

```bash
python WAND_practice_plateau.py
```

### Post installation check
- Run `Dummy_Run.py` to verify the environment and basic logging before a full experiment.
- Ensure a `data/` folder exists. Scripts will try to create it if missing.

### Running the scripts

```bash
# Quick start with fresh RNG and distractors ON
python WAND_practice_plateau.py

# Fully reproducible run, no distractors
python WAND_full_induction.py --seed 1234 --distractors off

# Test run and saving confirmation
python Dummy_Run.py
```

### Hot keys during an experiment

| Key | Effect |
|-----|--------|
| Esc | Emergency abort. Closes window and exits Python |
| 5   | Skip remainder of current demo or block and jump to the next stage |

## Configuration

All parameters are in `config/params.json`. All participant facing text is in `config/text_en.json`. The code reads values through `wand_common.get_param` and `wand_common.get_text`.

### Window and appearance

Edit `config/params.json`:

```json
{
  "window": {
    "fullscreen": false,
    "size": [1650, 1000],
    "monitor": "testMonitor",
    "background_color": "black",
    "color_space": "rgb",
    "use_fbo": true
  },
  "colors": {
    "default": "white",
    "levels": { "2": "#0072B2", "3": "#E69F00", "4": "#009E73" }
  },
  "timing": { "jitter_fraction": 0.10 }
}
```

If you prefer a taller window, set `"size": [1650, 1200]`.

### Other parameters

Key tunables used by the scripts and `wand_common.py`:

| Key                                   | Type           | Purpose |
|---------------------------------------|----------------|---------|
| `practice.speed_default`              | string         | Slow or normal initial speed in practice |
| `practice.speed_multiplier.normal`    | float          | Multiplier for normal speed |
| `practice.speed_multiplier.slow`      | float          | Multiplier for slow speed |
| `sequential.target_percentage`        | float          | Target rate for sequential N-back |
| `sequential.max_consecutive_matches`  | int            | Cap on consecutive true matches |
| `spatial.target_percentage`           | float          | Target rate for spatial N-back |
| `dual.target_rate`                    | float          | Target rate for dual N-back matches |
| `grid.spacing`                        | int            | Background grid spacing in pixels |
| `grid.color`                          | string         | Background grid colour name or hex |
| `grid.opacity`                        | float          | Background grid opacity 0 to 1 |

## Accessibility

- Default colours use a palette that remains distinct under common colour vision deficiency: blue `#0072B2` for level 2, orange `#E69F00` for level 3, teal `#009E73` for level 4.
- Feedback also uses symbols such as tick and cross, so colour is not the only cue. You can change colours in `params.json`.

## File Structure

| File                         | Description |
|------------------------------|-------------|
| `WAND_practice_plateau.py`   | Practice protocol for pre-fatigue calibration via adaptive N-back loops |
| `WAND_full_induction.py`     | Full fatigue induction sequence with escalating task load |
| `Dummy_Run.py`               | Quick verification script for sequential N-back logic and CSV output |
| `Dummy_Run_Practice.py`      | Quick verification script for sequential N-back logic and CSV output |
| `wand_common.py`             | Shared helpers and configuration loader |
| `config/params.json`         | Parameters for window, colours, timing, targets, and more |
| `config/text_en.json`        | Participant facing text strings |
| `requirements.txt`           | Runtime dependencies |
| `README.md`                  | Project overview and usage instructions |
| `README_experiment.md`       | Experimental design and implementation details |
| `LICENSE.txt`                | MIT License |
| `Abstract Stimuli/apophysis/`| PNG image stimuli for N-back tasks |
| `data/`                      | Output directory for logs and summaries |

## Stimuli Setup

The suite expects images in `Abstract Stimuli/apophysis`. Ensure:
- The folder is next to the scripts
- It contains at least 24 PNG files

Repository sketch:

```
/
├── WAND_practice_plateau.py
├── WAND_full_induction.py
├── Dummy_Run.py
├── Dummy_Run_Practice.py
├── wand_common.py
├── config/
│   ├── params.json
│   └── text_en.json
├── Abstract Stimuli/
│   └── apophysis/
│       ├── apophysis1.png
│       ├── apophysis2.png
│       └── ...
├── requirements.txt
├── README.md
├── README_experiment.md
├── LICENSE.txt
└── data/
```

## Testing

This project uses pytest. To run the test suite locally:

```bash
python -m pytest
```

## License

MIT License. See `LICENSE.txt`.

---
*WAND: Working-memory Adaptive-fatigue with N-back Difficulty*
