"""Decode raw little-endian engine doubles without the Godot JSON numeric parser."""
import argparse
import base64
import json
from pathlib import Path
import struct
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('input',type=Path);parser.add_argument('output',type=Path)
args=parser.parse_args()
def decode(value):
 if isinstance(value,dict):
  if set(value)=={'f64_le'}:
   raw=base64.b64decode(value['f64_le'],validate=True)
   if len(raw)%8:raise ValueError('Malformed double byte count')
   return list(struct.unpack('<'+'d'*(len(raw)//8),raw))
  return {k:decode(v) for k,v in value.items()}
 if isinstance(value,list):return [decode(v) for v in value]
 return value
packet=decode(json.loads(args.input.read_text(encoding='utf-8')))
args.output.write_text(json.dumps(packet,separators=(',',':'),allow_nan=False),encoding='utf-8')
print(json.dumps({'source_sha256':packet['source_sha256'],'state_summary':packet['state_summary'],'requests':len(packet['native_history'])}))
