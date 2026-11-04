extends "res://tests/test_blade_actual.gd"
class RecordingCutter extends RefCounted:
	var inner=load("res://scripts/membrane_cut.gd").new()
	var model
	var last_state:Dictionary
	var last_cut:Dictionary
	func slice_triangle(points,indices,a,b,c,max_vertices=4096,max_triangles=8192,material_partition=false)->Dictionary:
		last_state={}
		for key in ["positions","rest_positions","_previous","anchored","_removed","_outside","triangles","_triangle_area","surface_density","_material_rest","_material_indices","_material_ids"]:
			last_state[key]=model.get(key)
		var result:Dictionary=inner.slice_triangle(points,indices,a,b,c,max_vertices,max_triangles,material_partition)
		last_cut=result
		if not result.valid:
			DirAccess.make_dir_recursive_absolute("res://reports")
			var file:=FileAccess.open("res://reports/blade-cut-failure.bin",FileAccess.WRITE)
			if file:file.store_var({"points":points,"indices":indices,"patch":PackedVector3Array([a,b,c]),"reason":result.reason})
		return result
	func slice_triangle64(points,indices,a,b,c,max_vertices=4096,max_triangles=8192)->Dictionary:
		last_state={}
		for key in ["positions","rest_positions","_previous","anchored","_removed","_outside","triangles","_triangle_area","surface_density","_material_rest","_material_indices","_material_ids"]:
			last_state[key]=model.get(key)
		var result:Dictionary=inner.slice_triangle64(points,indices,a,b,c,max_vertices,max_triangles)
		last_cut=result
		if not result.valid:
			DirAccess.make_dir_recursive_absolute("res://reports")
			var file:=FileAccess.open("res://reports/blade-cut-failure.bin",FileAccess.WRITE)
			if file:file.store_var({"points":points,"indices":indices,"patch":PackedVector3Array([a,b,c]),"reason":result.reason})
		return result
func configure_capsule(_app)->bool:return true
func run()->void:
	var app=load("res://scripts/simulator.gd").new();root.add_child(app);app.set_physics_process(false);app.set_process(false);await process_frame
	app.start_practice();app.choose_tool("knife")
	if not configure_capsule(app):app.free();await process_frame;quit(1);return
	app.capsule._cutter=RecordingCutter.new()
	app.capsule._cutter.model=app.capsule
	for target in [Vector3(1.32,.80,0),Vector3(1.32,.65,0),Vector3(1.20,.65,0),Vector3(.90,.68,0),Vector3(0,.75,0)]:
		place(app,target)
		if failures:break
	var area:float=app.capsule.metrics().retained_area
	var central_vertex:=-1;var closest:=INF
	for vertex in range(app.capsule.rest_positions.size()):
		var point:Vector3=app.capsule.rest_positions[vertex];var radius_sq:float=float(point.x)*point.x+float(point.z)*point.z
		if radius_sq<closest:closest=radius_sq;central_vertex=vertex
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
	var central_detached:=false
	for piece in pieces:
		if central_vertex in piece.vertices:central_detached=true
	check(central_vertex>=0 and central_detached,"closed sharp-edge route detaches the intended central material, not just peripheral chips")
	check(absf(app.capsule.metrics().retained_area-area)<1e-9,"closed blade route preserves the entire membrane material")
	print("Closed blade result: ",failures," failures; components=",pieces.size(),"; failure=",app.capsule.native_failure)
	app.capsule._cutter.model=null
	app.free();await process_frame;quit(1 if failures else 0)
