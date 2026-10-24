"""Deterministic batch runs of scripted *synthetic* agents (WP30).

    python -m ophthosim.experiments config.json --out build/experiments/demo

Config (JSON):
    {"name": "demo", "cases": ["normal", "motion"], "difficulties": ["standard"],
     "seeds": [1, 2, 3], "policies": ["ideal", "careless"]}

Agents only validate the instrument (identical inputs give identical logs and
replays). They are not models of human surgeons, and their scores say nothing
about surgical skill or interface benefit for people.
"""
from __future__ import annotations

import argparse
import csv
import io
import json
import math
from pathlib import Path
import random
import sys
from typing import Any

from .engine import CASES, DIFFICULTIES, FINAL_CHECKS, PREOP_CHECKS, TOOL_NAMES, Phase
from .replay import ReplayGame
from .report import METRIC_COLUMNS, metrics_row

FRAME = 1 / 60
MAX_FRAMES = 60 * 60 * 20       # 20 simulated minutes per run at most
MAX_RUNS = 5000

POLICIES: dict[str, dict[str, float]] = {
    # jitter: target noise; miss: probability of an off-target removal;
    # delay: seconds before assessing an alert (None = never assesses).
    'ideal': {'jitter': 0.0, 'miss': 0.0, 'delay': 1.0, 'think': 2, 'wrong_tool': 0.0},
    'careless': {'jitter': .03, 'miss': .12, 'delay': 6.0, 'think': 1, 'wrong_tool': .3},
    'slow': {'jitter': .01, 'miss': .02, 'delay': 14.0, 'think': 8, 'wrong_tool': 0.0},
    'unresponsive': {'jitter': .01, 'miss': .02, 'delay': math.inf, 'think': 2,
                     'wrong_tool': 0.0},
}


class Agent:
    """Scripted synthetic operator driving the engine through semantic actions."""

    def __init__(self, game: ReplayGame, policy: str, seed: int) -> None:
        if policy not in POLICIES:
            raise ValueError(f'Unknown policy {policy!r}')
        self.game = game
        self.p = POLICIES[policy]
        self.rng = random.Random(f'{policy}:{seed}')
        self.frames = 0
        self._capsule_bin = 0

    def wait(self, frames: int) -> None:
        for _ in range(frames):
            if self.game.ending or self.frames >= MAX_FRAMES:
                return
            self.game.tick(FRAME)
            self.frames += 1

    def aim(self, x: float, y: float) -> tuple[float, float]:
        j = self.p['jitter']
        return (min(1., max(0., x + self.rng.uniform(-j, j))),
                min(1., max(0., y + self.rng.uniform(-j, j))))

    def handle_alert(self) -> None:
        delay = self.p['delay']
        if math.isinf(delay):
            # Never responds: a timed hold ends in a veto; an untimed
            # (tutorial) hold is abandoned after two simulated minutes.
            timeout = self.game.rules.alert_timeout
            self.wait(MAX_FRAMES if timeout is not None else round(120 / FRAME))
            self.frames = MAX_FRAMES
            return
        self.wait(round(delay / FRAME))
        if not self.game.ending:
            self.game.action('assess')

    def arm(self) -> None:
        g = self.game
        required = g.required_tool
        if required is None or g.tool == required:
            return
        if self.rng.random() < self.p['wrong_tool']:
            wrong = next(t for t in TOOL_NAMES if t != required)
            g.action('tool', wrong)
            self.wait(int(self.p['think']))
            # One mistaken attempt is rejected before the right tool is picked.
            g.action('touch', .5, .5)
        g.action('tool', required)

    def step(self) -> None:
        g = self.game
        if g.patient.alert:
            self.handle_alert()
            return
        self.arm()
        phase = g.phase
        if phase == Phase.PREOP:
            for item in PREOP_CHECKS:
                g.action('verify', item)
                self.wait(int(self.p['think']))
            g.action('confirm')
        elif phase == Phase.ANESTHESIA:
            g.action('prepare')
        elif phase == Phase.ENTRY:
            for index, target in enumerate(g._entry_target):
                if index not in g._entered:
                    g.action('touch', *self.aim(*target))
                    break
        elif phase == Phase.CAPSULE:
            angle = (self._capsule_bin + .5) * math.tau / 24
            self._capsule_bin = (self._capsule_bin + 1) % 24
            g.action('trace', *self.aim(.5 + .28 * math.cos(angle), .5 + .28 * math.sin(angle)))
        elif phase in (Phase.PHACO, Phase.CORTEX):
            if self.rng.random() < self.p['miss']:
                g.action('remove', *self.aim(.5 + g.work_radius + .03, .5))
            else:
                g.action('remove', *self.aim(.5, .5))
        elif phase == Phase.IOL or (phase == Phase.CLOSE and g._decentered):
            g.action('place', *self.aim(.5, .5))
        elif phase == Phase.CLOSE:
            for item in FINAL_CHECKS:
                if item not in g.eye.final_checks and not g.patient.alert:
                    g.action('verify', item)
                    break
        self.wait(int(self.p['think']))

    def play(self) -> ReplayGame:
        while not self.game.ending and self.frames < MAX_FRAMES:
            self.step()
        return self.game


