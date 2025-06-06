# Tests/test_script.py
import csv
import os
import sys

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from unittest.mock import MagicMock

# --- The Mocking Fix ---
# Create a fake object for the 'visual' module
mock_visual = MagicMock()

# IMPORTANT: Configure the fake Window object BEFORE it is used.
# Tell it that when its .size attribute is accessed, it must return a tuple.
mock_visual.Window.return_value.size = (800, 600)

# Now, replace the real psychopy modules with our fakes
sys.modules["psychopy"] = MagicMock()
sys.modules["psychopy.visual"] = mock_visual  # Use our configured mock
sys.modules["psychopy.event"] = MagicMock()
sys.modules["psychopy.core"] = MagicMock()
# --- End of Fix ---

import WAND_practice_plateau as practice


@pytest.mark.parametrize(
    "n_level, num_trials, block_no",
    [
        (2, 1, 1),
        (2, 10, 1),
        (3, 5, 2),
    ],
)
def test_run_block_creates_csv(tmp_path, n_level, num_trials, block_no):
    """
    Tests the data logging logic in isolation by mocking all
    graphical and blocking components of PsychoPy.
    """
    temp_data = tmp_path / "data"
    temp_data.mkdir()

    practice.PARTICIPANT_ID = "testpid"
    practice.CSV_PATH = os.path.join(str(temp_data), "seq_testpid.csv")
    practice._last_logged_level = None

    def fake_run_sequential_nback_practice(*args, **kwargs):
        return (80.0, 2, 1, 0.5)

    practice.run_sequential_nback_practice = fake_run_sequential_nback_practice

    accuracy, errors, lapses, avg_rt = practice.run_sequential_nback_practice(
        n=n_level,
        num_trials=num_trials,
        target_percentage=0.5,
        display_duration=0.8,
        isi=1.0,
    )

    practice.log_seq_block(
        level=n_level,
        block_no=block_no,
        accuracy=accuracy,
        errors=errors,
        lapses=lapses,
    )

    assert os.path.isfile(practice.CSV_PATH)

    with open(practice.CSV_PATH, newline="") as f:
        reader = csv.reader(f)
        all_rows = list(reader)

    data_rows = [
        row for row in all_rows if len(row) == 5 and row[0] not in ("level", "")
    ]
    assert data_rows, f"No data row found in {practice.CSV_PATH}"

    first_data = data_rows[0]
    assert int(first_data[0]) == n_level
    assert int(first_data[1]) == block_no
