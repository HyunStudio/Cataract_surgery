"""Recovery points: the verified replay journal doubles as an autosave.

A replay reconstructs the exact engine state (including timed safety holds),
so resuming never trusts a separately stored snapshot. Files are synthetic
and local; a tampered or truncated autosave is rejected, not repaired.
"""
from __future__ import annotations

from pathlib import Path
import threading

from .replay import ReplayGame

AUTOSAVE = Path("session_logs") / "autosave.replay.jsonl"


def write_autosave(game: ReplayGame, path: str | Path = AUTOSAVE) -> Path | None:
    """Save an unfinished case; finished cases clear their recovery point."""
    target = Path(path)
    if game.ending:
        clear_autosave(target)
        return None
    try:
        text = game.export_replay_jsonl()
    except RuntimeError:          # capture over its safety limits: skip
        return None
    _write(target, text)
    return target


def _write(target: Path, text: str) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_suffix(target.suffix + ".tmp")
    temporary.write_text(text, encoding="utf-8")
    temporary.replace(target)     # never leave a half-written autosave


class BackgroundAutosave:
    """Writes recovery points off the game loop.

    The journal text is captured on the caller's thread (the game keeps
    changing); only the file I/O runs on a worker. A newer request replaces
    an unwritten older one. Disk stalls (slow drives, antivirus scans) held
    the 3D loop for up to ~0.3 s per phase change when this was synchronous.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._job: tuple[str, Path, str | None] | None = None
        self._wake = threading.Event()
        self._idle = threading.Event()
        self._idle.set()
        self._thread: threading.Thread | None = None
        self._closed = False
        self.last_error: OSError | None = None

    def submit(self, game: ReplayGame, path: str | Path = AUTOSAVE) -> None:
        if game.ending:
            job = ("clear", Path(path), None)
        else:
            try:
                job = ("write", Path(path), game.export_replay_jsonl())
            except RuntimeError:      # capture over its safety limits: skip
                return
        with self._lock:
            if self._closed:
                raise RuntimeError("autosave is closed")
            self._job = job
            self._idle.clear()
            if self._thread is None or not self._thread.is_alive():
                self._thread = threading.Thread(target=self._run, name="autosave", daemon=True)
                self._thread.start()
        self._wake.set()

    def flush(self, timeout: float = 5.0) -> bool:
        """Wait for pending I/O; inspect last_error to detect a failed write."""
        return self._idle.wait(timeout)

    def close(self, timeout: float | None = None) -> bool:
        """Stop accepting saves, drain pending I/O and join the worker.

        A timeout reports incomplete shutdown; calling close again may wait
        for it. Normal exit waits without silently discarding a slow save.
        """
        with self._lock:
            self._closed = True
            worker = self._thread
            self._wake.set()
        if worker is not None:
            worker.join(timeout)
            return not worker.is_alive()
        return True

    def _run(self) -> None:
        while True:
            self._wake.wait()
            with self._lock:
                job, self._job = self._job, None
                self._wake.clear()
                if job is None:
                    self._idle.set()
                    if self._closed:
                        return
                    continue
            kind, target, text = job
            try:
                if kind == "clear":
                    clear_autosave(target)
                else:
                    _write(target, text)
            except OSError as exc:
                self.last_error = exc
            else:
                self.last_error = None
            with self._lock:
                if self._job is None:
                    self._idle.set()
                    if self._closed:
                        return
                else:
                    self._wake.set()


def load_autosave(path: str | Path = AUTOSAVE) -> ReplayGame:
    """Rebuild the saved case; raises ValueError/OSError on any problem."""
    return ReplayGame.replay_jsonl(Path(path).read_text(encoding="utf-8"))


def clear_autosave(path: str | Path = AUTOSAVE) -> None:
    try:
        Path(path).unlink()
    except FileNotFoundError:
        pass
