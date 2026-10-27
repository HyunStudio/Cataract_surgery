extends SceneTree
var failures := 0
func check(ok: bool, message: String) -> void:
	if not ok: failures+=1; push_error(message)
func _initialize() -> void:
	var source = load("res://scripts/case_recording.gd")
	if source==null:
		push_error("case recording missing"); quit(1); return
	var rec = source.new()
	var frame := {"capsule":{"positions":PackedVector3Array([Vector3.ZERO]),"triangles":PackedInt32Array(),"edges":[]},"lens":{"particles":[{"position":Vector3.ONE,"active":true}],"bonds":[]},"iol":{"positions":PackedVector3Array(),"optic_count":0,"metrics":{}},"rigs":[],"hand_tools":[],"selected":0,"actions":[],"options":{}}
	rec.record(0.,frame,true)
	frame.capsule.positions[0]=Vector3(1,2,3)
	rec.record(2.,frame,true)
	var recalled: Dictionary = rec.frame_at(0)
	check(recalled.capsule.positions[0]==Vector3.ZERO,"review preserves earlier topology state")
	recalled.capsule.positions[0]=Vector3(9,9,9)
	check(rec.frame_at(0).capsule.positions[0]==Vector3.ZERO,"review cannot mutate recording")
	check(rec.frame_at(1).capsule.positions[0]==Vector3(1,2,3),"recording preserves actual moved state")
	var exported = JSON.parse_string(rec.export_json({"ending":"completed"}))
	check(exported is Dictionary and exported.frames.size()==2,"report is valid bounded JSON")
	check(exported.frames[1].capsule_positions[0]==[1.,2.,3.],"vector data exports as numeric arrays")
	print("Case recording: ",failures," failures")
	quit(1 if failures else 0)
