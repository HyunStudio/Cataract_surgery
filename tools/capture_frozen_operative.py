"""Observe the same frozen blade route and preserve exact failure inputs."""
import argparse
import json
import re
from pathlib import Path
import subprocess
from native_build_provenance import sha256
root=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--report',type=Path,required=True);parser.add_argument('--name',required=True);args=parser.parse_args()
if not args.name or any(x not in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_' for x in args.name):raise SystemExit('Diagnostic name must be a filename component')
report=json.loads(args.report.read_text());probe=Path(report['probe']);expected=report['frozen_inputs'];engine=root/'.tools/godot/Godot_v4.7.2-stable_win64_console.exe'
if sha256(engine)!=report['engine_sha256']:raise SystemExit('Pinned engine differs from report')
if not all(sha256(probe/name)==value for name,value in expected.items()):raise SystemExit('Frozen input changed before capture')
script='tests/capture_operative_trajectory.gd'
if script not in {Path(name).as_posix() for name in expected}:raise SystemExit('Transparent capture script was not frozen')
log=probe/(args.name+'.log');output=root/'godot/reports'/(args.name+'.json')
evidence={'qualified':False,'status':'running','scope':'Transparent observation of identical frozen blade route only; not whole-operation, real-time or release qualification.','probe':str(probe),'source_report':str(args.report),'source_report_sha256':sha256(args.report),'engine_sha256':sha256(engine),'frozen_inputs':expected,'script':script};output.write_text(json.dumps(evidence,indent=2));print('Capturing frozen operative route: '+str(probe),flush=True)
with log.open('wb') as sink:completed=subprocess.run([str(engine),'--headless','--path',str(probe),'--script','res://'+script],stdout=sink,stderr=subprocess.STDOUT)
if not all(sha256(probe/name)==value for name,value in expected.items()):raise SystemExit('Frozen input changed during capture')
text=re.sub(r'\x1b\[[0-?]*[ -/]*[@-~]', '', log.read_text(encoding='utf-8',errors='replace'))
route_passed=completed.returncode==0 and 'Closed blade result: 0 failures' in text and not re.search(r'ERROR:|SCRIPT ERROR|leaked at exit|resources still in use',text)
evidence.update(status='completed',route_passed=route_passed,returncode=completed.returncode,log=str(log),log_sha256=sha256(log));output.write_text(json.dumps(evidence,indent=2));print(json.dumps({k:v for k,v in evidence.items() if k!='frozen_inputs'}),flush=True)
