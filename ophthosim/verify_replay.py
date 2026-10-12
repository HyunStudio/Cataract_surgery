"""CLI to verify a synthetic OphthoSim replay without launching Pygame.

Usage: python -m ophthosim.verify_replay session_logs/example.replay.jsonl
A valid SHA-256 journal is NOT proof of author identity or clinical accuracy.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from .replay import ReplayGame


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Verify a synthetic cataract simulation replay")
    parser.add_argument("file", type=Path, help="Replay JSONL file path")
    args = parser.parse_args(argv)
    try:
        if args.file.stat().st_size > ReplayGame.MAX_REPLAY_BYTES:
            raise ValueError("Replay exceeds the file-size budget")
        raw = args.file.read_text(encoding="utf-8")
        session = ReplayGame.replay_jsonl(raw)
    except (OSError, UnicodeError, ValueError, RuntimeError) as exc:
        print(f"REPLAY INVALID: {exc}", file=sys.stderr)
        return 2

    print(json.dumps({
        "status": "verified",
        "case": session.case,
        "seed": session.seed,
        "phase": session.phase.value,
        "ending": session.ending,
        "score": session.score(),
        "records": len(session.journal),
        "simulation_steps": session.step,
        "clinical_validation": False
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
