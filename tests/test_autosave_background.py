"""Background autosave: off the frame loop, latest request wins, flushable."""
import threading

from ophthosim.autosave import BackgroundAutosave, load_autosave
from ophthosim.engine import Phase
from ophthosim.replay import ReplayGame

import surgeon_helpers as H


def test_latest_submission_is_written_and_finished_case_clears(tmp_path):
    path = tmp_path / "a.replay.jsonl"
    saver = BackgroundAutosave()
    g = ReplayGame("normal", 7, "standard")
    H.run_to(g, Phase.ENTRY)
    saver.submit(g, path)
    H.run_to(g, Phase.CAPSULE)
    saver.submit(g, path)
    assert saver.flush()
    assert load_autosave(path).snapshot() == g.snapshot()
    g.action("abort")
    saver.submit(g, path)
    assert saver.flush() and not path.exists()


def test_write_errors_never_reach_the_game(tmp_path):
    blocker = tmp_path / "file"
    blocker.write_text("x")
    saver = BackgroundAutosave()
    g = ReplayGame("normal", 7, "standard")
    saver.submit(g, blocker / "sub" / "a.jsonl")     # parent is a file: OSError
    assert saver.flush()


def test_submit_does_not_wait_for_the_disk(tmp_path, monkeypatch):
    import ophthosim.autosave as A
    gate = threading.Event()
    real = A._write
    monkeypatch.setattr(A, "_write", lambda target, text: (gate.wait(5), real(target, text)))
    saver = BackgroundAutosave()
    saver.submit(ReplayGame("normal", 7, "standard"), tmp_path / "a.jsonl")
    assert not saver.flush(.05)                        # still writing, caller not blocked
    gate.set()
    assert saver.flush() and (tmp_path / "a.jsonl").exists()
