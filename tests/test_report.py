"""Explainable report, i18n, CSV/JSON session export and experiment batches."""
import csv
import io
import json

import pytest

from ophthosim import experiments
from ophthosim.engine import ENDING_FAILED, Phase
from ophthosim.i18n import EN, KO, LANGUAGES, t
from ophthosim.replay import ReplayGame
from ophthosim.report import (METRIC_COLUMNS, build_report, events_csv, explain,
                              metrics_csv, metrics_row, save_session, timeline)


def played(case='normal', difficulty='standard', policy='ideal', seed=4):
    return experiments.run_one(case, difficulty, seed, policy)


# --- i18n --------------------------------------------------------------------
def test_korean_table_covers_every_english_key():
    assert set(KO) == set(EN)
    assert all(KO[key].strip() for key in KO)


def test_translation_fallbacks_never_raise():
    assert t('ko', 'phase.PREOP') == '수술 전 확인'
    assert t('fr', 'phase.PREOP') == EN['phase.PREOP']
    assert t('en', 'no.such.key') == 'no.such.key'
    assert t('en', 'why.stages', completed=1) == EN['why.stages']   # missing arg
    assert t('en', 'why.stages', completed=3, of=7) == 'Completed 3 of 7 procedure stages.'


# --- report --------------------------------------------------------------------
@pytest.mark.parametrize('lang', LANGUAGES)
def test_report_points_match_engine_and_have_reasons(lang):
    game = played('motion')
    report = build_report(game, lang)
    assert report['score'] == game.score()
    assert sum(r['points'] for r in report['breakdown']) == pytest.approx(game.score(), abs=1)
    assert all(r['reasons'] and all(r['reasons']) for r in report['breakdown'])
    assert report['ending'] == 'COMPLICATION MANAGED'
    assert report['ending_text'] == t(lang, 'ending.COMPLICATION MANAGED')
    json.dumps(report, ensure_ascii=False)


def test_explanations_cover_pending_veto_and_latency():
    pending = ReplayGame()
    rows = {r['key']: r for r in explain(pending)}
    assert rows['tissue']['reasons'] == [EN['why.tissue.pending']]
    assert rows['safety']['reasons'] == [EN['why.safety.pending']]
    failed = played('vitals', policy='unresponsive')
    assert failed.ending == ENDING_FAILED
    rows = {r['key']: r for r in explain(failed, 'ko')}
    assert rows['safety']['reasons'] == [KO['why.safety.veto']]
    assert '방치' in rows['response']['reasons'][0]
    slow = played('vitals', policy='slow')
    reason = {r['key']: r for r in explain(slow)}['response']['reasons'][0]
    assert 'assessed after 14.' in reason and 'credit' in reason


def test_timeline_marks_alerts_and_is_chronological():
    game = played('decenter')
    rows = timeline(game)
    times = [row['t'] for row in rows]
    assert times == sorted(times)
    kinds = [row['kind'] for row in rows]
    assert kinds[0] == 'start' and kinds[-1] == 'ending'
    assert kinds.count('preop_check') == 3
    alert = next(row for row in rows if row['kind'] == 'alert')
    assert alert['critical'] and 'IOL decentration' in alert['text']
    assert any(row['kind'] == 'assessed' for row in rows)


def test_events_csv_round_trips_every_event():
    game = played('leak')
    rows = list(csv.DictReader(io.StringIO(events_csv(game))))
    assert len(rows) == game.event_count()
    assert [r['kind'] for r in rows] == [e['kind'] for e in game.events]
    assert json.loads(rows[0]['data'])['case'] == 'leak'


def test_metrics_row_and_csv_columns():
    game = played('pupil', policy='careless')
    row = metrics_row(game)
    assert tuple(row) == METRIC_COLUMNS
    assert row['alert_count'] == 1 and row['first_alert_response'] == 'assess'
    assert row['near_misses'] > 0
    parsed = list(csv.DictReader(io.StringIO(metrics_csv([row, metrics_row(played())]))))
    assert len(parsed) == 2 and parsed[1]['first_alert_latency_s'] == ''


