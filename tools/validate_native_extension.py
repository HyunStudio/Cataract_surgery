"""Fresh-import gate for the isolated experimental extension; preserves failed probes."""
import argparse
import json
import re
from pathlib import Path
import shutil
import subprocess
import tempfile
from native_build_provenance import sha256, source_hashes, verify_sources

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--raw-import",action="store_true",help="Reproduce upstream editor shutdown race without its timing workaround")
parser.add_argument("--capsule",action="store_true",help="Run the actual capsule integration test against frozen product sources")
parser.add_argument("--capsule-extraction",action="store_true",help="Run refined native flap extraction with real forceps-body and anatomical contact")
parser.add_argument("--coupled-capsule",action="store_true",help="Run packed64 actual joint capsule timestep checks")
parser.add_argument("--coupled-extraction",action="store_true",help="Replay the canonical complete extraction with the packed64 joint backend")
options = parser.parse_args()
if options.coupled_capsule and (options.capsule_extraction or options.coupled_extraction): parser.error("Select one coupled validation scope")
options.capsule_extraction = options.capsule_extraction or options.coupled_extraction
options.capsule = options.capsule or options.capsule_extraction or options.coupled_capsule
report = ROOT/("godot/reports/native-coupled-extraction-validation.json" if options.coupled_extraction else "godot/reports/native-coupled-capsule-validation.json" if options.coupled_capsule else "godot/reports/native-capsule-extraction-validation.json" if options.capsule_extraction else "godot/reports/native-capsule-validation.json" if options.capsule else "godot/reports/native-extension-validation-no-delay.json" if options.raw_import else "godot/reports/native-extension-validation.json")
report.parent.mkdir(parents=True,exist_ok=True)
report.write_text(json.dumps({"qualified":False,"state":"preparing","validator_sha256":sha256(Path(__file__))}),encoding="utf-8")
source = ROOT/".tools/native-godot"
artifact = source/"bin/membrane.dll"
manifest = json.loads((source/"bin/membrane.build.json").read_text())
if sha256(artifact) != manifest["artifact_sha256"]: raise SystemExit("Extension differs from its build manifest")
verify_sources(manifest["sources"])
probe = Path(tempfile.mkdtemp(prefix="membrane-validation-",dir=ROOT/".tools"))
(probe/"bin").mkdir()
intended = {"project.godot":ROOT/"native/test_project.godot", "test_bridge.gd":ROOT/"native/tests/test_godot_bridge.gd",
            "local_jaw_contact.json":ROOT/"native/tests/fixtures/local_jaw_contact.json",
            "refined_flap.json":ROOT/"native/tests/fixtures/refined_flap.json", "bin/membrane.gdextension":ROOT/"native/membrane.gdextension"}
if options.capsule:
    # Freeze tracked project resources while retaining the isolated test project config.
    tracked = subprocess.check_output(["git","ls-files","--","godot"],cwd=ROOT,text=True).splitlines()
    for name in tracked:
        path = ROOT/name
        if path.is_file() and name != "godot/project.godot": intended[str(path.relative_to(ROOT/"godot"))] = path
    intended["test_capsule.gd"] = ROOT/("godot/tests/test_capsule_coupled.gd" if options.coupled_capsule else "godot/tests/test_capsule_native_extraction.gd" if options.capsule_extraction else "godot/tests/test_capsule_native.gd")
    adapter = ROOT/"godot/scripts/native_membrane_backend.gd"
    if adapter.exists(): intended["scripts/native_membrane_backend.gd"] = adapter
if options.coupled_capsule:
    intended["iris_boundary265.json"]=ROOT/"native/tests/fixtures/iris_boundary265.json"
    for fixture in ["joint_physical264_second.json","joint_physical265.json"]: intended[fixture]=ROOT/"native/tests/fixtures"/fixture
    for fixture in ["joint_static262.json","joint_motion262.json","joint_trajectory264_second.json"]: intended[fixture]=ROOT/"native/tests/fixtures"/fixture
test_sources = source_hashes([*intended.values(),Path(__file__).resolve()])
for name,path in intended.items():
    (probe/name).parent.mkdir(parents=True,exist_ok=True)
    shutil.copyfile(path,probe/name)
    if sha256(probe/name) != test_sources[str(path.relative_to(ROOT))]: raise SystemExit("Frozen native test differs from intended source")
