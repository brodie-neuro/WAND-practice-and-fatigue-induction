#!/usr/bin/env python3
"""
wand_common.py

Shared helpers and configuration loader for the WAND tasks.

This module centralises:
  - JSON-based configuration loading (parameters and UI text)
  - Window and grid drawing helpers used across tasks
  - Small utilities (timing jitter, colour selection, sequence generators)
  - An error hook that renders a readable message in the PsychoPy window

It is safe to import from both the full induction and practice scripts.
"""

from __future__ import annotations

import inspect
import json
import logging
import os
import random
import sys
from typing import Any, Dict, Iterable, List, Optional, Tuple

from psychopy import core, visual  # type: ignore

# -----------------------------------------------------------------------------
# Module configuration and globals
# -----------------------------------------------------------------------------

LOGGER = logging.getLogger(__name__)

# Base directory discovery (works when frozen with PyInstaller)
if getattr(sys, "frozen", False):
    BASE_DIR = sys._MEIPASS  # type: ignore[attr-defined]
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Default config directory is "<repo>/config"
DEFAULT_CONFIG_DIR = os.path.join(BASE_DIR, "config")

# Module-level config caches (populated by load_config)
PARAMS: Dict[str, Any] = {}
TEXT: Dict[str, str] = {}

# Cached background grid lines
_GRID_LINES: List[visual.ShapeStim] = []


# =============================================================================
# Configuration loading
# =============================================================================


def _safe_read_json(path: str) -> Any:
    """
    Read JSON from a file path.

    Parameters
    ----------
    path : str
        Absolute path to a JSON file.

    Returns
    -------
    Any
        Decoded JSON value, or None on failure.

    Notes
    -----
    Errors are logged as warnings. The function does not raise on parse failure."""

    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        LOGGER.warning("Config file not found: %s", path)
    except Exception as exc:  # noqa: BLE001
        LOGGER.warning("Failed to parse JSON '%s': %s", path, exc)
    return None


def load_config(
    lang: str = "en",
    config_dir: Optional[str] = None,
    params_file: str = "params.json",
    text_file_tpl: str = "text_{lang}.json",
) -> Tuple[Dict[str, Any], Dict[str, str]]:
    """
    Load parameters and localised text from the config directory.

    Parameters
    ----------
    lang : str, optional
        Language code for the text bundle. Default is "en".
    config_dir : str, optional
        Directory containing config JSON files. If None, "<module>/config" is used.
    params_file : str, optional
        File name for the parameters JSON. Default is "params.json".
    text_file_tpl : str, optional
        Template for the localised text filename. "{lang}" is replaced with the
        value of the `lang` argument. Default is "text_{lang}.json".

    Returns
    -------
    Tuple[Dict[str, Any], Dict[str, str]]
        A tuple `(PARAMS, TEXT)`. Both are also stored in module globals so that
        downstream helpers do not need to pass them around.

    Notes
    -----
    Missing files are tolerated. In that case the respective cache remains empty
    and downstream helpers will fall back to sensible defaults."""
    global PARAMS, TEXT

    cfg_dir = config_dir or DEFAULT_CONFIG_DIR
    params_path = os.path.join(cfg_dir, params_file)
    text_path = os.path.join(cfg_dir, text_file_tpl.format(lang=lang))

    params = _safe_read_json(params_path) or {}
    text = _safe_read_json(text_path) or {}

    if not isinstance(params, dict):
        LOGGER.warning("Params JSON did not decode to a dict: %s", params_path)
        params = {}
    if not isinstance(text, dict):
        LOGGER.warning("Text JSON did not decode to a dict: %s", text_path)
        text = {}

    PARAMS = params
    TEXT = {str(k): str(v) for k, v in text.items()}
    return PARAMS, TEXT


def _get_from(obj: Dict[str, Any], path: str, default: Any = None) -> Any:
    """
    Traverse a nested dictionary using a dotted key path.

    Parameters
    ----------
    obj : Dict[str, Any]
        Source dictionary.
    path : str
        Dotted path, for example "practice.speed_multiplier.slow".
    default : Any, optional
        Value returned when a key is missing. Default is None.

    Returns
    -------
    Any
        The resolved value or `default`.
    """
    cur: Any = obj
    for part in path.split("."):
        if not isinstance(cur, dict) or part not in cur:
            return default
        cur = cur[part]
    return cur


