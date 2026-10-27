"""Fresh-import gate for the isolated experimental extension; preserves failed probes."""
import argparse
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
from native_build_provenance import sha256, source_hashes, verify_sources

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--raw-import",action="store_true",help="Reproduce upstream editor shutdown race without its timing workaround")
options = parser.parse_args()
report = ROOT/("godot/reports/native-extension-validation-no-delay.json" if options.raw_import else "godot/reports/native-extension-validation.json")
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
            "refined_flap.json":ROOT/"native/tests/fixtures/refined_flap.json", "bin/membrane.gdextension":ROOT/"native/membrane.gdextension"}
test_sources = source_hashes([*intended.values(),Path(__file__).resolve()])
for name,path in intended.items():
    shutil.copyfile(path,probe/name)
    if sha256(probe/name) != test_sources[str(path.relative_to(ROOT))]: raise SystemExit("Frozen native test differs from intended source")
shutil.copyfile(artifact,probe/"bin/membrane.dll")
if sha256(probe/"bin/membrane.dll") != manifest["artifact_sha256"]:
    raise SystemExit("Frozen extension differs from its build manifest")
verify_sources(test_sources)
expected = {name:sha256(probe/name) for name in ["project.godot","test_bridge.gd","refined_flap.json","bin/membrane.gdextension","bin/membrane.dll"]}
editor = ROOT/".tools/godot/Godot_v4.7.2-stable_win64_console.exe"
engine = editor.with_name("Godot_v4.7.2-stable_win64.exe")
proof = {"scope":"isolated native bridge first import and headless packed-array contract",
         "qualified":False,"probe":str(probe),"inputs":expected,"test_sources":test_sources,"build":manifest,
         "launcher_sha256":sha256(editor),"engine_sha256":sha256(engine),
         "import_frame_delay_ms":0 if options.raw_import else 1000,"stages":[]}
# Godot upstream#111048/#123658: deferred editor documentation can outlive
# fast headless import shutdown. Delay editor frames only; never change physics.
import_args = ["--editor","--import"]+([] if options.raw_import else ["--frame-delay","1000"])
for name, args, marker in [("fresh_import",import_args,None),
                            ("bridge",["--script","res://test_bridge.gd"],"Native Godot bridge: 0 failures")]:
    log = probe/f"{name}.log"
    print(f"Native validation {name}: {probe}",flush=True)
    with log.open("wb") as output:
        process = subprocess.run([str(editor),"--headless","--path",str(probe),*args],stdout=output,stderr=subprocess.STDOUT)
    text = log.read_text(encoding="utf-8",errors="replace")
    passed = process.returncode == 0 and "ERROR:" not in text and "SCRIPT ERROR" not in text and (marker is None or marker in text)
    proof["stages"].append({"name":name,"arguments":args,"returncode":process.returncode,"passed":passed,"log":str(log),"log_sha256":sha256(log)})
    if not passed: break
verify_sources(manifest["sources"])
verify_sources(test_sources)
if any(sha256(probe/name) != value for name,value in expected.items()):
    raise SystemExit("Validation inputs changed during the run")
proof["qualified"] = len(proof["stages"]) == 2 and all(stage["passed"] for stage in proof["stages"])
report.write_text(json.dumps(proof,indent=2),encoding="utf-8")
print(json.dumps({"qualified":proof["qualified"],"stages":proof["stages"],"report":str(report)},indent=2))
raise SystemExit(0 if proof["qualified"] else 1)
