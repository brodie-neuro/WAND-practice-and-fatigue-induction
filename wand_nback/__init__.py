"""
WAND Package - Working-memory Adaptive-fatigue with N-back Difficulty

Pip-installable package for the WAND cognitive fatigue induction protocol.

Version: 1.2.0
Author: Brodie E. Mangan
"""

__version__ = "1.2.0"
__author__ = "Brodie E. Mangan"

# Analysis exports
from wand_nback.analysis import (
    calculate_A_prime,
    calculate_dprime,
    summarise_sequential_block,
)

# Core utility exports
from wand_nback.common import get_param, get_text, load_config, load_gui_config

__all__ = [
    "__version__",
    "__author__",
    "load_config",
    "load_gui_config",
    "get_param",
    "get_text",
    "summarise_sequential_block",
    "calculate_dprime",
    "calculate_A_prime",
]