def get_param(path: str, default: Any = None) -> Any:
    """
    Fetch a parameter from the `PARAMS` cache using a dotted path.

    Parameters
    ----------
    path : str
        Dotted key path, for example "practice.speed_multiplier.slow".
    default : Any, optional
        Value returned when the key is missing. Default is None.

    Returns
    -------
    Any
        The parameter value if present, otherwise `default`.

    See Also
    --------
    _get_from : Helper that implements dotted path traversal."""
    return _get_from(PARAMS, path, default)


def get_text(key: str, **fmt: Any) -> str:
    """
    Fetch a localised text string and optionally format it.

    Parameters
    ----------
    key : str
        Lookup key in the `TEXT` cache.
    **fmt
        Keyword substitutions applied via `str.format`.

    Returns
    -------
    str
        The resolved string. If the key is missing the key itself is returned."""
    raw = TEXT.get(key, key)
    try:
        return raw.format(**fmt)
    except Exception:  # noqa: BLE001
        return raw


# =============================================================================
# Error hook
# =============================================================================


def install_error_hook(win: visual.Window) -> None:
    """
    Install an exception hook that also renders a readable message in a window.

    On any uncaught exception this hook:
      1. Writes the traceback to stderr.
      2. Displays a concise error notice in the PsychoPy window.

    Parameters
    ----------
    win : psychopy.visual.Window
        The active PsychoPy window to draw into.

    Returns
    -------
    None
    """

    def _hook(etype, value, tb):
        import traceback  # local import to avoid a global dependency

        traceback.print_exception(etype, value, tb)
        try:
            msg = get_text("error_generic")
            visual.TextStim(
                win, text=msg, color="white", height=24, wrapWidth=900
            ).draw()
            win.flip()
        except Exception:
            pass

    sys.excepthook = _hook


# =============================================================================
# Grid helpers
# =============================================================================


