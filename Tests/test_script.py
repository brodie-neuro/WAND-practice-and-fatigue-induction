import csv
import os
import sys

import pytest

# Add project root to the path so we can import the main script
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# --- The Definitive Mocking Fix ---
# This code MUST run before `import WAND_practice_plateau`.
# It creates fake modules and inserts them into Python's cache. When your main
# script tries to `from psychopy import visual`, Python finds our fake object
# instead of the real one and uses it. This prevents any graphics, windows,
# or event loops from ever starting.
from unittest.mock import MagicMock

sys.modules["psychopy"] = MagicMock()
sys.modules["psychopy.visual"] = MagicMock()
sys.modules["psychopy.event"] = MagicMock()
sys.modules["psychopy.core"] = MagicMock()
# --- End of Fix ---

# This import is now safe. It will not create a window or hang.
import WAND_practice_plateau as practice


@pytest.mark.parametrize(
    "n_level, num_trials, block_no",
    [
        (2, 1, 1),
        (2, 10, 1),
        (3, 5, 2),
    ],
)
def test_log_seq_block_writes_csv(mocker, tmp_path, n_level, num_trials, block_no):
    """
    Tests that the `log_seq_block` function works correctly in isolation.
    """
    # 1. Set up a temporary folder for the test's output
    temp_data = tmp_path / "data"
    temp_data.mkdir()

    # 2. Override the global variables that the logging function will use
    practice.PARTICIPANT_ID = "testpid"
    practice.CSV_PATH = os.path.join(str(temp_data), "test_log.csv")
    practice._last_logged_level = None

    # 3. Use mocker to stop the test from trying to find the `image_files`
    #    list, which is normally created when the real script runs.
    mocker.patch("WAND_practice_plateau.image_files", ["image1.png", "image2.png"])

    # 4. We don't need to test the full experiment, only the logging.
    #    So, we directly call the function we want to test with some fake data.
    practice.log_seq_block(
        level=n_level, block_no=block_no, accuracy=85.5, errors=3, lapses=1
    )

    # 5. Check if the file was created and contains the correct data
    assert os.path.isfile(practice.CSV_PATH)
    with open(practice.CSV_PATH, newline="") as f:
        rows = list(csv.reader(f))

    data_rows = [row for row in rows if len(row) == 5 and row[0] not in ("level", "")]
    assert len(data_rows) == 1, "Expected exactly one data row"

    logged_data = data_rows[0]
    assert int(logged_data[0]) == n_level
    assert int(logged_data[1]) == block_no
