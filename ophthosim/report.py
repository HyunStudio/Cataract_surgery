"""Explainable results report and research exports for one synthetic session.

Everything is derived from the engine's own events, score breakdown and
metrics, so the results screen, the JSON report and the CSV files always
agree with the replayable session. Scores are game feedback, not a clinical
or skill assessment.
"""
from __future__ import annotations

import csv
import io
import json
from pathlib import Path
from typing import Any

from .engine import Game
from .i18n import t

DISCLAIMER = ('Synthetic educational simulation. Scores are in-game feedback; '
              'they are not clinical outcomes or validated skill measures.')


def _pct(value: float) -> int:
    return round(100 * value)


def explain(game: Game, lang: str = 'en') -> list[dict[str, Any]]:
    """Breakdown rows with a localized label and a one-line reason each."""
    rows = []
    for item in game.score_breakdown():
        key, detail = item['key'], item['detail']
        if key == 'stages':
            reasons = [t(lang, 'why.stages', completed=detail['completed'], of=detail['of'])]
        elif key == 'tissue':
            reasons = ([t(lang, 'why.tissue', integrity=_pct(detail['capsule_integrity']),
                          near=detail['near_misses'])]
                       if detail['evaluated'] else [t(lang, 'why.tissue.pending')])
        elif key == 'iol':
            reasons = ([t(lang, 'why.iol', alignment=_pct(detail['alignment']),
                          attempts=detail['attempts'])]
                       if detail['evaluated'] else [t(lang, 'why.iol.pending')])
        elif key == 'response':
            if not detail['evaluated']:
                reasons = [t(lang, 'why.response.pending')]
            elif not detail['alerts']:
                reasons = [t(lang, 'why.response.none')]
            else:
                reasons = []
                for alert in detail['alerts']:
                    name = t(lang, f"alert.{alert['kind']}")
                    if alert['response'] in (None, 'timeout'):
                        reasons.append(t(lang, 'why.response.timeout', alert=name))
                    else:
                        reasons.append(t(lang, 'why.response.item', alert=name,
                                         response=t(lang, f"response.{alert['response']}"),
                                         latency=f"{alert['latency']:.1f}",
                                         credit=_pct(alert['fraction'])))
        else:
            if detail['ending'] is None:
                reasons = [t(lang, 'why.safety.pending')]
            else:
                reasons = [t(lang, 'why.safety.veto' if detail['veto'] else 'why.safety.ok')]
        rows.append({'key': key, 'label': t(lang, f'score.{key}'),
                     'points': item['points'], 'max': item['max'], 'reasons': reasons})
    return rows


def timeline(game: Game, lang: str = 'en') -> list[dict[str, Any]]:
    """Human-readable key events with simulation time in seconds."""
    rows = []
    for event in game.events:
        kind, data = event['kind'], event['data']
        seconds = event['sim_time_ms'] / 1000
        if kind == 'start':
            text = t(lang, 'tl.start', case=t(lang, f"case.{data['case']}"),
                     difficulty=t(lang, f"difficulty.{data.get('difficulty', 'standard')}"))
        elif kind == 'phase':
            text = t(lang, 'tl.phase', phase=t(lang, f"phase.{data['to']}"))
        elif kind == 'alert':
            text = t(lang, 'tl.alert', alert=t(lang, f"alert.{data['kind']}"))
        elif kind == 'assessed':
            text = t(lang, 'tl.assessed', alert=t(lang, f"alert.{data['alert']}"),
                     latency=f"{data.get('latency_s', 0):.1f}")
        elif kind == 'veto':
            text = t(lang, 'tl.veto', alert=t(lang, f"alert.{data['alert']}"))
        elif kind == 'ending':
            text = t(lang, 'tl.ending', ending=t(lang, f"ending.{data['outcome']}"))
        elif kind in ('preop_check', 'check'):
            text = t(lang, f'tl.{kind}', item=t(lang, f"check.{data['item']}"))
        elif kind == 'scenario_draw':
            text = t(lang, 'tl.scenario_draw', hazard=t(lang, f"case.{data['hazard']}"))
        elif kind == 'help_requested':
            text = t(lang, 'tl.help_requested')
        else:
            continue
        rows.append({'t': round(seconds, 2), 'step': event['step'], 'kind': kind,
                     'text': text, 'critical': kind in ('alert', 'veto')})
    return rows


