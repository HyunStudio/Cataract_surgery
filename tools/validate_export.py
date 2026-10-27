"""Qualify frozen production PCK resources under the identical Windows release engine.

This is not a test of the original main-scene startup or human input choreography.
No candidate files are written; interrupted/running jobs retain their logs and PID.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import uuid


SCENARIOS = {
    "normal": ("test_volumetric_encounter.gd", "Volumetric encounter: 0 failures"),
    "adverse": ("test_volumetric_injury.gd", "Volumetric injury: 0 failures"),
    "control": ("test_control_context.gd", "Control context: 0 failures"),
}
REPO = Path(__file__).resolve().parents[1]


def plain_log(value: str) -> str:
    return re.sub(r"\x1b(?:\[[0-?]*[ -/]*[@-~]|\][^\x07\x1b]*(?:\x07|\x1b\\))", "", value).replace("\r", "\n")


def engine_error(stdout: str, stderr: str) -> bool:
    return bool(re.search(r"(?:SCRIPT ERROR:|(?:^|\n)\s*ERROR:)", plain_log(stdout + "\n" + stderr)))


def digest(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def pair_identity(candidate: Path) -> dict[str, str]:
    return {"exe": digest(candidate), "pck": digest(candidate.with_suffix(".pck"))}


def freeze_candidate(candidate: Path, stage: Path) -> dict[str, str]:
    identity = pair_identity(candidate)  # Validate both before creating anything.
    stage.mkdir(parents=True, exist_ok=False)
    shutil.copyfile(candidate, stage / "NativeQA.exe")
    shutil.copyfile(candidate.with_suffix(".pck"), stage / "production.pck")
    frozen = {"exe": digest(stage / "NativeQA.exe"), "pck": digest(stage / "production.pck")}
    if frozen != identity or pair_identity(candidate) != identity:
        raise ValueError("Candidate changed while freezing the artifact")
    return identity


def adapt_fixture(source: str, scenario: str) -> str:
    if scenario not in SCENARIOS:
        raise ValueError("Unsupported scenario")
    if not source.startswith("extends SceneTree\n") or source.count("func _initialize()") != 1:
        raise ValueError("Unsupported fixture lifecycle; review the adapter")
    if source.count("quit(1 if failures else 0)") != 1 or "await physics_frame" in source:
        raise ValueError("Unsupported fixture outcome or frame lifecycle")
    source = source.replace("extends SceneTree\n", "extends Node\n", 1)
    source = source.replace("func _initialize()", "func _ready()", 1)
    source = re.sub(r"(?<![\w.])root\.", "get_tree().root.", source)
    source = source.replace("await process_frame", "await get_tree().process_frame")
    source = re.sub(r"(?<![\w.])quit\(", "get_tree().quit(", source)
    source = source.replace("res://reports/", "user://native-validation/")
    if re.search(r"\bSceneTree\b|\b_initialize\b|(?<![\w.])(?:root\.|process_frame\b|quit\()", source):
        raise ValueError("Unadapted SceneTree reference; review the adapter")
    return source


def assess(code: int, stdout: str, stderr: str, scenario: str,
           expected: dict[str, str], current: dict[str, str]) -> list[str]:
    reasons = []
    if code != 0:
        reasons.append(f"Release fixture exited {code}")
    if SCENARIOS[scenario][1] not in plain_log(stdout).splitlines():
        reasons.append("Expected completed zero-failure outcome absent")
    if engine_error(stdout, stderr):
        reasons.append("Engine error in fixture output")
    if current != expected:
        reasons.append("Candidate or frozen production artifacts changed")
    return reasons


def prepare_project(stage: Path, scenario: str, identity: dict[str, str]) -> Path:
    project = stage / "qa-project"
    project.mkdir()
    source = (REPO / "godot/tests" / SCENARIOS[scenario][0]).read_text(encoding="utf-8")
    (stage / "source-fixture.gd").write_text(source, encoding="utf-8")
    (project / "fixture.gd").write_text(adapt_fixture(source, scenario), encoding="utf-8")
    settings = (REPO / "godot/project.godot").read_text(encoding="utf-8")
    for key, replacement in [("config/name", '"OphthoSim Native QA ' + stage.name + '"'),
                             ("run/main_scene", '"res://qa.tscn"')]:
        settings, count = re.subn(r"^" + re.escape(key) + r"=.*$", key + "=" + replacement,
                                 settings, flags=re.MULTILINE)
        if count != 1:
            raise ValueError("Unsupported production settings: " + key)
    (project / "project.godot").write_text(settings, encoding="utf-8")
    pack = json.dumps((stage / "production.pck").as_posix())
    bootstrap = f'''extends Node
func _ready()->void:
\tprint("Native release QA executable=",OS.get_executable_path())
\tvar pack:String={pack}
\tvar actual:=FileAccess.get_sha256(pack)
\tprint("Production PCK SHA256=",actual)
\tif actual!="{identity['pck']}" or not ProjectSettings.load_resource_pack(pack,false):
\t\tpush_error("Frozen production PCK unavailable or changed"); get_tree().quit(1); return
\tif FileAccess.file_exists("res://tests/{SCENARIOS[scenario][0]}"):
\t\tpush_error("Developer fixture leaked into production PCK"); get_tree().quit(1); return
\tDirAccess.make_dir_recursive_absolute(ProjectSettings.globalize_path("user://native-validation"))
\tprint("QA output directory=",ProjectSettings.globalize_path("user://native-validation"))
\tvar fixture=load("res://fixture.gd")
\tif not fixture:
\t\tpush_error("QA fixture unavailable"); get_tree().quit(1); return
\tadd_child(fixture.new())
'''
    (project / "qa.gd").write_text(bootstrap, encoding="utf-8")
    (project / "qa.tscn").write_text('[gd_scene load_steps=2 format=3]\n\n'
                                    '[ext_resource type="Script" path="res://qa.gd" id="1"]\n\n'
                                    '[node name="NativeQA" type="Node"]\nscript = ExtResource("1")\n',
                                    encoding="utf-8")
    # Only the tiny QA project is exported. Product scripts/assets come from the mounted pack.
    (project / "export_presets.cfg").write_text('''[preset.0]
name="Native QA"
platform="Windows Desktop"
runnable=true
export_filter="all_resources"
include_filter=""
exclude_filter=""
script_export_mode=2

[preset.0.options]
binary_format/embed_pck=false
binary_format/architecture="x86_64"
texture_format/s3tc_bptc=true
texture_format/etc2_astc=false
''', encoding="utf-8")
    return project


def run_logged(command: list[str], stage: Path, label: str, report: dict, save) -> tuple[int, str, str]:
    out, err = stage / f"{label}.log", stage / f"{label}.err"
    with out.open("w", encoding="utf-8") as stdout, err.open("w", encoding="utf-8") as stderr:
        process = subprocess.Popen(command, stdout=stdout, stderr=stderr,
                                   creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
        report.update(phase=label, pid=process.pid, command=command)
        save()
        print(f"{label}: PID {process.pid}; {out}", flush=True)
        code = process.wait()  # No observation timeout terminates the simulation.
    report.setdefault("exit_codes", {})[label] = code
    save()
    return code, out.read_text(encoding="utf-8", errors="replace"), err.read_text(encoding="utf-8", errors="replace")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("candidate", type=Path, help="Exported Windows .exe with sibling .pck")
    parser.add_argument("--scenario", choices=SCENARIOS, default="control")
    parser.add_argument("--engine", type=Path,
                        default=REPO / ".tools/godot/Godot_v4.7.2-stable_win64_console.exe")
    parser.add_argument("--gpu", action="store_true", help="Run alone: focus loss disarms production controls")
    args = parser.parse_args()
    candidate, engine = args.candidate.resolve(), args.engine.resolve()
    if not candidate.is_file() or candidate.suffix.lower() != ".exe" or not engine.is_file():
        parser.error("Existing Windows candidate .exe and Godot editor executable required")
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex[:8]
    stage = REPO / ".tools/export-validation" / stamp
    identity = freeze_candidate(candidate, stage)
    report = {"status": "running", "scenario": args.scenario, "candidate": str(candidate),
              "identity": identity, "stage": str(stage), "gpu": args.gpu,
              "adapter_sha256": digest(Path(__file__)), "editor_sha256": digest(engine),
              "scope": "compiled production resources under identical release engine; original startup not qualified"}

    def save():
        (stage / "result.json").write_text(json.dumps(report, indent=2), encoding="utf-8")

    save()
    print(f"Frozen candidate: {identity}; report {stage / 'result.json'}", flush=True)
    try:
        project = prepare_project(stage, args.scenario, identity)
        report["source_commit"] = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO, text=True).strip()
        report["source_status"] = subprocess.check_output(["git", "status", "--porcelain"], cwd=REPO, text=True).splitlines()
        report["source_fixture_sha256"] = digest(stage / "source-fixture.gd")
        report["qa_inputs_sha256"] = {path.name: digest(path) for path in project.iterdir() if path.is_file()}
        save()
        for label, command in [
            ("import", [str(engine), "--headless", "--path", str(project), "--editor", "--import"]),
            ("export", [str(engine), "--headless", "--path", str(project), "--export-pack",
                        "Native QA", str(stage / "NativeQA.pck")]),
        ]:
            code, out, err = run_logged(command, stage, label, report, save)
            if code or engine_error(out, err):
                raise ValueError(label + " failed; inspect retained logs")
        report["qa_pack_sha256"] = digest(stage / "NativeQA.pck")
        command = [str(stage / "NativeQA.exe")]
        if not args.gpu:
            command.append("--headless")
        code, out, err = run_logged(command, stage, "fixture", report, save)
        current = pair_identity(candidate)
        frozen = {"exe": digest(stage / "NativeQA.exe"), "pck": digest(stage / "production.pck")}
        reasons = assess(code, out, err, args.scenario, identity, current)
        if frozen != identity:
            reasons.append("Frozen executable or production PCK changed")
        if "Production PCK SHA256=" + identity["pck"] not in plain_log(out).splitlines():
            reasons.append("Production PCK mount evidence absent")
        report.update(status="failed" if reasons else "passed", reasons=reasons,
                      candidate_after=current, frozen_after=frozen)
    except Exception as error:
        report.update(status="failed", reasons=[str(error)])
    finally:
        save()
    print(f"{report['status']}: {stage / 'result.json'}", flush=True)
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
