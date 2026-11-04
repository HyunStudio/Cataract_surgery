import sys
from types import SimpleNamespace

from ophthosim import launcher


def test_default_launches_korean_3d_and_forwards_case(monkeypatch):
    calls = []
    monkeypatch.setitem(sys.modules, 'ophthosim.gl_surgery',
                        SimpleNamespace(main=lambda args: calls.append(args) or 0))
    assert launcher.main(['--case', 'leak']) == 0
    assert calls == [['--lang', 'ko', '--case', 'leak']]


def test_2d_keeps_explicit_language(monkeypatch):
    calls = []
    monkeypatch.setitem(sys.modules, 'ophthosim.app',
                        SimpleNamespace(main=lambda args: calls.append(args)))
    assert launcher.main(['--mode', '2d', '--lang', 'en']) == 0
    assert calls == [['--lang', 'en']]


def test_frozen_uses_writable_user_directory(monkeypatch, tmp_path):
    monkeypatch.setattr(sys, 'frozen', True, raising=False)
    monkeypatch.setenv('LOCALAPPDATA', str(tmp_path))
    monkeypatch.chdir(tmp_path)
    calls = []
    monkeypatch.setitem(sys.modules, 'ophthosim.gl_surgery',
                        SimpleNamespace(main=lambda args: calls.append(launcher.Path.cwd())))
    launcher.main([])
    assert calls == [tmp_path / 'OphthoSim']


def test_frozen_explicit_resume_remains_relative_to_invoking_directory(monkeypatch, tmp_path):
    monkeypatch.setattr(sys, 'frozen', True, raising=False)
    monkeypatch.setenv('LOCALAPPDATA', str(tmp_path / 'data'))
    monkeypatch.chdir(tmp_path)
    calls = []
    monkeypatch.setitem(sys.modules, 'ophthosim.gl_surgery',
                        SimpleNamespace(main=lambda args: calls.append(args)))
    launcher.main(['--resume', 'case.jsonl'])
    assert calls == [['--lang', 'ko', '--resume', str(tmp_path / 'case.jsonl')]]
