"""
WAND Package - Working-memory Adaptive-fatigue with N-back Difficulty

Pip-installable package for the WAND cognitive fatigue induction protocol.

Version: 1.1.1
Author: Brodie E. Mangan
"""

__version__ = "1.1.1"
__author__ = "Brodie E. Mangan"

# Core utility exports
from wand_nback.common import (
    load_config,
    load_gui_config,
    get_param,
    get_text,
)

# Analysis exports
from wand_nback.analysis import (
    summarise_sequential_block,
    calculate_dprime,
    calculate_A_prime,
)

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