def create_grid_lines(win: visual.Window) -> List[visual.ShapeStim]:
    """
    Construct a reusable, faint grid sized to the current window.

    The grid is cosmetic and intended as a neutral low-contrast background.

    Parameters
    ----------
    win : psychopy.visual.Window
        PsychoPy window to build the lines for.

    Returns
    -------
    List[visual.ShapeStim]
        Pre-built line stimuli ready to be drawn.

    Notes
    -----
    Spacing, colour and opacity can be customised via config:
      - grid.spacing
      - grid.color
      - grid.opacity
    """
    spacing = int(get_param("grid.spacing", 100))
    color = get_param("grid.color", "gray")
    opacity = float(get_param("grid.opacity", 0.2))

    w, h = win.size
    lines: List[visual.ShapeStim] = []

    # Vertical lines
    x = -w // 2
    while x <= w // 2:
        lines.append(
            visual.ShapeStim(
                win,
                vertices=[(x, -h // 2), (x, h // 2)],
                lineColor=color,
                opacity=opacity,
                closeShape=False,
                autoLog=False,
            )
        )
        x += spacing

    # Horizontal lines
    y = -h // 2
    while y <= h // 2:
        lines.append(
            visual.ShapeStim(
                win,
                vertices=[(-w // 2, y), (w // 2, y)],
                lineColor=color,
                opacity=opacity,
                closeShape=False,
                autoLog=False,
            )
        )
        y += spacing

    return lines


def set_grid_lines(lines: Iterable[visual.ShapeStim]) -> None:
    """
    Register line stimuli so `draw_grid` can draw them later.

    Parameters
    ----------
    lines : Iterable[visual.ShapeStim]
        The line stimuli to cache.

    Returns
    -------
    None
    """
    global _GRID_LINES
    _GRID_LINES = list(lines)


def draw_grid() -> None:
    """
    Draw the cached grid lines to the current back buffer.

    Returns
    -------
    None

    Notes
    -----
    You must call `set_grid_lines` once per session to cache the lines.
    This function does not call `win.flip()`.
    """
    for line in _GRID_LINES:
        line.draw()


def create_grid(
    win: visual.Window,
    grid_size: int,
    grid_length: float = 480,
) -> Tuple[List[visual.Rect], visual.Rect]:
    """
    Create a square grid of rectangles for Dual N-back tasks.

    Parameters
    ----------
    win : psychopy.visual.Window
        PsychoPy window to target.
    grid_size : int
        Number of rows and columns, for example 3 for a 3x3 grid.
    grid_length : float, optional
        Side length of the full grid square in pixels. Default is 480.

    Returns
    -------
    Tuple[List[visual.Rect], visual.Rect]
        A tuple `(cells, outline)` where `cells` is a list of cell rectangles
        and `outline` is one rectangle that frames the grid.
    """
    cell = grid_length / float(grid_size)
    top_left = (-grid_length / 2.0, grid_length / 2.0)

    cells: List[visual.Rect] = []
    for col in range(grid_size):
        for row in range(grid_size):
            cx = top_left[0] + (col + 0.5) * cell
            cy = top_left[1] - (row + 0.5) * cell
            cells.append(
                visual.Rect(
                    win,
                    width=cell,
                    height=cell,
                    pos=(cx, cy),
                    lineColor="white",
                    fillColor=None,
                )
            )

    outline = visual.Rect(
        win,
        width=grid_length,
        height=grid_length,
        pos=(0, 0),
        lineColor="white",
        fillColor=None,
        lineWidth=2,
    )
    return cells, outline


def display_grid(
    win: visual.Window,
    highlight_pos: Optional[int] = None,
    highlight: bool = False,
    n_level: Optional[int] = None,
    feedback_text: Optional[str] = None,
    lapse_feedback: Optional[str] = None,
) -> None:
    """
    Draw the radial 12-position grid, with optional highlight and messages.

    Parameters
    ----------
    win : psychopy.visual.Window
        PsychoPy window to draw on.
    highlight_pos : Optional[int], optional
        Index 0..11 on the radial grid to highlight. Default is None.
    highlight : bool, optional
        Whether to draw a filled highlight square at `highlight_pos`. Default is False.
    n_level : Optional[int], optional
        Current N-back level. Used for colour and the level label. Default is None.
    feedback_text : Optional[str], optional
        Short message to draw above the grid. Default is None.
    lapse_feedback : Optional[str], optional
        Short message in orange, drawn slightly higher than `feedback_text`. Default is None.

    Returns
    -------
    None
    """
    import math

    draw_grid()

    radius = 150
    num_positions = 12
    angles = [i * (360.0 / num_positions) for i in range(num_positions)]
    positions = [
        (radius * math.cos(math.radians(a)), radius * math.sin(math.radians(a)))
        for a in angles
    ]

    grid_color = get_level_color(n_level)

    # Fixation cross
    visual.TextStim(win, text="+", color="white", height=32).draw()

    # 12 squares around the circle
    for pos in positions:
        visual.Rect(
            win, width=50, height=50, pos=pos, lineColor=grid_color, lineWidth=2
        ).draw()

    # Optional highlight
    if highlight and highlight_pos is not None:
        visual.Rect(
            win, width=50, height=50, pos=positions[highlight_pos], fillColor="white"
        ).draw()

    # Optional texts
    if feedback_text:
        visual.TextStim(
            win, text=feedback_text, color=grid_color, height=24, pos=(0, 250)
        ).draw()

    if lapse_feedback:
        visual.TextStim(
            win, text=lapse_feedback, color="orange", height=24, pos=(0, 300)
        ).draw()

    if n_level:
        visual.TextStim(
            win,
            text=get_text("level_label", n=n_level),
            color="white",
            height=24,
            pos=(-450, 350),
            alignText="left",
        ).draw()


# =============================================================================
# Visual utilities
# =============================================================================


def get_level_color(n_level: Optional[int]) -> str:
    """
    Map an N-back level to a colour string with sensible fallbacks.

    Parameters
    ----------
    n_level : Optional[int]
        The current N-back level.

    Returns
    -------
    str
        A PsychoPy compatible colour value. Values are taken from
        `colors.levels` in params if available, otherwise a built-in mapping.
    """
    if n_level is None:
        return get_param("colors.default", "white")

    mapping = get_param("colors.levels", {})
    key = str(n_level)
    if isinstance(mapping, dict) and key in mapping:
        return mapping[key]

    return {2: "deepskyblue", 3: "orange", 4: "crimson"}.get(n_level, "white")


def get_jitter(base_seconds: float) -> float:
    """
    Return a jittered duration around a base value.

    The fraction is read from `timing.jitter_fraction` in params.
    Default is 0.10 which gives a range of plus or minus ten percent.

    Parameters
    ----------
    base_seconds : float
        The nominal duration in seconds.

    Returns
    -------
    float
        A random duration in the interval `[base*(1 - j), base*(1 + j)]`.
    """
    frac = float(get_param("timing.jitter_fraction", 0.10))
    low = base_seconds * (1.0 - frac)
    high = base_seconds * (1.0 + frac)
    return random.uniform(low, high)


# =============================================================================
# N-back sequence helpers
# =============================================================================


def print_debug_info(sequence, n: int, is_dual: bool = False) -> None:
    """
    Log where true N-back matches occur in a generated sequence.

    Parameters
    ----------
    sequence : list
        Stimulus sequence. For dual tasks this is a list of `(pos, image)` pairs.
    n : int
        N-back distance.
    is_dual : bool, optional
        Set True for a dual (position and image) sequence. Default is False.

    Returns
    -------
    None
    """
    if is_dual:
        match_positions = [
            i
            for i in range(n, len(sequence))
            if sequence[i][0] == sequence[i - n][0]
            and sequence[i][1] == sequence[i - n][1]
        ]
        summary = [pos[0] for pos in sequence]
    else:
        match_positions = [
            i for i in range(n, len(sequence)) if sequence[i] == sequence[i - n]
        ]
        summary = sequence

    response_positions = [i - (n - 1) for i in match_positions]
    LOGGER.debug("Sequence (summary): %s", summary)
    LOGGER.debug("Positive target positions: %s", response_positions)


def generate_dual_nback_sequence(
    num_trials: int,
    grid_size: int,
    n: int,
    image_files: List[str],
    target_rate: float = 0.5,
) -> Tuple[List[Tuple[int, int]], List[str]]:
    """
    Build a combined position and image sequence for Dual N-back and log it.

    Parameters
    ----------
    num_trials : int
        Total number of trials to generate.
    grid_size : int
        Width and height of the spatial grid, for example 3 for 3x3.
    n : int
        N-back distance for matches.
    image_files : List[str]
        Image filenames to sample from.
    target_rate : float, optional
        Proportion of eligible trials that should be true dual matches.
        Default is 0.5.

    Returns
    -------
    Tuple[List[Tuple[int, int]], List[str]]
        A tuple `(pos_seq, image_seq)` of equal length.

    Notes
    -----
    The target rate is enforced on the eligible range `[n, num_trials)`.
    """
    positions = [(x, y) for x in range(grid_size) for y in range(grid_size)]
    pos_seq = [random.choice(positions) for _ in range(num_trials)]
    image_seq = [random.choice(image_files) for _ in range(num_trials)]

    num_targets = int((num_trials - n) * target_rate)
    target_indices = random.sample(range(n, num_trials), num_targets)

    for idx in target_indices:
        pos_seq[idx] = pos_seq[idx - n]
        image_seq[idx] = image_seq[idx - n]

    combined_seq = list(zip(pos_seq, image_seq))
    print_debug_info(combined_seq, n, is_dual=True)
    return pos_seq, image_seq


def generate_positions_with_matches(
    num_positions: int,
    n: int,
    target_percentage: float = 0.5,
) -> List[int]:
    """
    Create a 12-position sequence with a requested fraction of true n-back repeats.

    Parameters
    ----------
    num_positions : int
        Total sequence length.
    n : int
        N-back distance.
    target_percentage : float, optional
        Fraction of trials after the first `n` that should be targets.
        Default is 0.5.

    Returns
    -------
    List[int]
        Ordered radial-grid indices in `0..11`.

    Notes
    -----
    Target indices are sampled uniformly from the eligible range `[n, num_positions)`.
    Non-targets are sampled freely. The function does not guarantee absence of
    incidental 2-back repeats when `n` is not equal to 2.
    """
    positions = list(range(12))
    seq: List[int] = [random.choice(positions) for _ in range(num_positions)]

    n_targets = int((num_positions - n) * float(target_percentage))
    n_targets = max(0, min(n_targets, max(0, num_positions - n)))

    if n_targets > 0:
        target_idxs = random.sample(range(n, num_positions), n_targets)
        for idx in target_idxs:
            seq[idx] = seq[idx - n]

    return seq


# =============================================================================
# Dual task stimulus builder
# =============================================================================


def display_dual_stimulus(
    win: visual.Window,
    pos: Tuple[int, int],
    image_file: str,
    grid_size: int,
    n_level: int,
    feedback_text: Optional[str] = None,
    return_stims: bool = False,
    return_stim: bool = False,
    preloaded_images: Optional[Dict[str, visual.ImageStim]] = None,
    image_dir: Optional[str] = None,
    grid_length: float = 480,
    include_highlight: bool = True,
    flip_if_drawn: bool = True,
):
    """
    Build and optionally draw the highlight and image for one Dual N-back trial.

    This function supports both practice and full induction call patterns.

    Parameters
    ----------
    win : psychopy.visual.Window
        PsychoPy window.
    pos : Tuple[int, int]
        `(col, row)` in `0..grid_size-1` for the grid.
    image_file : str
        File name key. Either a key in `preloaded_images` or a file name under `image_dir`.
    grid_size : int
        Grid dimension, for example 3.
    n_level : int
        N-back level, used for colour selection.
    feedback_text : Optional[str], optional
        Optional string drawn above the grid when the function draws immediately.
    return_stims : bool, optional
        If True, return `(highlight_rect, image_stim)` without drawing or flipping.
    return_stim : bool, optional
        If True, return only the `image_stim` without drawing or flipping.
    preloaded_images : Optional[Dict[str, visual.ImageStim]], optional
        Dict of preloaded `ImageStim` objects indexed by file name.
    image_dir : Optional[str], optional
        Folder path for images if not preloaded. If None, the function tries a
        caller global named `image_dir`, then falls back to a default folder.
    grid_length : float, optional
        Pixel length of the grid side. Default is 480.
    include_highlight : bool, optional
        If True, build a filled rect under the image that uses the level colour.
        Default is True.
    flip_if_drawn : bool, optional
        If True and the function draws, call `win.flip()` before returning.
        Default is True.

    Returns
    -------
    Union[Tuple[Optional[visual.Rect], visual.ImageStim], visual.ImageStim, None]
        One of:
        - `(highlight_rect, image_stim)` if `return_stims` is True
        - `image_stim` if `return_stim` is True
        - `None` if the function draws (and optionally flips) internally

    Notes
    -----
    Compatibility:
    - Full induction calls with `return_stims=True` and draws stims itself.
    - Practice calls with `return_stim=True` and draws the image itself.
    """
    # Compute cell centre for the target position
    cell_len = float(grid_length) / float(grid_size)
    top_left = (-grid_length / 2.0, grid_length / 2.0)
    cx = top_left[0] + pos[0] * cell_len + cell_len / 2.0
    cy = top_left[1] - pos[1] * cell_len - cell_len / 2.0

    # Level colour
    lvl_color = get_level_color(n_level)

    # Highlight rect under the image
    highlight_rect = None
    if include_highlight:
        highlight_rect = visual.Rect(
            win,
            width=cell_len,
            height=cell_len,
            pos=(cx, cy),
            lineColor=lvl_color,
            fillColor=lvl_color,
            lineWidth=2,
        )

    # Resolve image stim
    img_stim: Optional[visual.ImageStim] = None

    # 1) explicit preloaded dict
    if isinstance(preloaded_images, dict) and image_file in preloaded_images:
        img_stim = preloaded_images[image_file]
        img_stim.pos = (cx, cy)
        img_stim.size = (cell_len - 10, cell_len - 10)

    # 2) caller globals for a dict named preloaded_images_dual
    if img_stim is None:
        caller_globals = inspect.currentframe().f_back.f_globals  # type: ignore[attr-defined]
        caller_preloaded = caller_globals.get("preloaded_images_dual")
        if isinstance(caller_preloaded, dict) and image_file in caller_preloaded:
            img_stim = caller_preloaded[image_file]
            img_stim.pos = (cx, cy)
            img_stim.size = (cell_len - 10, cell_len - 10)

    # 3) fall back to loading from disk
    if img_stim is None:
        if image_dir is None:
            caller_globals = inspect.currentframe().f_back.f_globals  # type: ignore[attr-defined]
            image_dir = caller_globals.get("image_dir")
        if image_dir is None:
            image_dir = os.path.join(BASE_DIR, "Abstract Stimuli", "apophysis")

        path = (
            image_file
            if os.path.isabs(image_file)
            else os.path.join(image_dir, image_file)
        )
        img_stim = visual.ImageStim(
            win,
            image=path,
            pos=(cx, cy),
            size=(cell_len - 10, cell_len - 10),
        )

    # Return paths for the two scripts
    if return_stims:
        return highlight_rect, img_stim

    if return_stim:
        return img_stim

    # Draw now if neither return flag is set
    if highlight_rect is not None:
        highlight_rect.draw()
    img_stim.draw()

    if feedback_text:
        visual.TextStim(
            win, text=feedback_text, color="orange", height=24, pos=(0, 300)
        ).draw()

    if flip_if_drawn:
        win.flip()
    return None


# -----------------------------------------------------------------------------
# Public API
# -----------------------------------------------------------------------------

__all__ = [
    "BASE_DIR",
    "DEFAULT_CONFIG_DIR",
    "PARAMS",
    "TEXT",
    "load_config",
    "get_param",
    "get_text",
    "install_error_hook",
    "create_grid_lines",
    "set_grid_lines",
    "draw_grid",
    "display_grid",
    "create_grid",
    "get_level_color",
    "get_jitter",
    "generate_dual_nback_sequence",
    "generate_positions_with_matches",
    "print_debug_info",
    "display_dual_stimulus",
]
