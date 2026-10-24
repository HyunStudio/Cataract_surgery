"""Recovery points: the verified replay journal doubles as an autosave.

A replay reconstructs the exact engine state (including timed safety holds),
so resuming never trusts a separately stored snapshot. Files are synthetic
and local; a tampered or truncated autosave is rejected, not repaired.
"""
from __future__ import annotations

from pathlib import Path

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
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_suffix(target.suffix + ".tmp")
    temporary.write_text(text, encoding="utf-8")
    temporary.replace(target)     # never leave a half-written autosave
    return target


def load_autosave(path: str | Path = AUTOSAVE) -> ReplayGame:
    """Rebuild the saved case; raises ValueError/OSError on any problem."""
    return ReplayGame.replay_jsonl(Path(path).read_text(encoding="utf-8"))


def clear_autosave(path: str | Path = AUTOSAVE) -> None:
    try:
        Path(path).unlink()
    except FileNotFoundError:
        pass
