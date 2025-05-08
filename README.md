# WAND ‑ Practice‑and‑Fatigue‑Induction Suite  
*Working‑memory Adaptive‑fatigue with N‑back Difficulty*

Three PsychoPy scripts that together **induce, measure “active” mental fatigue**  

| Script                       | Purpose                                                                                  | Typical run‑time        |
|-----------------------------|------------------------------------------------------------------------------------------|--------------------------|
| **`WAND_practice_plateau.py`**   | Calibrate individual N-back Capacity. Adaptive blocks cycle until performance variability ≤ 7 % (plateau). | ≈ 25–45 min             |
| **`WAND_full_induction.py`**     | Protocol that pushes the same circuits to overload via sequenced **Sequential → Spatial → Dual N‑back** blocks, progressive timing compression and mini‑distractors. | ≈ 70 min (including short breaks) |
| **`Dummy_Run.py`** | Lightweight script to test the sequential task logic and confirm CSV data logging integrity. | ≈ 3 min               |

---

### Design Principles  
| Design element                    | Model purpose                                                                 |
|----------------------------------|-------------------------------------------------------------------------------|
| **Sequential / Spatial / Dual tasks**       | Tax the same fronto‑parietal–striatal networks in three complementary ways.  |
| **Adaptive level & linear timing compression** | Keep each participant in “strain mode” (Hockey 2013) — hard but *just* doable. |
| **Mini‑distractors (180–220 ms, 10× per block)** | Probe inhibitory failure: compare A′ / RT pre‑ vs post‑distractor trials.          |
| **Practice plateau (≤ 7 % var over 3 / 5 blocks)** | Strip out learning effects so later drops are genuine fatigue.             |
| **Balanced 50 % target : lure**            | Removes conservative response bias; d′/A′ reflect sensitivity, not guessing. |
| **Lapse‑cue & colour‑coded N‑levels**       | Prevent silent disengagement; sustain engagement without external rewards.  |

---

## 2 Installation (Python 3.8.x)

```powershell
python -m venv venv
# Windows
venv\Scripts\activate
# macOS / Linux
source venv/bin/activate

pip install -r requirements.txt

### Files  

| File                  | Description                                                                 |
|-----------------------|-----------------------------------------------------------------------------|
| `WAND_practice_plateau.py`   | Practice protocol for pre‑fatigue calibration via adaptive N‑back loops |
| `WAND_full_induction.py`     | Full fatigue induction sequence with escalating task load               |
| `Dummy_Run.py` | Quick test script for verifying sequential N‑back logic and CSV output   |
| `requirements.txt`           | Minimal runtime dependencies for executing the main scripts              |
| `requirements_dev.txt`       | Extended development dependencies     |
| `README.md`                  | Overview of project, usage instructions                                 |
| `README_experiment.md`       | In-depth documentation for study setup, task design, and behavioural logic |
| `LICENSE.txt`                | MIT License (free to use, modify, and distribute)                        |
| `Abstract Stimuli/apophysis/` | PNG images used as stimuli in the N-back tasks |

## Images   
This script requires image files located in the "Abstract Stimuli/apophysis" folder relative to the script. Ensure this folder:
- Is in the same directory as the script.
- Contains at least 24 PNG files.
Clone the repository, and verify the structure:
- script.py
- Abstract Stimuli/
  - apophysis/
    - apophysis1.png
    - apophysis2.png
    - ...

## Citation
If you use this suite in your research, please cite:
Mangan, B. (2025). WAND Practice and Fatigue Induction Suite. GitHub Repository: brodie_neuro/WAND-practice-and-fatigue-induction.