def build_report(game: Game, lang: str = 'en') -> dict[str, Any]:
    return {
        'report_version': 1,
        'language': lang,
        'case': game.case, 'hazard': game.hazard, 'difficulty': game.difficulty,
        'seed': game.seed, 'phase': game.phase.value,
        'ending': game.ending,
        'ending_text': t(lang, f'ending.{game.ending}') if game.ending else None,
        'score': game.score(),
        'breakdown': explain(game, lang),
        'timeline': timeline(game, lang),
        'metrics': game.metrics(),
        'disclaimer': DISCLAIMER,
    }


def events_csv(game: Game) -> str:
    """One row per engine event; nested data is kept as compact JSON."""
    out = io.StringIO()
    writer = csv.writer(out, lineterminator='\n')
    writer.writerow(['step', 'sim_time_ms', 'phase', 'kind', 'case', 'seed', 'data'])
    for event in game.events:
        writer.writerow([event['step'], event['sim_time_ms'], event['phase'], event['kind'],
                         event['case'], event['seed'],
                         json.dumps(event['data'], sort_keys=True, separators=(',', ':'),
                                    ensure_ascii=False)])
    return out.getvalue()


METRIC_COLUMNS = ('case', 'hazard', 'difficulty', 'seed', 'ending', 'score', 'sim_time_s',
                  'near_misses', 'rejected_inputs', 'wrong_tool', 'iol_attempts', 'pauses',
                  'help_requests', 'capsule_misses', 'endpoint_error_entry',
                  'endpoint_error_capsule', 'endpoint_error_iol', 'alert_count', 'first_alert_latency_s', 'first_alert_response',
                  'score_stages', 'score_tissue', 'score_iol', 'score_response',
                  'score_safety')


def metrics_row(game: Game) -> dict[str, Any]:
    metrics = game.metrics()
    alerts = metrics['alerts']
    row = {key: metrics.get(key) for key in METRIC_COLUMNS if key in metrics}
    row['alert_count'] = len(alerts)
    row['first_alert_latency_s'] = alerts[0]['latency'] if alerts else None
    row['first_alert_response'] = alerts[0]['response'] if alerts else None
    for task, value in metrics['endpoint_error'].items():
        row[f'endpoint_error_{task.lower()}'] = value
    for item in game.score_breakdown():
        row[f"score_{item['key']}"] = item['points']
    return {key: row.get(key) for key in METRIC_COLUMNS}


def metrics_csv(rows: list[dict[str, Any]]) -> str:
    out = io.StringIO()
    writer = csv.DictWriter(out, fieldnames=METRIC_COLUMNS, lineterminator='\n')
    writer.writeheader()
    for row in rows:
        writer.writerow({key: ('' if row.get(key) is None else row[key]) for key in METRIC_COLUMNS})
    return out.getvalue()


def save_session(game: Game, directory: str | Path = 'session_logs',
                 prefix: str = 'case', lang: str = 'en') -> list[Path]:
    """Write trace JSONL, replay JSONL (if available), report JSON and CSVs.

    Only synthetic data is written; there are no personal identifiers.
    """
    root = Path(directory)
    root.mkdir(parents=True, exist_ok=True)
    base = f'{prefix}_{game.case}_{game.difficulty}_seed_{game.seed}'
    outputs = {
        f'{base}.jsonl': game.export_jsonl(),
        f'{base}.events.csv': events_csv(game),
        f'{base}.metrics.csv': metrics_csv([metrics_row(game)]),
        f'{base}.report.json': json.dumps(build_report(game, lang), ensure_ascii=False,
                                          indent=2, sort_keys=True) + '\n',
    }
    if hasattr(game, 'export_replay_jsonl'):
        # Raises RuntimeError on an over-limit capture: never write partial data.
        outputs[f'{base}.replay.jsonl'] = game.export_replay_jsonl()
    paths = []
    for name, text in outputs.items():
        path = root / name
        path.write_text(text, encoding='utf-8')
        paths.append(path)
    return paths
