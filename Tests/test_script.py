# Tests/test_script.py
import sys
import os
import csv
import pytest

# This line ensures Python can find your WAND_practice_plateau.py script
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# --- The Mocking Fix ---
from unittest.mock import MagicMock

# Create a fake object for the 'visual' module
mock_visual = MagicMock()

# IMPORTANT FIX: Configure the fake Window object. Tell it that when its
# .size attribute is accessed, it should return a tuple (800, 600).
mock_visual.Window.return_value.size = (800, 600)

# Now, replace the real psychopy modules with our fakes
sys.modules['psychopy'] = MagicMock()
sys.modules['psychopy.visual'] = mock_visual  # Use our configured mock
sys.modules['psychopy.event'] = MagicMock()
sys.modules['psychopy.core'] = MagicMock()
# --- End of Fix ---

# Now this import is safe
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
    def fake_run_sequential_nback_practice(*args, **kwargs):
        return (80.0, 2, 1, 0.5)

    practice.run_sequential_nback_practice = fake_run_sequential_nback_practice

    # ─── 4. Run only the logic we want to test ───

    # Get the fake data from our stubbed function
    accuracy, errors, lapses, avg_rt = practice.run_sequential_nback_practice(
        n=n_level, num_trials=num_trials, target_percentage=0.5,
        display_duration=0.8, isi=1.0,
    )
    # Call the real logging function with the fake data
    practice.log_seq_block(
        level=n_level, block_no=block_no, accuracy=accuracy,
        errors=errors, lapses=lapses,
    )

    # ─── 5. Check if the logging function did its job correctly ───
    assert os.path.isfile(practice.CSV_PATH)

    with open(practice.CSV_PATH, newline="") as f:
        reader = csv.reader(f)
        all_rows = list(reader)

    data_rows = [row for row in all_rows if len(row) == 5 and row[0] not in ("level", "")]
    assert data_rows, f"No data row found in {practice.CSV_PATH}"

    first_data = data_rows[0]
    assert int(first_data[0]) == n_level
    assert int(first_data[1]) == block_no