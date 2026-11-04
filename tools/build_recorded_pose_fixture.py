"""Independent SciPy reference samples for the scalar-double Godot packet reader."""
import argparse
import json
import math
from pathlib import Path
import sys
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'native/tests'))
from test_contact_guard import linear,arc
from test_trajectory_contact import sample

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--output',type=Path,required=True)
args=parser.parse_args()
cases=[{'kinds':[0],'packets':linear([1.+2.**-40,.2,.3],[1.+2.**-38,.4,.7],.1)},
       {'kinds':[1],'packets':arc()}]
packet=arc()
packet[13:19]=[.1,.2,-.3,.3,-.1,.2]
packet[27:39]=[1.,.1,.2,.9,.3,.1,.8,-.1,.2,.7,.2,.3]
packet[39:41]=[.2,.8]
# Unique shortest arc with sign-flipped, slightly nonunit recorded quaternion.
# An exact180degree tie would allow SciPy and the packet convention to pick
# different equally short paths; the preceding analytic arc retains that tie.
packet[23:27]=[0.,0.,-math.sin(.4)*1.0001,-math.cos(.4)*1.0001]
cases.append({'kinds':[1],'packets':packet})
actual=json.loads((ROOT/'native/tests/fixtures/operative_motion144.json').read_text())['guard_request']
cases.append({'kinds':actual['kinds'],'packets':actual['packets']})
for case in cases:
    case['times']=[0.,.125,.25,.375,.5,.75,.875,1.]
    case['expected']=[]
    for t in case['times']:
        row=[]
        for kind,p in zip(case['kinds'],np.array(case['packets']).reshape(-1,41)):
            segment=sample(p,t) if kind else ((1-t)*p[:6]+t*p[6:12]).reshape(2,3)
            if t==0:segment=p[:6].reshape(2,3)
            if t==1:segment=p[6:12].reshape(2,3)
            row.extend(segment.ravel().tolist()+[float(p[12])])
        case['expected'].append(row)
args.output.parent.mkdir(parents=True,exist_ok=True)
args.output.write_text(json.dumps(cases,indent=2),encoding='utf-8')
