extends "res://tests/capture_operative_trajectory.gd"
func run()->void:
	var app=load("res://scripts/simulator.gd").new();root.add_child(app);app.set_physics_process(false);app.set_process(false);await process_frame
	app.start_practice();app.choose_tool("knife")
	if not configure_capsule(app):app.free();quit(1);return
	var r:=.4;var y:float=app.geometry.bag_front(r);var prior:=Vector3(r,y,0)
	var next:=Vector3(r*cos(TAU/64.),y,r*sin(TAU/64.));var down:=Vector3.UP*.05
	var result:Dictionary=app.capsule.incise_patches([PackedVector3Array([prior-down,next-down,next+down]),PackedVector3Array([prior-down,next+down,prior+down])])
	check(result.valid and result.changed,"smoke performs a real retained incision through staged material instances")
	var before:PackedByteArray=var_to_bytes(app.capsule._embedded_state)
	load("res://capture_operative_terminal.gd").save(app,0,app.capsule.detached_components())
	check(var_to_bytes(app.capsule._embedded_state)==before,"terminal observation preserves owned state bytes")
	var saved:Dictionary=FileAccess.open("res://reports/operative-terminal.bin",FileAccess.READ).get_var()
	check(saved.blade_trace.size()==2,"both attempted blade patches survive staged-instance ownership and binary export")
	check(var_to_bytes(saved.state)==before,"binary checkpoint preserves all owned state bytes")
	var data:Dictionary=JSON.parse_string(FileAccess.get_file_as_string("res://reports/operative-terminal.json"))
	check(data.triangles.size()==app.capsule.triangles.size() and data.xyz.size()==app.capsule.positions.size()*3 and data.anchored.size()*3==data.xyz.size(),"terminal topology export has complete aligned arrays")
	app.free();await process_frame
	print("Terminal capture smoke: ",failures," failures");quit(1 if failures else 0)
