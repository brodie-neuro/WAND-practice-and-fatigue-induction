"""
Tests for loop structure integrity in WAND scripts.

Uses Python's AST to verify that critical loops have correct indentation
and contain the expected task execution code. This catches bugs where
code is accidentally placed outside a loop body.
"""

import ast
import os

import pytest

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INDUCTION_FILE = os.path.join(BASE_DIR, "wand_nback", "full_induction.py")
PRACTICE_FILE = os.path.join(BASE_DIR, "wand_nback", "practice_plateau.py")


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
            f"does not contain task execution code in its body "
            f"(only {loop['body_statement_count']} statements found). "
            f"This suggests task code is incorrectly indented outside the loop."
        )


def test_induction_main_loop_body_not_trivial():
    """
    The 'for cycle_num' loop body must have more than just 1-2 statements.
    A trivially small body suggests task code accidentally fell outside the loop.
    """
    with open(INDUCTION_FILE, "r", encoding="utf-8") as f:
        source = f.read()

    loops = _find_for_cycle_num_loops(source)

    for loop in loops:
        assert loop["body_statement_count"] > 2, (
            f"'for cycle_num' loop at line {loop['lineno']} has only "
            f"{loop['body_statement_count']} statements in body. "
            f"Expected more (sequential + events + spatial/dual tasks)."
        )


def test_induction_file_parses_cleanly():
    """full_induction.py must parse without syntax errors."""
    with open(INDUCTION_FILE, "r", encoding="utf-8") as f:
        source = f.read()
    # This will raise SyntaxError if the file has issues
    ast.parse(source)
