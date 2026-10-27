"""Qualification must fail closed without modifying the exported candidate."""
from pathlib import Path
import json
import subprocess

import pytest

from tools.validate_export import adapt_fixture, assess, digest, freeze_candidate, prepare_project


FIXTURE = '''extends SceneTree
var failures:=0
func _initialize()->void: call_deferred("run")
func run()->void:
\tvar app=load("res://scripts/simulator.gd").new(); root.add_child(app)
\tawait process_frame
\troot.get_texture().get_image().save_png("res://reports/frame.png")
\tprint("Volumetric encounter: ",failures," failures"); quit(1 if failures else 0)
'''


def test_adaptation_preserves_assertions_and_production_resource_path():
    result = adapt_fixture(FIXTURE, "normal")
    assert result.startswith("extends Node\n")
    assert 'load("res://scripts/simulator.gd")' in result
    assert 'print("Volumetric encounter: ",failures," failures")' in result
    assert "get_tree().quit(1 if failures else 0)" in result
    assert "get_tree().root.add_child(app)" in result
    assert "await get_tree().process_frame" in result
    assert 'save_png("user://native-validation/frame.png")' in result
    assert "func _ready()" in result


@pytest.mark.parametrize("source", [FIXTURE.replace("extends SceneTree", "extends Node"),
                                    FIXTURE.replace("_initialize", "initialize"),
                                    FIXTURE.replace("quit(1 if failures else 0)", "quit(0)"),
                                    FIXTURE.replace("await process_frame", "await physics_frame")])
def test_fixture_structure_drift_is_rejected(source):
    with pytest.raises(ValueError):
        adapt_fixture(source, "normal")


def test_only_named_fixtures_can_run():
    with pytest.raises(ValueError):
        adapt_fixture(FIXTURE, "../../arbitrary")


@pytest.mark.parametrize("scenario,filename", [
    ("normal", "test_volumetric_encounter.gd"),
    ("adverse", "test_volumetric_injury.gd"),
    ("control", "test_control_context.gd"),
])
def test_actual_allowlisted_fixtures_keep_early_failure_exits(scenario, filename):
    source = (Path(__file__).resolve().parents[1] / "godot/tests" / filename).read_text(encoding="utf-8")
    result = adapt_fixture(source, scenario)
    assert result.count("get_tree().quit(1)") == source.count("quit(1)")
    assert result.count("get_tree().quit(1 if failures else 0)") == 1


def test_frozen_pair_is_byte_identical_and_never_overwrites_candidate(tmp_path):
    candidate = tmp_path / "candidate" / "Surgical.exe"
    candidate.parent.mkdir()
    candidate.write_bytes(b"actual release engine")
    candidate.with_suffix(".pck").write_bytes(b"compiled production resources")
    stage = tmp_path / "unique"
    identity = freeze_candidate(candidate, stage)
    assert (stage / "NativeQA.exe").read_bytes() == candidate.read_bytes()
    assert (stage / "production.pck").read_bytes() == candidate.with_suffix(".pck").read_bytes()
    assert len(identity["exe"]) == len(identity["pck"]) == 64
    with pytest.raises(FileExistsError):
        freeze_candidate(candidate, stage)
    assert candidate.read_bytes() == b"actual release engine"


def test_missing_pck_does_not_create_staging(tmp_path):
    candidate = tmp_path / "Surgical.exe"
    candidate.write_bytes(b"engine")
    stage = tmp_path / "unique"
    with pytest.raises(FileNotFoundError):
        freeze_candidate(candidate, stage)
    assert not stage.exists()


@pytest.mark.parametrize("code,out,err,current", [
    (1, "Volumetric encounter: 0 failures", "", {"exe": "a", "pck": "b"}),
    (0, "started only", "", {"exe": "a", "pck": "b"}),
    (0, "Volumetric encounter: 0 failures", "SCRIPT ERROR: invalid", {"exe": "a", "pck": "b"}),
    (0, "ERROR: failed\nVolumetric encounter: 0 failures", "", {"exe": "a", "pck": "b"}),
    (0, "Volumetric encounter: 0 failures", "\x1b[31mERROR: failed\x1b[0m", {"exe": "a", "pck": "b"}),
    (0, "Volumetric encounter: 0 failures", "", {"exe": "a", "pck": "changed"}),
])
def test_zero_exit_alone_or_mutated_artifact_never_qualifies(code, out, err, current):
    assert assess(code, out, err, "normal", {"exe": "a", "pck": "b"}, current)


def test_full_matching_evidence_qualifies():
    identity = {"exe": "a", "pck": "b"}
    assert assess(0, "Volumetric encounter: 0 failures\n", "", "normal", identity, identity) == []


def test_production_pack_cannot_replace_trusted_qa_fixture(tmp_path):
    engine = Path(__file__).resolve().parents[1] / ".tools/godot/Godot_v4.7.2-stable_win64_console.exe"
    if not engine.is_file():
        pytest.skip("Optional local Godot integration: pinned editor unavailable")
    (tmp_path / "project.godot").write_text("config_version=5\n", encoding="utf-8")
    hostile = tmp_path / "replacement.gd"
    hostile.write_text('extends Node\nfunc _ready():\n\tprint("REPLACED_QA_FIXTURE"); get_tree().quit(0)\n', encoding="utf-8")
    pack = tmp_path / "production.pck"
    script = tmp_path / "pack.gd"
    script.write_text('extends SceneTree\nfunc _initialize():\n\tvar p=PCKPacker.new()\n'
                      f'\tif p.pck_start({json.dumps(pack.as_posix())})!=OK: quit(1); return\n'
                      f'\tif p.add_file("res://fixture.gd",{json.dumps(hostile.as_posix())})!=OK: quit(1); return\n'
                      '\tquit(0 if p.flush()==OK else 1)\n', encoding="utf-8")
    create = subprocess.run([str(engine), "--headless", "--path", str(tmp_path), "--script", str(script)],
                            capture_output=True, text=True, timeout=30)
    assert create.returncode == 0, create.stdout + create.stderr
    project = prepare_project(tmp_path, "control", {"pck": digest(pack)})
    (project / "fixture.gd").write_text('extends Node\nfunc _ready():\n\tprint("TRUSTED_QA_FIXTURE"); get_tree().quit(0)\n', encoding="utf-8")
    run = subprocess.run([str(engine), "--headless", "--path", str(project)],
                         capture_output=True, text=True, timeout=30)
    assert run.returncode == 0, run.stdout + run.stderr
    assert "TRUSTED_QA_FIXTURE" in run.stdout and "REPLACED_QA_FIXTURE" not in run.stdout
