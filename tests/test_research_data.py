"""Research data contract: event migration, practice/evaluation splits."""
import csv
import io
import json

import pytest

from ophthosim import experiments
from ophthosim.engine import Game
from ophthosim.migrate import CURRENT, main, migrate_event, migrate_jsonl


def _legacy(version, difficulty=None):
    game = Game('motion', 4, difficulty or 'standard')
    events = []
    for event in game.events:
        old = {k: v for k, v in event.items() if k not in ('session_id', 'scenario_id')}
        old['schema_version'] = version
        if version == 1:
            old['data'] = {k: v for k, v in old['data'].items() if k != 'difficulty'}
        events.append(old)
    return game, events


@pytest.mark.parametrize('version', [1, 2])
def test_old_traces_gain_v3_identifiers_without_changing_content(version):
    game, events = _legacy(version, 'hard' if version == 2 else None)
    text = ''.join(json.dumps(e) + '\n' for e in events)
    migrated = [json.loads(line) for line in migrate_jsonl(text).splitlines()]
    expected_level = 'hard' if version == 2 else 'standard'
    for old, new in zip(events, migrated):
        assert new['schema_version'] == CURRENT and new['migrated_from'] == version
        assert new['scenario_id'] == f'motion/{expected_level}'
        assert new['session_id'] == Game('motion', 4, expected_level).session_id
        for key in ('kind', 'step', 'sim_time_ms', 'phase', 'case', 'seed'):
            assert new[key] == old[key]
    assert migrated[0]['data']['difficulty'] == expected_level


def test_current_events_pass_through_and_bad_events_fail():
    event = Game().events[0]
    assert migrate_event(event) == event
    for bad in ({}, {'schema_version': 9}, {'schema_version': 2, 'case': 'x'}, 'text'):
        with pytest.raises(ValueError):
            migrate_event(bad)
    with pytest.raises(ValueError):
        migrate_jsonl('\n\n')


def test_migrate_cli(tmp_path):
    _, events = _legacy(1)
    src, dst = tmp_path / 'old.jsonl', tmp_path / 'new.jsonl'
    src.write_text(''.join(json.dumps(e) + '\n' for e in events), encoding='utf-8')
    assert main([str(src), str(dst)]) == 0
    assert all(json.loads(l)['schema_version'] == 3 for l in dst.read_text().splitlines())
    src.write_text('{"schema_version": 7}\n', encoding='utf-8')
    assert main([str(src), str(dst)]) == 2


def test_practice_and_evaluation_splits(tmp_path):
    config = {'name': 'split', 'cases': ['normal', 'vitreous'],
              'splits': {'practice': [1, 2], 'evaluation': [50, 51, 52]},
              'policies': ['ideal']}
    result = experiments.run_experiment(config, tmp_path)
    assert result['runs'] == 10 and result['all_replays_verified']
    assert set(result['summary']) == {'ideal/standard/practice', 'ideal/standard/evaluation'}
    assert result['summary']['ideal/standard/evaluation']['runs'] == 6
    rows = list(csv.DictReader(io.StringIO((tmp_path / 'metrics.csv').read_text())))
    assert {r['split'] for r in rows} == {'practice', 'evaluation'}
    assert {r['seed'] for r in rows if r['split'] == 'evaluation'} == {'50', '51', '52'}


@pytest.mark.parametrize('bad', [
    {'splits': {'practice': [1], 'evaluation': [1]}},              # leakage
    {'splits': {'practice': [1]}},
    {'splits': {'practice': [1], 'evaluation': [2], 'extra': [3]}},
    {'splits': {'practice': [], 'evaluation': [2]}},
    {'splits': {'practice': [1], 'evaluation': [2]}, 'seeds': [3]},
    {'splits': [1, 2]},
])
def test_invalid_splits_rejected(bad):
    with pytest.raises(ValueError):
        experiments.load_config(bad)


def test_data_dictionary_documents_every_metric_column_and_event_kind():
    from pathlib import Path
    from ophthosim.report import METRIC_COLUMNS
    text = (Path(__file__).resolve().parents[1] / 'docs' / 'DATA_DICTIONARY.md').read_text('utf-8')
    for column in (*METRIC_COLUMNS, 'policy', 'split', 'replay_verified'):
        assert f'`{column}`' in text, column
    kinds = {'start', 'scenario_draw', 'phase', 'alert', 'assessed', 'veto', 'ending',
             'preop_check', 'check', 'rejected', 'tool', 'help_requested', 'near_miss',
             'entry_point', 'capsule_completed', 'removed', 'placed', 'pause'}
    for kind in kinds:
        assert f'`{kind}`' in text, kind