def test_save_session_writes_consistent_files(tmp_path):
    game = played('haze')
    paths = save_session(game, tmp_path, lang='ko')
    names = sorted(p.name for p in paths)
    assert names == sorted(f'case_haze_standard_seed_4{suffix}' for suffix in
                           ('.jsonl', '.events.csv', '.metrics.csv', '.report.json',
                            '.replay.jsonl'))
    report = json.loads((tmp_path / 'case_haze_standard_seed_4.report.json').read_text('utf-8'))
    assert report['language'] == 'ko' and report['score'] == game.score()
    replay = (tmp_path / 'case_haze_standard_seed_4.replay.jsonl').read_text('utf-8')
    assert ReplayGame.replay_jsonl(replay).snapshot() == game.snapshot()


def test_save_session_refuses_overflowed_replay(tmp_path):
    game = played()
    game.journal_overflow = True
    with pytest.raises(RuntimeError):
        save_session(game, tmp_path)
    assert not list(tmp_path.glob('*.report.json'))


# --- experiments ----------------------------------------------------------------
def test_agents_reach_expected_endings():
    assert played('normal').ending == 'SIMULATION COMPLETE'
    assert played('capsule').ending == 'SAFELY ABORTED'
    assert played('motion', policy='unresponsive').ending == ENDING_FAILED
    abandoned = played('motion', 'tutorial', 'unresponsive')
    assert abandoned.ending is None and abandoned.patient.alert
    assert played('normal', policy='careless').near_misses > 0


def test_experiment_is_deterministic_and_verified(tmp_path):
    config = {'name': 'unit', 'cases': ['normal', 'random'], 'difficulties': ['hard'],
              'seeds': [1, 2, 3], 'policies': ['ideal', 'slow']}
    first = experiments.run_experiment(config, tmp_path / 'a', save_replays=True)
    second = experiments.run_experiment(config, tmp_path / 'b')
    assert first['runs'] == 12 and first['all_replays_verified']
    assert first['summary'] == second['summary']
    assert (tmp_path / 'a' / 'metrics.csv').read_text() == (tmp_path / 'b' / 'metrics.csv').read_text()
    rows = list(csv.DictReader(io.StringIO((tmp_path / 'a' / 'metrics.csv').read_text())))
    assert len(rows) == 12 and rows[0]['policy'] == 'ideal' and rows[0]['replay_verified'] == 'True'
    assert len(list((tmp_path / 'a' / 'replays').glob('*.jsonl'))) == 12


@pytest.mark.parametrize('bad', [
    [], {'name': 'x y'}, {'cases': []}, {'cases': ['clinical']}, {'difficulties': ['easy']},
    {'policies': ['robot']}, {'seeds': [1.5]}, {'seeds': [True]}, {'seeds': [10**30]},
    {'extra': 1}, {'seeds': list(range(experiments.MAX_RUNS + 1))},
])
def test_invalid_configs_rejected(bad):
    with pytest.raises(ValueError):
        experiments.load_config(bad)


def test_cli(tmp_path, capsys):
    config = tmp_path / 'c.json'
    config.write_text(json.dumps({'name': 'cli', 'seeds': [5]}), encoding='utf-8')
    assert experiments.main([str(config), '--out', str(tmp_path / 'out')]) == 0
    out = json.loads(capsys.readouterr().out)
    assert out['runs'] == 1 and out['all_replays_verified']
    config.write_text('{"name": "bad name"}', encoding='utf-8')
    assert experiments.main([str(config)]) == 2
    assert experiments.main([str(tmp_path / 'missing.json')]) == 2


def test_unknown_policy_rejected():
    with pytest.raises(ValueError):
        experiments.Agent(ReplayGame(), 'cheater', 1)
