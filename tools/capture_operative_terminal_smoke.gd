extends "res://tests/capture_operative_trajectory.gd"
func run()->void:
	var app=load("res://scripts/simulator.gd").new();root.add_child(app);app.set_physics_process(false);app.set_process(false);await process_frame
	app.start_practice();app.choose_tool("knife")
	if not configure_capsule(app):app.free();quit(1);return
	var before:PackedByteArray=var_to_bytes(app.capsule._embedded_state)
	load("res://capture_operative_terminal.gd").save(app,0,app.capsule.detached_components())
	check(var_to_bytes(app.capsule._embedded_state)==before,"terminal observation preserves owned state bytes")
	var saved:Dictionary=FileAccess.open("res://reports/operative-terminal.bin",FileAccess.READ).get_var()
	check(var_to_bytes(saved.state)==before,"binary checkpoint preserves all owned state bytes")
	var data:Dictionary=JSON.parse_string(FileAccess.get_file_as_string("res://reports/operative-terminal.json"))
	check(data.triangles.size()==app.capsule.triangles.size() and data.xyz.size()==app.capsule.positions.size()*3 and data.anchored.size()*3==data.xyz.size(),"terminal topology export has complete aligned arrays")
	app.free();await process_frame
	print("Terminal capture smoke: ",failures," failures");quit(1 if failures else 0)