def run_one(case: str, difficulty: str, seed: int, policy: str) -> ReplayGame:
    game = ReplayGame(case, seed, difficulty)
    return Agent(game, policy, seed).play()


def load_config(raw: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise ValueError('Config must be a JSON object')
    allowed = {'name', 'cases', 'difficulties', 'seeds', 'splits', 'policies'}
    if set(raw) - allowed:
        raise ValueError(f'Unknown config keys: {sorted(set(raw) - allowed)}')
    config = {'name': raw.get('name', 'experiment'),
              'cases': raw.get('cases', ['normal']),
              'difficulties': raw.get('difficulties', ['standard']),
              'seeds': raw.get('seeds', [1]),
              'policies': raw.get('policies', ['ideal'])}
    name = config['name']
    if not isinstance(name, str) or not name or len(name) > 60 or not all(
            c.isalnum() or c in '-_' for c in name):
        raise ValueError('name must be 1-60 characters of [A-Za-z0-9_-]')
    for key, valid in (('cases', CASES), ('difficulties', tuple(DIFFICULTIES)),
                       ('policies', tuple(POLICIES))):
        values = config[key]
        if not isinstance(values, list) or not values or any(v not in valid for v in values):
            raise ValueError(f'{key} must be a non-empty list drawn from {list(valid)}')
    def checked(seeds, label):
        if (not isinstance(seeds, list) or not seeds or
                any(type(s) is not int or abs(s) > 2**63 - 1 for s in seeds)):
            raise ValueError(f'{label} must be a non-empty list of 64-bit integers')
        return seeds
    if 'splits' in raw:
        # Research plan: practice and held-out evaluation seeds must not leak.
        if 'seeds' in raw:
            raise ValueError("use either 'seeds' or 'splits', not both")
        splits = raw['splits']
        if (not isinstance(splits, dict) or set(splits) != {'practice', 'evaluation'}):
            raise ValueError("splits must contain exactly 'practice' and 'evaluation'")
        practice = checked(splits['practice'], 'practice seeds')
        evaluation = checked(splits['evaluation'], 'evaluation seeds')
        if set(practice) & set(evaluation):
            raise ValueError('practice and evaluation seeds overlap (leakage)')
        config['splits'] = {'practice': practice, 'evaluation': evaluation}
        plan = [('practice', s) for s in practice] + [('evaluation', s) for s in evaluation]
    else:
        plan = [('all', s) for s in checked(config['seeds'], 'seeds')]
    config['seed_plan'] = plan
    seeds = plan
    runs = (len(config['cases']) * len(config['difficulties']) * len(seeds)
            * len(config['policies']))
    if runs > MAX_RUNS:
        raise ValueError(f'{runs} runs exceeds the {MAX_RUNS}-run limit')
    return config


def run_experiment(config: dict[str, Any], out: Path | None = None,
                   save_replays: bool = False) -> dict[str, Any]:
    config = load_config(config)
    rows, records = [], []
    for policy in config['policies']:
        for difficulty in config['difficulties']:
            for case in config['cases']:
                for split, seed in config['seed_plan']:
                    game = run_one(case, difficulty, seed, policy)
                    raw = game.export_replay_jsonl()
                    verified = ReplayGame.replay_jsonl(raw).snapshot() == game.snapshot()
                    row = {'policy': policy, 'split': split, **metrics_row(game),
                           'replay_verified': verified}
                    rows.append(row)
                    records.append({'policy': policy, 'split': split, 'metrics': game.metrics(),
                                    'replay_verified': verified})
                    if out is not None and save_replays:
                        (out / 'replays').mkdir(parents=True, exist_ok=True)
                        (out / 'replays' / f'{policy}_{case}_{difficulty}_{seed}.replay.jsonl'
                         ).write_text(raw, encoding='utf-8')
    summary = summarize(rows)
    result = {'name': config['name'], 'runs': len(rows), 'config': config,
              'summary': summary, 'all_replays_verified': all(r['replay_verified'] for r in rows),
              'note': 'Scripted synthetic agents; instrument validation only.'}
    if out is not None:
        out.mkdir(parents=True, exist_ok=True)
        buffer = io.StringIO()
        fields = ('policy', 'split', *METRIC_COLUMNS, 'replay_verified')
        writer = csv.DictWriter(buffer, fieldnames=fields, lineterminator='\n')
        writer.writeheader()
        for row in rows:
            writer.writerow({k: ('' if row.get(k) is None else row[k]) for k in fields})
        (out / 'metrics.csv').write_text(buffer.getvalue(), encoding='utf-8')
        (out / 'runs.jsonl').write_text(
            ''.join(json.dumps(r, sort_keys=True) + '\n' for r in records), encoding='utf-8')
        (out / 'summary.json').write_text(json.dumps(result, indent=2, sort_keys=True) + '\n',
                                          encoding='utf-8')
    return result


def summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Per (policy, difficulty) means and ending counts."""
    groups: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        key = f"{row['policy']}/{row['difficulty']}"
        if row.get('split', 'all') != 'all':
            key += f"/{row['split']}"
        groups.setdefault(key, []).append(row)
    summary = {}
    for key, items in sorted(groups.items()):
        endings: dict[str, int] = {}
        for item in items:
            label = item['ending'] or 'UNFINISHED'   # e.g. abandoned untimed hold
            endings[label] = endings.get(label, 0) + 1
        latencies = [i['first_alert_latency_s'] for i in items
                     if i['first_alert_latency_s'] is not None]
        summary[key] = {
            'runs': len(items),
            'mean_score': round(sum(i['score'] for i in items) / len(items), 2),
            'mean_near_misses': round(sum(i['near_misses'] for i in items) / len(items), 3),
            'mean_alert_latency_s': (round(sum(latencies) / len(latencies), 3)
                                     if latencies else None),
            'endings': endings,
        }
    return summary


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description='Run scripted synthetic sessions')
    parser.add_argument('config', type=Path)
    parser.add_argument('--out', type=Path, default=None)
    parser.add_argument('--save-replays', action='store_true')
    ns = parser.parse_args(argv)
    try:
        raw = json.loads(ns.config.read_text(encoding='utf-8'))
        out = ns.out or Path('build/experiments') / str(raw.get('name', 'experiment'))
        result = run_experiment(raw, out, ns.save_replays)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f'Experiment failed: {exc}', file=sys.stderr)
        return 2
    print(json.dumps({k: result[k] for k in ('name', 'runs', 'all_replays_verified', 'summary')},
                     indent=2, sort_keys=True))
    return 0 if result['all_replays_verified'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
