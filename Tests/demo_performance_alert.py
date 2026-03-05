"""
Demo: Performance Monitor — warn_then_terminate flow.

Shows two scenarios:
  1. Block 3: d-prime flag (focus instruction)
  2. Block 4: lapse flag with count (you missed X trials)

Usage:
    py -3.10 Tests/demo_performance_alert.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from psychopy import core, visual

from wand_nback.common import load_config
from wand_nback.performance_monitor import (
    MonitorConfig,
    check_sequential_block,
    handle_flag,
    reset_flag_count,
)

# Load config so get_text() has the english text strings
load_config()
reset_flag_count()

config = MonitorConfig(
    enabled=True,
    dprime_threshold=1.0,
    missed_response_threshold=0.20,
    action="warn_then_terminate",
)

win = visual.Window(size=[900, 600], fullscr=False, color="black", units="pix")

# --- Block 3: lapse flag (first flag = warning) ---
info = visual.TextStim(win, text="Block 3 complete.", color="white", height=24)
info.draw()
win.flip()
core.wait(2.0)

# Simulating 45 lapses out of 162 trials (27% lapse rate)
check3 = check_sequential_block(
    {
        "Overall D-Prime": 1.50,
        "Correct Responses": 104,
        "Incorrect Responses": 13,
        "Lapses": 45,
    },
    block_number=3,
    config=config,
)
d3 = handle_flag(win, "Sequential 2-back", 3, check3, config, n_back_level=2)
print(f"[Block 3] Flagged: lapses. Decision: {d3}")

# --- Block 4: d-prime flag (second flag = terminate) ---
info2 = visual.TextStim(win, text="Block 4 complete.", color="white", height=24)
info2.draw()
win.flip()
core.wait(2.0)

check4 = check_sequential_block(
    {
        "Overall D-Prime": 0.44,
        "Correct Responses": 73,
        "Incorrect Responses": 54,
        "Lapses": 5,
    },
    block_number=4,
    config=config,
)
d4 = handle_flag(win, "Sequential 2-back", 4, check4, config, n_back_level=2)
print(f"[Block 4] Flagged: d-prime. Decision: {d4}")

win.close()
core.quit()
