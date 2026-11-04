import threading

import pytest

from ophthosim import autosave
from ophthosim.replay import ReplayGame


def test_close_drains_latest_request_and_joins_worker(tmp_path, monkeypatch):
    entered, release = threading.Event(), threading.Event()
    real_write = autosave._write

    def blocked_write(target, text):
        entered.set()
        assert release.wait(5)
        real_write(target, text)

    monkeypatch.setattr(autosave, '_write', blocked_write)
    saver = autosave.BackgroundAutosave()
    game = ReplayGame('normal', 7, 'standard')
    path = tmp_path / 'recovery.jsonl'
    saver.submit(game, path)
    assert entered.wait(5)
    saver.submit(game, path)
    try:
        assert not saver.close(timeout=0)
    finally:
        release.set()
    assert saver.close(timeout=5)
    assert not saver._thread.is_alive()
    assert autosave.load_autosave(path).snapshot() == game.snapshot()
    with pytest.raises(RuntimeError, match='closed'):
        saver.submit(game, path)


def test_failed_write_is_observable_without_crashing_loop(tmp_path):
    blocker = tmp_path / 'file'
    blocker.write_text('x')
    saver = autosave.BackgroundAutosave()
    saver.submit(ReplayGame('normal', 7, 'standard'), blocker / 'save.jsonl')
    assert saver.close(timeout=5)
    assert isinstance(saver.last_error, OSError)
