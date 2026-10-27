extends RefCounted
## Reduced capsule-cortex adhesion model; synthetic, dimensionless coefficients.
## Classification stays with each material particle as it moves or is aspirated.
var surface_flow:=false
var _flow_active:=false
var _all_released:=false
var _field:=PackedFloat64Array()
var _flow_edges:Array[Vector2i]=[]
var _flow_weights:=PackedFloat64Array()
var adhesion:=PackedFloat64Array()
var _rest:=PackedVector3Array()
var _cortex:=PackedByteArray()
func reset(positions:PackedVector3Array,cortex_radius:=.5)->void:
	_rest=positions.duplicate(); adhesion.resize(positions.size()); _cortex.resize(positions.size())
	for i in range(positions.size()):
		_cortex[i]=1 if Vector2(positions[i].x,positions[i].z).length()>cortex_radius else 0
		adhesion[i]=1. if _cortex[i] else 0.
	_flow_active=false; _all_released=false
	_field.resize(positions.size()); _field.fill(0.); _flow_edges=[]; _flow_weights=PackedFloat64Array()
	if surface_flow:
		for a in range(positions.size()):
			if not is_cortex(a): continue
			for b in range(a+1,positions.size()):
				var distance:=positions[a].distance_to(positions[b])
				if is_cortex(b) and distance<.62:
					_flow_edges.append(Vector2i(a,b)); _flow_weights.append(.5/maxf(.05,distance))
func is_cortex(index:int)->bool:
	return index>=0 and index<_cortex.size() and _cortex[index]!=0
func step(dt:float,tip:Vector3,flow:float,positions:PackedVector3Array,active:PackedByteArray)->void:
	if not is_finite(dt) or dt<=0. or dt>.05 or not tip.is_finite() or not is_finite(flow): return
	if positions.size()!=_rest.size() or active.size()!=_rest.size(): return
	for point in positions:
		if not point.is_finite(): return
	flow=clampf(flow,0.,1.)
	if surface_flow:
		if _all_released or (flow==0. and not _flow_active): return
		_surface_step(dt,tip,flow,positions,active); return
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

func _surface_step(dt:float,tip:Vector3,flow:float,positions:PackedVector3Array,active:PackedByteArray)->void:
	# A transported exposure field, not additional compartment volume or calibrated pressure.
	var weights:=PackedFloat64Array(); weights.resize(positions.size()); weights.fill(0.)
	var total:=0.
	for i in range(positions.size()):
		if active[i]==0 or not is_cortex(i): continue
		var distance:=positions[i].distance_to(tip)
		if distance<.24: weights[i]=1.-distance/.24; total+=weights[i]
	if total>0. and flow>0.: _flow_active=true
	if not _flow_active: return
	var count:=ceili(dt/(1./240.)); var h:=dt/count
	var delta:=PackedFloat64Array(); delta.resize(positions.size())
	for substep in range(count):
		if total>0. and flow>0.:
			for i in range(positions.size()):
				if weights[i]>0.: _field[i]=minf(1.,_field[i]+h*flow*3.*weights[i]/total)
		delta.fill(0.)
		for index in range(_flow_edges.size()):
			var edge:=_flow_edges[index]
			if active[edge.x]==0 or active[edge.y]==0: continue
			var transfer:=(_field[edge.x]-_field[edge.y])*minf(.045,h*12.*_flow_weights[index])
			delta[edge.x]-=transfer; delta[edge.y]+=transfer
		for i in range(positions.size()):
			if active[i]==0: _field[i]=0.; continue
			_field[i]=clampf((_field[i]+delta[i])*exp(-.15*h),0.,1.)
			if is_cortex(i): adhesion[i]=maxf(0.,adhesion[i]-h*_field[i]*1.5)

	_all_released=true
	for i in range(adhesion.size()):
		if is_cortex(i) and active[i]!=0 and adhesion[i]>0.: _all_released=false; break
