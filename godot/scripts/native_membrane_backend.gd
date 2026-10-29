extends RefCounted
func invalidate_cache()->void: _cache.clear()
## Optional global XPBD proximal update. This is not calibrated capsule mechanics.
const FORCE_TOLERANCE:=1e-8
const CURVATURE_REFINEMENT_TOLERANCE:=1e-12
var _kernel:RefCounted
var _cache:Dictionary={}
var _calls:=0
var _hits:=0
var _last_stats:=PackedFloat64Array()
var diagnostic_capture:=""
func _init()->void:
	if ClassDB.class_exists("MembraneKernel"): _kernel=ClassDB.instantiate("MembraneKernel")
func ready()->bool: return _kernel!=null
func diagnostics()->Dictionary: return {"calls":_calls,"cache_hits":_hits,"last_stats":_last_stats.duplicate()}
func project(points:PackedVector3Array,inverse:PackedFloat64Array,a:PackedInt32Array,b:PackedInt32Array,rest:PackedFloat64Array,active:PackedByteArray,multipliers:PackedFloat64Array,alpha:float)->Dictionary:
	if not ready() or not is_finite(alpha) or alpha<=0.: return {"valid":false,"reason":"native_unavailable_or_compliance"}
	if inverse.size()!=points.size() or a.size()!=b.size() or a.size()!=rest.size() or a.size()!=active.size() or a.size()!=multipliers.size(): return {"valid":false,"reason":"native_shape"}
	var key:Dictionary={"points":points,"inverse":inverse,"a":a,"b":b,"rest":rest,"active":active,"lambda":multipliers,"alpha":alpha}
	if key==_cache:
		_hits+=1; return {"valid":true,"positions":points.duplicate(),"lambda":multipliers.duplicate()}
	var xyz:=PackedFloat64Array(); xyz.resize(points.size()*3)
	for i in range(points.size()):
		for axis in range(3): xyz[i*3+axis]=points[i][axis]
	var ea:=PackedInt32Array(); var eb:=PackedInt32Array(); var lengths:=PackedFloat64Array()
	for e in range(a.size()):
		if a[e]<0 or b[e]<0 or a[e]>=points.size() or b[e]>=points.size(): return {"valid":false,"reason":"native_index"}
		if active[e]==0 or inverse[a[e]]+inverse[b[e]]==0.: continue
		var effective:float=rest[e]-alpha*multipliers[e]
		if not is_finite(effective) or effective<=0.: return {"valid":false,"reason":"native_effective_rest"}
		ea.append(a[e]); eb.append(b[e]); lengths.append(effective)
	_calls+=1
	var result:Dictionary=_kernel.solve(xyz,inverse,ea,eb,lengths,alpha,100,FORCE_TOLERANCE)
	# A small nonzero gradient can pass the ordinary stopping norm before the
	# compressed soft modes settle. Tighten it once; never accept a failed status.
	if result.status==3 and result.stats[1]>0. and result.stats[1]<=FORCE_TOLERANCE:
		_calls+=1
		result=_kernel.solve(xyz,inverse,ea,eb,lengths,alpha,100,CURVATURE_REFINEMENT_TOLERANCE)
	_last_stats=result.stats.duplicate()
	if result.status!=0:
		if not diagnostic_capture.is_empty() and not FileAccess.file_exists(diagnostic_capture):
			var file:=FileAccess.open(diagnostic_capture,FileAccess.WRITE)
			if file: file.store_string(JSON.stringify({"xyz":Array(xyz),"inverse":Array(inverse),"a":Array(ea),"b":Array(eb),"rest":Array(lengths),"alpha":alpha,"status":result.status,"stats":Array(_last_stats)}))
		return {"valid":false,"reason":"native_solve","status":result.status,"stats":_last_stats}
	var out:=PackedVector3Array(); out.resize(points.size())
	for i in range(points.size()): out[i]=Vector3(result.xyz[3*i],result.xyz[3*i+1],result.xyz[3*i+2])
	var next_lambda:=multipliers.duplicate()
	# A fully prescribed edge still carries a compliant reaction; it needs no
	# positional unknown in the native solve, but its constitutive dual is not zero.
	for e in range(a.size()):
		if active[e]==0: continue
		var squared:=0.
		for axis in range(3): squared+=pow(result.xyz[3*a[e]+axis]-result.xyz[3*b[e]+axis],2)
		next_lambda[e]=-(sqrt(squared)-rest[e])/alpha
	_cache=key.duplicate(true); _cache.points=out.duplicate(); _cache["lambda"]=next_lambda.duplicate()
	return {"valid":true,"positions":out,"lambda":next_lambda}
