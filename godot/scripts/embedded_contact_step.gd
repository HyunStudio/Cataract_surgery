extends RefCounted
## Coupled candidate checks and full physical body interval guard; no projection.
const GeometryLimits=preload("res://scripts/fine_geometry_limits.gd")
const Query=preload("res://scripts/membrane_contact_query.gd")
const Pose=preload("res://scripts/recorded_body_pose.gd")
const GAP:=1e-9
const COMP:=1e-11
static func invalid(reason:String)->Dictionary:
	return {"valid":false,"changed":false,"reason":reason}
static func prepare(state:Dictionary,motion:Dictionary)->Dictionary:
	if not motion.get("kinds") is PackedInt32Array or not motion.get("packets") is PackedFloat64Array:return invalid("contact_motion_shape")
	var guard=motion.get("guard")
	if guard==null or not guard.has_method("guard_motion"):return invalid("contact_guard_unavailable")
	if state.rest.size()>GeometryLimits.LEGACY_POINTS and not guard.has_method("guard_fine_motion"):return invalid("contact_fine_guard_unavailable")
	var kinds:PackedInt32Array=motion.kinds;var packets:PackedFloat64Array=motion.packets
	if kinds.size()>64 or packets.size()!=kinds.size()*41 or (state.indices.size()/3)*kinds.size()>65536:return invalid("contact_motion_budget")
	for value in packets:
		if not is_finite(value):return invalid("contact_motion_coordinate")
	var capsules:=PackedFloat64Array()
	for body in range(kinds.size()):
		if kinds[body] not in [0,1]:return invalid("contact_motion_kind")
		var off:=body*41
		for k in range(12):
			if absf(packets[off+k])>16.:return invalid("contact_motion_coordinate")
		if packets[off+12]<=GAP or packets[off+12]>.3:return invalid("contact_motion_radius")
		capsules.append_array(packets.slice(off+6,off+13))
	return {"valid":true,"reason":"","kinds":kinds.duplicate(),"packets":packets.duplicate(),"capsules":capsules,"bodies":kinds.size(),"guard":guard}
static func force(state:Dictionary,xyz:PackedFloat64Array,dual:PackedFloat64Array,context:Dictionary,backend)->Dictionary:
	var faces:int=state.indices.size()/3
	var times:PackedFloat64Array=context.get("times",PackedFloat64Array([1.]))
	if dual.size()!=faces*context.bodies*times.size():return invalid("native_contact_dual_shape")
	var views:Array=[];var layers:Array=[]
	for t in times:
		var view:=state.duplicate(false);var posed:=xyz.duplicate()
		if t!=1.:
			if not context.get("previous") is PackedFloat64Array or context.previous.size()!=xyz.size():return invalid("contact_previous_shape")
			for k in range(posed.size()):posed[k]=context.previous[k]+t*(xyz[k]-context.previous[k])
		view.xyz=posed;views.append(view)
		if times.size()==1:layers.append(context.capsules)
		else:
			var sampled:=Pose.sample(context.kinds,context.packets,t)
			if not sampled.valid:return invalid("independent_contact_pose")
			layers.append(sampled.capsules)
	var distributed:=PackedFloat64Array();distributed.resize(xyz.size());var complementarity:=0.
	for pair in range(dual.size()):
		var u:float=dual[pair]
		if not is_finite(u) or u<0.:return invalid("native_contact_dual")
		if u==0.:continue
		var layer:int=pair/(faces*context.bodies);var t:float=times[layer]
		var face:int=(pair/context.bodies)%faces;var body:int=pair%context.bodies;var off:=body*7;var radius:float=layers[layer][off+6]
		var witness:=Query.face(views[layer],face,layers[layer].slice(off,off+6),radius,backend)
		if not witness.valid:return invalid("independent_contact_witness")
		if witness.values[1] < -GAP:return invalid("independent_contact_gap")
		complementarity=maxf(complementarity,absf(u*(witness.values[0]/(radius*radius)-1.)))
		if complementarity>COMP:return invalid("independent_contact_complementarity")
		for node in range(3):
			for axis in range(3):distributed[witness.nodes[node]*3+axis]-=u*t*witness.gradient[node*3+axis]/(radius*radius)
	return {"valid":true,"reason":"","force":distributed,"complementarity":complementarity}
static func guard(previous:PackedFloat64Array,current:PackedFloat64Array,triangles:PackedInt32Array,context:Dictionary)->Dictionary:
	if previous.size()!=current.size() or previous.is_empty() or previous.size()%3!=0 or previous.size()/3>GeometryLimits.FINE_POINTS:return invalid("contact_guard_geometry_shape")
	var method:="guard_fine_motion" if previous.size()/3>GeometryLimits.LEGACY_POINTS else "guard_motion"
	if not context.guard.has_method(method):return invalid("contact_fine_guard_unavailable")
	var answer=context.guard.call(method,{"previous":previous,"current":current,"triangles":triangles,"kinds":context.kinds,"packets":context.packets,"budget":128,"gap_tolerance":GAP})
	if not answer is Dictionary or not answer.get("status") is int or not answer.get("stats") is PackedFloat64Array or answer.stats.size()!=8:return invalid("native_contact_guard_shape")
	if answer.status!=0:return {"valid":false,"changed":false,"reason":"native_contact_motion","status":answer.status,"stats":answer.stats,"witness_t":answer.get("witness_t",-1.)}
	for k in range(8):
		# A complete separation certificate may require no distance samples, so
		# nearest sampled gap stays +INF. NaN or other infinite fields reject.
		if k==4 and answer.stats[k]==INF:continue
		if not is_finite(answer.stats[k]):return invalid("native_contact_guard_stats")
	return {"valid":true,"reason":"","stats":answer.stats}