shutil.copyfile(artifact,probe/"bin/membrane.dll")
if sha256(probe/"bin/membrane.dll") != manifest["artifact_sha256"]:
    raise SystemExit("Frozen extension differs from its build manifest")
verify_sources(test_sources)
expected = {name:sha256(probe/name) for name in [*intended,"bin/membrane.dll"]}
editor = ROOT/".tools/godot/Godot_v4.7.2-stable_win64_console.exe"
engine = editor.with_name("Godot_v4.7.2-stable_win64.exe")
scope = ("optional packed64 joint canonical extraction with actual bodies and anatomical guards; not whole-app qualification" if options.coupled_extraction else "optional packed64 joint actual capsule timestep and incision/rollback; not whole-app qualification" if options.coupled_capsule else "optional actual capsule native refined extraction with forceps-body and anatomical contact; not whole-app qualification" if options.capsule_extraction else
         "optional actual capsule native integration: refined rest/traction, gentle moving body contact and transactional failures; not whole-app qualification"
         if options.capsule else "isolated native bridge first import and headless packed-array contract")
proof = {"scope":scope,
         "qualified":False,"probe":str(probe),"inputs":expected,"test_sources":test_sources,"build":manifest,
         "launcher_sha256":sha256(editor),"engine_sha256":sha256(engine),
         "import_frame_delay_ms":0 if options.raw_import else 25,
         "import_quit_after_frames":None if options.raw_import else 35,"stages":[]}
# Godot upstream#111048/#123658: deferred editor documentation can outlive
# fast headless import shutdown. Explicit editor frames address the documented
# lifecycle race; completed import stages are required too. Runtime is undelayed.
import_args = ["--editor","--import"]+([] if options.raw_import else ["--quit-after","35","--frame-delay","25"])
runtime_script = "res://test_capsule.gd" if options.capsule else "res://test_bridge.gd"
runtime_marker = "Native coupled capsule: 0 failures" if options.coupled_capsule else "Native capsule extraction: 0 failures" if options.capsule_extraction else "Native capsule: 0 failures" if options.capsule else "Native Godot bridge: 0 failures"
runtime_args = ["--script",runtime_script]+(["--","--joint-contact"] if options.coupled_extraction else [])
for name, args, marker in [("fresh_import",import_args,None),
                            ("capsule" if options.capsule else "bridge",runtime_args,runtime_marker)]:
    log = probe/f"{name}.log"
    print(f"Native validation {name}: {probe}",flush=True)
    with log.open("wb") as output:
        process = subprocess.run([str(editor),"--headless","--path",str(probe),*args],stdout=output,stderr=subprocess.STDOUT)
    text = log.read_text(encoding="utf-8",errors="replace")
    plain_text = re.sub(r"\x1b\[[0-?]*[ -/]*[@-~]","",text)
    passed = process.returncode == 0 and "ERROR:" not in plain_text and "SCRIPT ERROR" not in plain_text and (marker is None or marker in plain_text)
    stages = set(re.findall(r"^\[[^\]]+\]\s+(\w+)\s+\|",plain_text,re.MULTILINE)) if name=="fresh_import" else set()
    completed = set(re.findall(r"^\[ DONE \]\s+(\w+)",plain_text,re.MULTILINE)) if name=="fresh_import" else set()
    if name=="fresh_import": passed = passed and {"first_scan_filesystem","loading_editor_layout"}<=completed and stages<=completed
    proof["stages"].append({"name":name,"arguments":args,"returncode":process.returncode,"passed":passed,"log":str(log),"log_sha256":sha256(log),"completed_import_stages":sorted(completed)})
    if not passed: break
verify_sources(manifest["sources"])
verify_sources(test_sources)
if any(sha256(probe/name) != value for name,value in expected.items()):
    raise SystemExit("Validation inputs changed during the run")
proof["qualified"] = len(proof["stages"]) == 2 and all(stage["passed"] for stage in proof["stages"])
report.write_text(json.dumps(proof,indent=2),encoding="utf-8")
print(json.dumps({"qualified":proof["qualified"],"stages":proof["stages"],"report":str(report)},indent=2))
raise SystemExit(0 if proof["qualified"] else 1)
