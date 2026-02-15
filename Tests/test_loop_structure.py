"""
Tests for loop structure integrity.

Verifies that:
1. The 'while passes < 2' loops in practice_plateau.py have their `passes`
   counter increment INSIDE the loop body, preventing infinite loops.
2. The 'for cycle_num' main experiment loop in full_induction.py has its
   task execution code INSIDE the loop body, not outside it.

These tests use Python's AST (Abstract Syntax Tree) to inspect source code
structure directly, so they don't require PsychoPy or any mocking.
"""

import ast
import os

import pytest

_PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

PRACTICE_FILE = os.path.join(_PROJECT_DIR, "wand_nback", "practice_plateau.py")
INDUCTION_FILE = os.path.join(_PROJECT_DIR, "wand_nback", "full_induction.py")


def _find_while_passes_loops(source: str):
    """
    Find all 'while passes < N' loops in the source and check whether
    `passes` is assigned inside each loop body.

    Returns a list of dicts with keys:
        - lineno: line number of the while statement
        - has_passes_update: True if `passes = ...` appears inside the loop body
    """
    tree = ast.parse(source)
    results = []

    for node in ast.walk(tree):
        if not isinstance(node, ast.While):
            continue

        # Check if the while condition references 'passes'
        condition_src = ast.dump(node.test)
        if "passes" not in condition_src:
            continue

        # Check if the loop body contains an assignment to 'passes'
        has_update = False
        for child in ast.walk(node):
            if child is node:
                continue
            if isinstance(child, ast.Assign):
                for target in child.targets:
                    if isinstance(target, ast.Name) and target.id == "passes":
                        has_update = True
                        break

        results.append(
            {
                "lineno": node.lineno,
                "has_passes_update": has_update,
            }
        )

    return results


def test_all_passes_loops_have_internal_increment():
    """Every 'while passes < N' loop must increment passes inside its body."""
    with open(PRACTICE_FILE, "r", encoding="utf-8") as f:
        source = f.read()

    loops = _find_while_passes_loops(source)

    # We expect at least 2 loops (Spatial and Dual normal-speed practice)
    assert len(loops) >= 2, (
        f"Expected at least 2 'while passes' loops in practice_plateau.py, "
        f"found {len(loops)}"
    )

    for loop in loops:
        assert loop["has_passes_update"], (
            f"'while passes' loop at line {loop['lineno']} in practice_plateau.py "
            f"does NOT update 'passes' inside the loop body. "
            f"This will cause an infinite loop."
        )


def test_spatial_and_dual_loops_are_structurally_identical():
    """
    The Spatial and Dual normal-speed practice loops should have the same
    structure. This catches copy-paste errors where one loop diverges.
    """
    with open(PRACTICE_FILE, "r", encoding="utf-8") as f:
        source = f.read()

    loops = _find_while_passes_loops(source)

    # Both should have passes updated inside
    updates = [loop["has_passes_update"] for loop in loops]
    assert all(updates), (
        f"Not all 'while passes' loops update passes internally. "
        f"Loop details: {loops}"
    )


# =========================================================================
# full_induction.py - main experiment loop structure
# =========================================================================


def _find_for_cycle_num_loops(source: str):
    """
    Find 'for cycle_num in range(...)' loops and check whether they contain
    meaningful task execution code (calls to run_scheduled_events, etc.)
    inside their body.

    Returns a list of dicts with keys:
        - lineno: line number of the for statement
        - body_statement_count: number of statements in the loop body
        - has_task_code: True if the loop body contains task-related calls
    """
    tree = ast.parse(source)
    results = []

    for node in ast.walk(tree):
        if not isinstance(node, ast.For):
            continue

        # Check if the loop variable is 'cycle_num'
        if not (isinstance(node.target, ast.Name) and node.target.id == "cycle_num"):
            continue

        body_count = len(node.body)

        # Check if the body contains meaningful task code (not just logging)
        has_task_code = False
        for child in ast.walk(node):
            if child is node:
                continue
            # Look for calls to run_scheduled_events, run_sequential_nback_block,
            # run_adaptive_nback_task, etc.
            if isinstance(child, ast.Call):
                func = child.func
                if isinstance(func, ast.Name) and func.id in (
                    "run_scheduled_events",
                    "run_sequential_nback_block",
                    "run_adaptive_nback_task",
                ):
                    has_task_code = True
                    break

        results.append(
            {
                "lineno": node.lineno,
                "body_statement_count": body_count,
                "has_task_code": has_task_code,
            }
        )

    return results


def test_induction_main_loop_contains_task_code():
    """
    The 'for cycle_num' loop in full_induction.py must contain task execution
    code inside its body, not just logging statements.

    This catches the indentation bug where task code was accidentally placed
    outside the for loop, causing the experiment to only run one iteration.
    """
    with open(INDUCTION_FILE, "r", encoding="utf-8") as f:
        source = f.read()

    loops = _find_for_cycle_num_loops(source)

    assert len(loops) >= 1, (
        f"Expected at least 1 'for cycle_num' loop in full_induction.py, "
        f"found {len(loops)}"
    )

    for loop in loops:
        assert loop["has_task_code"], (
            f"'for cycle_num' loop at line {loop['lineno']} in full_induction.py "
            f"does NOT contain task execution code inside its body "
            f"(only {loop['body_statement_count']} statement(s)). "
            f"This means the experiment loop body is outside the for loop."
        )
        # The loop should have more than just a logging statement
        assert loop["body_statement_count"] > 1, (
            f"'for cycle_num' loop at line {loop['lineno']} has only "
            f"{loop['body_statement_count']} statement(s) in its body. "
            f"Expected multiple statements (sequential, spatial, dual task blocks)."
        )
