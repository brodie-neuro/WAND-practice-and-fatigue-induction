from pathlib import Path


def _module():
    import Tests.quicktest_induction as quicktest_induction

    return quicktest_induction


def test_pyproject_quicktest_entrypoint_targets_main():
    pyproject = Path(__file__).resolve().parents[1] / "pyproject.toml"
    text = pyproject.read_text(encoding="utf-8")
    assert 'wand-quicktest = "Tests.quicktest_induction:main"' in text


def test_main_defaults_to_automated_quicktest(monkeypatch):
    module = _module()
    called = {}

    monkeypatch.setattr(
        module, "_enable_quicktest_mode", lambda: called.setdefault("patched", True)
    )

    def fake_run_quicktest(n_back_level, num_trials, quicktest):
        called.update(
            {
                "level": n_back_level,
                "trials": num_trials,
                "quicktest": quicktest,
            }
        )

    monkeypatch.setattr(module, "run_quicktest", fake_run_quicktest)
    module.main([])

    assert called["patched"] is True
    assert called["level"] == 2
    assert called["trials"] == 10
    assert called["quicktest"] is True


def test_main_manual_mode_uses_manual_arguments(monkeypatch):
    module = _module()
    called = {}

    monkeypatch.setattr(
        module, "_enable_quicktest_mode", lambda: called.setdefault("patched", True)
    )

    def fake_run_quicktest(n_back_level, num_trials, quicktest):
        called.update(
            {
                "level": n_back_level,
                "trials": num_trials,
                "quicktest": quicktest,
            }
        )

    monkeypatch.setattr(module, "run_quicktest", fake_run_quicktest)
    module.main(["--manual", "--level", "3", "--trials", "12"])

    assert "patched" not in called
    assert called["level"] == 3
    assert called["trials"] == 12
    assert called["quicktest"] is False
