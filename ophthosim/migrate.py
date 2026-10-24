"""Versioned event-trace migration (research data contract).

    python -m ophthosim.migrate old_trace.jsonl new_trace.jsonl

Upgrades schema v1/v2 event traces to v3 by adding the fields later
versions define: ``session_id`` and ``scenario_id`` (deterministic synthetic
identifiers derived from case/difficulty/seed) and an explicit difficulty
(v1 traces predate difficulty levels and were played at today's
"standard" tolerances). Event content is never altered or invented.
Command replays are not migrated: rules changed between schema versions, so
an old replay cannot be re-executed faithfully and is rejected instead.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
from typing import Any

CURRENT = 3


def _session_id(case: str, difficulty: str, seed: int) -> str:
    digest = hashlib.sha256(f'{case}:{difficulty}:{seed}'.encode()).hexdigest()
    return f'SIM-{digest[:10]}'


def migrate_event(event: dict[str, Any], difficulty: str | None = None) -> dict[str, Any]:
    """Return a v3 copy of one event; raises ValueError on unknown schemas."""
    if not isinstance(event, dict):
        raise ValueError('Event must be an object')
    version = event.get('schema_version')
    if version not in (1, 2, 3):
        raise ValueError(f'Unsupported event schema: {version!r}')
    for key in ('case', 'seed', 'kind', 'step', 'sim_time_ms', 'phase'):
        if key not in event:
            raise ValueError(f'Event missing {key!r}')
    out = dict(event)
    if version == CURRENT:
        return out
    level = difficulty or 'standard'
    out['session_id'] = _session_id(event['case'], level, event['seed'])
    out['scenario_id'] = f"{event['case']}/{level}"
    if event['kind'] == 'start':
        data = dict(event.get('data') or {})
        data.setdefault('difficulty', level)
        out['data'] = data
    out['schema_version'] = CURRENT
    out['migrated_from'] = version
    return out


def migrate_jsonl(text: str) -> str:
    """Migrate a whole trace; the start event's difficulty applies to all."""
    events = [json.loads(line) for line in text.splitlines() if line.strip()]
    if not events:
        raise ValueError('Empty trace')
    start = next((e for e in events if e.get('kind') == 'start'), {})
    difficulty = (start.get('data') or {}).get('difficulty')
    return ''.join(json.dumps(migrate_event(e, difficulty), sort_keys=True,
                              ensure_ascii=False) + '\n' for e in events)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description='Upgrade an event trace to schema v3')
    parser.add_argument('source', type=Path)
    parser.add_argument('target', type=Path)
    ns = parser.parse_args(argv)
    try:
        ns.target.write_text(migrate_jsonl(ns.source.read_text(encoding='utf-8')),
                             encoding='utf-8')
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f'Migration failed: {exc}', file=sys.stderr)
        return 2
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
