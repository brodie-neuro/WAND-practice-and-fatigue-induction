# Tests/test_script.py
import csv
import os
import sys

import pytest

# This path modification is still needed so Python can find your script
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# This import is now completely safe because the main script's
# startup code is protected by the `if __name__ == "__main__"` block.
import WAND_practice_plateau as practice


@pytest.mark.parametrize(
    "n_level, num_trials, block_no",
    [
        (2, 1, 1),
        (2, 10, 1),
        (3, 5, 2),
    ],
)
def test_run_block_creates_csv(mocker, tmp_path, n_level, num_trials, block_no):
    """
    Tests the data logging logic after refactoring the main script.
    """
    # ─── 1. Override global variables in the imported module ───
    temp_data = tmp_path / "data"
    temp_data.mkdir()

    practice.PARTICIPANT_ID = "testpid"
    practice.CSV_PATH = os.path.join(str(temp_data), "seq_testpid.csv")
    practice._last_logged_level = None

    # ─── 2. Use mocker to replace the real experiment function with a fake one ───
    # This instantly returns predictable data for our test.
    mocker.patch(
        "WAND_practice_plateau.run_sequential_nback_practice",
        return_value=(80.0, 2, 1, 0.5),
    )

    # ─── 3. Run only the logic we want to test ───
    accuracy, errors, lapses, avg_rt = practice.run_sequential_nback_practice(
        n=n_level, num_trials=num_trials
    )
    practice.log_seq_block(
        level=n_level,
        block_no=block_no,
        accuracy=accuracy,
        errors=errors,
        lapses=lapses,
    )

    # ─── 4. Check if the logging function worked correctly ───
    assert os.path.isfile(practice.CSV_PATH)
    with open(practice.CSV_PATH, newline="") as f:
        reader = csv.reader(f)
        all_rows = list(reader)
    data_rows = [
        row for row in all_rows if len(row) == 5 and row[0] not in ("level", "")
    ]
    assert data_rows
    first_data = data_rows[0]
    assert int(first_data[0]) == n_level
    assert int(first_data[1]) == block_no
