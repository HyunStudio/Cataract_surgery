extends RefCounted
## Reduced capsule-cortex adhesion model; synthetic, dimensionless coefficients.
## Classification stays with each material particle as it moves or is aspirated.
var adhesion:=PackedFloat64Array()
var _rest:=PackedVector3Array()
var _cortex:=PackedByteArray()
func reset(positions:PackedVector3Array)->void:
	_rest=positions.duplicate(); adhesion.resize(positions.size()); _cortex.resize(positions.size())
	for i in range(positions.size()):
		_cortex[i]=1 if Vector2(positions[i].x,positions[i].z).length()>.5 else 0
		adhesion[i]=1. if _cortex[i] else 0.
func is_cortex(index:int)->bool:
	return index>=0 and index<_cortex.size() and _cortex[index]!=0
func step(dt:float,tip:Vector3,flow:float,positions:PackedVector3Array,active:PackedByteArray)->void:
	if not is_finite(dt) or dt<=0. or dt>.05 or not tip.is_finite() or not is_finite(flow): return
	if positions.size()!=_rest.size() or active.size()!=_rest.size(): return
	for point in positions:
		if not point.is_finite(): return
	flow=clampf(flow,0.,1.)
	if flow==0.: return
	for i in range(positions.size()):
		if active[i]==0 or not is_cortex(i): continue
		var distance:=positions[i].distance_to(tip)
		if distance<.24:
			adhesion[i]=maxf(0.,adhesion[i]-dt*flow*1.5*(1.-distance/.24))
func peel_weight(a:int,b:int,tip:Vector3,positions:PackedVector3Array)->float:
	var strongest:=0.
	for index in [a,b]:
		if not is_cortex(index) or adhesion[index]>=.35: continue
		var distance:=positions[index].distance_to(tip)
		if distance<.16: strongest=maxf(strongest,1.-distance/.16)
	return strongest
func adhesion_acceleration(index:int,position:Vector3)->Vector3:
	if not is_cortex(index) or not position.is_finite(): return Vector3.ZERO
	return ((_rest[index]-position)*adhesion[index]*60.).limit_length(4.)
func metrics(active:PackedByteArray,masses:PackedFloat64Array)->Dictionary:
	var nucleus:=0.; var cortex:=0.; var released:=0.; var count:=0
	if active.size()!=_rest.size() or masses.size()!=_rest.size(): return {}
	for i in range(active.size()):
		if is_cortex(i):
			count+=1; released+=1.-adhesion[i]
			if active[i]!=0: cortex+=masses[i]
		elif active[i]!=0: nucleus+=masses[i]
	return {"nucleus_remaining":nucleus,"cortex_remaining":cortex,"adhesion_released":released/maxi(count,1)}
