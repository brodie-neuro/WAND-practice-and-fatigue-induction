# Tests/test_smoke.py
import sys
import os

# ensure the project root (where WAND_practice_plateau.py lives) is on sys.path:
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir)))



import csv
import os

import pytest

# Import your real practice script:
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
    Smoke‐test for run_block():
      1) Monkey‐patch enough of `practice` so that no PsychoPy window is needed.
      2) Stub out `run_sequential_nback_practice(...)` to return a fixed result.
      3) Call run_block() so that it invokes our stub and then writes a CSV.
      4) Verify that:
         - accuracy ∈ [0,100]
         - CSV file exists
         - the data‐row in CSV matches (level, block)
    """

    # ─── Step 1: Monkey‐patch file‐writing globals so that CSV_PATH points to a temp folder ───
    temp_data = tmp_path / "data"
    temp_data.mkdir()

    practice.PARTICIPANT_ID = "testpid"
    practice.data_dir = str(temp_data)
    practice.CSV_PATH = os.path.join(str(temp_data), "seq_testpid.csv")
    practice._last_logged_level = None

    # Provide a bare‐minimum DummyWin so that nothing PsychoPy‐related is actually used.
    class DummyWin:
        def __init__(self):
            # These two attributes are sometimes read by PsychoPy internals:
            self.units = "pix"
            self.size = (800, 600)

        def getContentScaleFactor(self):
            return 1

        def flip(self):
            pass

        def close(self):
            pass

    practice.win = DummyWin()

    # ─── Step 2: Stub out `run_sequential_nback_practice` itself ───
    # We do not want any actual PsychoPy drawing. So we override that function
    # to return a fixed (accuracy, errors, lapses, avg_rt).
    def fake_run_sequential_nback_practice(
        n, num_trials, target_percentage, display_duration, isi
    ):
        # Return e.g. 80% accuracy, 2 errors, 1 lapse, average RT = 0.5
        return (80.0, 2, 1, 0.5)

    practice.run_sequential_nback_practice = fake_run_sequential_nback_practice

    # ─── Step 3: Define a small helper (run_block) that our test calls ───
    def run_block(practice_mod, n_level: int, num_trials: int, block_no: int):
        """
        1) Calls practice_mod.run_sequential_nback_practice(...) (which is now stubbed).
        2) Calls practice_mod.log_seq_block(...) to append one CSV row.
        3) Returns whatever the stub returned.
        """
        accuracy, errors, lapses, avg_rt = practice_mod.run_sequential_nback_practice(
            n=n_level,
            num_trials=num_trials,
            target_percentage=0.5,
            display_duration=0.8,
            isi=1.0,
        )

        practice_mod.log_seq_block(
            level=n_level,
            block_no=block_no,
            accuracy=accuracy,
            errors=errors,
            lapses=lapses,
        )

        return accuracy, errors, lapses, avg_rt

    # ─── Step 4: Invoke run_block(...) ───
    accuracy, errors, lapses, avg_rt = run_block(
        practice_mod=practice,
        n_level=n_level,
        num_trials=num_trials,
        block_no=block_no,
    )

    # ─── Step 5: Assertions ───

    #  5a) The "stubbed" accuracy should be within [0, 100]
    assert 0.0 <= accuracy <= 100.0

    #  5b) CSV file must exist
    assert os.path.isfile(practice.CSV_PATH), "CSV file was not created"

    #  5c) Read all rows and find the first "data row" of length 5
    with open(practice.CSV_PATH, newline="") as f:
        reader = csv.reader(f)
        all_rows = list(reader)

    # The CSV should have:
    #   • A provenance header (e.g. ["Created 2025-06-06 12:34", "Participant", "testpid"])
    #   • A header row ["level","block","accuracy_pct","errors","lapses"]
    #   • Possibly a blank line (if level changed)
    #   • Then at least one data‐row of length 5: [ level, block, "80.00", "2", "1" ]
    data_rows = [
        row for row in all_rows if len(row) == 5 and row[0] not in ("level", "")
    ]
    assert data_rows, f"No 5‐column data row found in {practice.CSV_PATH!r}"

    first_data = data_rows[0]
    # Check that level and block match
    assert int(first_data[0]) == n_level
    assert int(first_data[1]) == block_no

    # Check string‐formatted accuracy (we returned 80.0)
    # It should appear as "80.00" (two decimal places are formatted by log_seq_block).
    assert first_data[2].startswith(
        "80"
    ), f"Expected accuracy ~80, got {first_data[2]!r}"
