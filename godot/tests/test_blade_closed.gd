extends "res://tests/test_blade_actual.gd"
class RecordingCutter extends RefCounted:
	var inner=load("res://scripts/membrane_cut.gd").new()
	var model
	var last_state:Dictionary
	var last_cut:Dictionary
	func slice_triangle(points,indices,a,b,c)->Dictionary:
		last_state={}
		for key in ["positions","rest_positions","_previous","anchored","_removed","_outside","triangles","_triangle_area","surface_density"]:
			last_state[key]=model.get(key)
		var result:Dictionary=inner.slice_triangle(points,indices,a,b,c)
		last_cut=result
		if not result.valid:
			DirAccess.make_dir_recursive_absolute("res://reports")
			var file:=FileAccess.open("res://reports/blade-cut-failure.bin",FileAccess.WRITE)
			if file:file.store_var({"points":points,"indices":indices,"patch":PackedVector3Array([a,b,c]),"reason":result.reason})
		return result
func run()->void:
	var app=load("res://scripts/simulator.gd").new();root.add_child(app);app.set_physics_process(false);app.set_process(false);await process_frame
	app.start_practice();app.choose_tool("knife")
	app.capsule._cutter=RecordingCutter.new()
	app.capsule._cutter.model=app.capsule
	for target in [Vector3(1.32,.80,0),Vector3(1.32,.65,0),Vector3(1.20,.65,0),Vector3(.90,.68,0),Vector3(0,.75,0)]:
		place(app,target)
		if failures:break
	var area:float=app.capsule.metrics().retained_area
	app.grip_down=true
	for i in range(145):
		if failures:break
		var angle:=TAU*i/144.;var radius:=.57
		place(app,Vector3(radius*cos(angle),app.geometry.bag_front(radius)-.005,radius*sin(angle)))
		if i%12==0:print("Closed blade progress ",i," ",JSON.stringify(app.capsule.metrics(),"",true,true))
	var pieces:Array=app.capsule.detached_components()
	if failures:
		DirAccess.make_dir_recursive_absolute("res://reports")
		var file:=FileAccess.open("res://reports/blade-transfer-failure.bin",FileAccess.WRITE)
		if file:file.store_var({"state":app.capsule._cutter.last_state,"cut":app.capsule._cutter.last_cut})
	check(not pieces.is_empty(),"continuous closed sharp-edge route retains a genuinely detached anterior flap")
	check(absf(app.capsule.metrics().retained_area-area)<1e-9,"closed blade route preserves the entire membrane material")
	print("Closed blade result: ",failures," failures; components=",pieces.size(),"; failure=",app.capsule.native_failure)
	app.capsule._cutter.model=null
	app.free();await process_frame;quit(1 if failures else 0)
