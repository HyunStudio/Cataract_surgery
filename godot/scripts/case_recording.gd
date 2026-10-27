extends RefCounted
## Compact visual snapshots, independent of the authoritative numerical state.
const MAX_FRAMES := 900
const INTERVAL := 2.0
var frames: Array[Dictionary] = []
var base: Dictionary = {}

func reset() -> void:
	frames.clear(); base={}

func record(time: float, source: Dictionary, force := false) -> void:
	if frames.size()>=MAX_FRAMES or not is_finite(time) or time<0 or source.is_empty(): return
	if not force and not frames.is_empty() and time-float(frames[-1].time)<INTERVAL: return
	if base.is_empty(): base=source.duplicate(true)
	var lens_positions := PackedVector3Array()
	var lens_active := PackedByteArray()
	var adhesion:=PackedFloat64Array()
	var bonds := PackedByteArray()
	var cap_edges := PackedByteArray()
	for p in source.lens.particles:
		lens_positions.append(p.position); lens_active.append(int(p.active)); adhesion.append(float(p.get("adhesion",0.)))
	for edge in source.lens.bonds: bonds.append(int(edge.active))
	for edge in source.capsule.edges: cap_edges.append(int(edge.active))
	frames.append({"time":time,"capsule_positions":source.capsule.positions.duplicate(),"capsule_triangles":source.capsule.triangles.duplicate(),"capsule_edges":cap_edges,"lens_positions":lens_positions,"lens_adhesion":adhesion,"lens_active":lens_active,"lens_bonds":bonds,"iol_positions":source.iol.positions.duplicate(),"iol_metrics":source.iol.metrics.duplicate(true),"rigs":source.rigs.duplicate(true),"hand_tools":source.hand_tools.duplicate(),"selected":source.selected,"actions":source.actions.duplicate(true),"options":source.options.duplicate(true)})

func frame_at(index: int) -> Dictionary:
	if index<0 or index>=frames.size(): return {}
	var compact: Dictionary = frames[index]
	var result := base.duplicate(true)
	result.capsule.positions=compact.capsule_positions.duplicate()
	result.capsule.triangles=compact.capsule_triangles.duplicate()
	for i in range(result.capsule.edges.size()): result.capsule.edges[i].active=bool(compact.capsule_edges[i])
	for i in range(result.lens.particles.size()):
		result.lens.particles[i].position=compact.lens_positions[i]
		result.lens.particles[i].active=bool(compact.lens_active[i])
		if compact.has("lens_adhesion"): result.lens.particles[i]["adhesion"]=compact.lens_adhesion[i]
	for i in range(result.lens.bonds.size()): result.lens.bonds[i].active=bool(compact.lens_bonds[i])
	result.iol.positions=compact.iol_positions.duplicate()
	result.iol.metrics=compact.iol_metrics.duplicate(true)
	for key in ["rigs","hand_tools","selected","actions","options"]:
		result[key]=compact[key].duplicate(true) if compact[key] is Array or compact[key] is Dictionary else compact[key]
	result.options.room=false
	return result

func export_json(report: Dictionary) -> String:
	return JSON.stringify(_numeric({"version":1,"kind":"visual_case_recording","report":report,"base":base,"frames":frames}))

func _numeric(value: Variant) -> Variant:
	if value is Vector3: return [value.x,value.y,value.z]
	if value is Dictionary:
		var out := {}
		for key in value: out[str(key)]=_numeric(value[key])
		return out
	if value is Array or value is PackedVector3Array or value is PackedByteArray or value is PackedInt32Array or value is PackedFloat64Array:
		var out: Array=[]
		for item in value: out.append(_numeric(item))
		return out
	return value
