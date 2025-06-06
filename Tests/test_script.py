# Tests/test_script.py
import csv
import os
import sys

import pytest

# This line ensures Python can find your WAND_practice_plateau.py script
# by adding the project's root folder to the path.
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# --- The Mocking Fix ---
# This is the most important part. We trick Python by creating fake, empty
# modules. When your script tries to `import psychopy.visual`, Python finds
# our harmless fake object first and stops, never loading the real library.
# This prevents any windows from being created or any errors related to graphics.
from unittest.mock import MagicMock

sys.modules["psychopy"] = MagicMock()
sys.modules["psychopy.visual"] = MagicMock()
sys.modules["psychopy.event"] = MagicMock()
sys.modules["psychopy.core"] = MagicMock()
# --- End of Fix ---

# Now, this import is safe. It will load your script's logic, but any
# PsychoPy calls within it will go to our fake objects and do nothing.
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
    # ─── 1. Set up a temporary folder for the test's output ───
    temp_data = tmp_path / "data"
    temp_data.mkdir()

    # ─── 2. Override global variables in your script to point to our test folder ───
    practice.PARTICIPANT_ID = "testpid"
    practice.CSV_PATH = os.path.join(str(temp_data), "seq_testpid.csv")
    practice._last_logged_level = None

    # ─── 3. Replace the real experiment function with a simple fake one ("stub") ───
    # This fake function doesn't run any trials; it just instantly returns
    # predictable data for us to test the logging part of the code.
    def fake_run_sequential_nback_practice(*args, **kwargs):
        return (80.0, 2, 1, 0.5)

    practice.run_sequential_nback_practice = fake_run_sequential_nback_practice

    # ─── 4. Run only the logic we want to test ───

    # Call the fake function to get our test data
    accuracy, errors, lapses, avg_rt = practice.run_sequential_nback_practice(
        n=n_level,
        num_trials=num_trials,
        target_percentage=0.5,
        display_duration=0.8,
        isi=1.0,
    )
    # Call the REAL logging function with the FAKE data
    practice.log_seq_block(
        level=n_level,
        block_no=block_no,
        accuracy=accuracy,
        errors=errors,
        lapses=lapses,
    )

    # ─── 5. Check if the logging function did its job correctly ───
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
