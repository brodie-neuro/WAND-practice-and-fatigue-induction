# WAND ‑ Practice‑and‑Fatigue‑Induction Suite  
*Working‑memory Adaptive‑fatigue with N‑back Difficulty*

Two PsychoPy scripts that together **induce, measure, and explain “active” mental fatigue** 

| Script | Purpose | Typical run‑time |
|--------|---------|------------------|
| **`WAND‑practice‑plateau.py`** | Calibrate individual working‑memory capacity.  Adaptive blocks cycle until performance variability ≤ 7 % (plateau). | ≈ 25-45 min |
| **`WAND‑full‑induction.py`** | Protocol that pushes the same circuits to overload via sequenced **Sequential → Spatial → Dual N‑back** blocks, progressive timing compression and mini‑distractors. | ≈ 90 min (including breaks) |

---

### Design Principles  
| Design element | Model purpose |
|----------------|---------------|
| **Sequential / Spatial / Dual tasks** | Tax the same fronto‑parietal–striatal networks in three complementary ways. |
| **Adaptive level & linear timing compression** | Keep each participant in “strain mode” (Hockey 2013) — hard but *just* doable. |
| **Mini‑distractors (180–220 ms, 10× per block)** | Probe inhibitory failure: compare A′ / RT pre‑ vs post‑distractor. |
| **Practice plateau (≤ 7 % var over 3 / 5 blocks)** | Strip out learning effects so later drops are genuine fatigue. |
| **Balanced 50 % target : lure** | Removes conservative response bias; d′/A′ reflect sensitivity, not guessing. |
| **Lapse‑cue & colour‑coded N‑levels** | Prevent silent disengagement; sustain engagement without external rewards. |

---

## 2 Installation (Python 3.8.x)

```powershell
python -m venv venv
# Windows
venv\Scripts\activate
# macOS / Linux
source venv/bin/activate

pip install -r requirements.txt
