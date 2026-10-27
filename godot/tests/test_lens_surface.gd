extends SceneTree
var failures:Array[String]=[]
func check(ok:bool,message:String)->void:
	if not ok: failures.append(message)
func _initialize()->void: call_deferred("run")
func run()->void:
	var surface_script=load("res://scripts/lens_surface.gd")
	check(surface_script!=null and surface_script.can_instantiate(),"Continuous lens surface implementation loads")
	if surface_script==null or not surface_script.can_instantiate(): finish(); return
	var solver=load("res://scripts/lens_fluid_solver.gd").new()
	var surface=surface_script.new()
	var original=solver.particles.duplicate(true)
	var bonds_before=solver.bonds.duplicate(true)
	var mesh:ArrayMesh=surface.update_from_solver(solver)
	check(mesh.get_surface_count()==1,"Intact particles form a continuous lens surface")
	var initial_arrays=mesh.surface_get_arrays(0)
	check(initial_arrays[Mesh.ARRAY_COLOR]!=null and initial_arrays[Mesh.ARRAY_COLOR].size()>100,"surface carries physical nuclear/cortical material identity")
	var initial_vertices:PackedVector3Array=initial_arrays[Mesh.ARRAY_VERTEX].duplicate()
	var initial_indices:PackedInt32Array=initial_arrays[Mesh.ARRAY_INDEX].duplicate()
	check(initial_indices.size()>500,"Indexed smooth caps and side strips replace point-cloud balls")
	check(solver.particles==original and solver.bonds==bonds_before,"Surface construction cannot alter numerical tissue")
	var changed:Vector3=solver.particles[75].position+Vector3(.02,.04,0)
	solver.particles[75].position=changed
	mesh=surface.update_from_solver(solver)
	var moved_vertices:PackedVector3Array=mesh.surface_get_arrays(0)[Mesh.ARRAY_VERTEX]
	check(moved_vertices[75].is_equal_approx(changed),"Actual source particle displacement is represented exactly")
	check(moved_vertices!=initial_vertices,"Deformation updates the smooth display vertices")
	check(mesh.surface_get_arrays(0)[Mesh.ARRAY_INDEX].size()==initial_indices.size(),"Deformation alone cannot globally remove active material")
	solver.reset()
	solver.particles[75].active=false
	mesh=surface.update_from_solver(solver)
	var removed_arrays=mesh.surface_get_arrays(0)
	check(removed_arrays[Mesh.ARRAY_INDEX].size()<initial_indices.size(),"Inactive cap particle opens only its local faces")
	check(not 75 in surface.visible_source_triangles,"Inactive source cannot support phantom surface faces")
	check(removed_arrays[Mesh.ARRAY_INDEX].size()>initial_indices.size()*.75,"One removed particle preserves distant tissue")
	solver.reset()
	mesh=surface.update_from_solver(solver)
	var selected_edge:Dictionary={}
	for bond in solver.bonds:
		if (bond.a==74 and bond.b==75) or (bond.a==75 and bond.b==74): selected_edge=bond; break
	check(not selected_edge.is_empty(),"Fixture selects an actual physical cap connection")
	selected_edge.active=false
	mesh=surface.update_from_solver(solver)
	check(mesh.surface_get_arrays(0)[Mesh.ARRAY_INDEX].size()<initial_indices.size(),"Broken physical connection opens supported display faces")
	check(solver.metrics().remaining_mass>.999,"Rendering broken connections does not erase active mass")
	for bond in solver.bonds:
		if bond.a==75 or bond.b==75: bond.active=false
	mesh=surface.update_from_solver(solver)
	check(surface.detached_positions.has(solver.particles[75].position),"Detached active particle position is exposed for actual fragment rendering")
	solver.reset()
	mesh=surface.update_from_solver(solver)
	var restored=mesh.surface_get_arrays(0)
	check(restored[Mesh.ARRAY_VERTEX]==initial_vertices and restored[Mesh.ARRAY_INDEX]==initial_indices,"Reset regenerates the same continuous topology and positions")
	for normal in restored[Mesh.ARRAY_NORMAL]: check(normal.is_finite() and normal.length()>.99,"Smooth shading normals are finite and normalized")
	finish()
func finish()->void:
	for message in failures: push_error(message)
	print("LENS SURFACE: ","PASS" if failures.is_empty() else "FAIL (%d)"%failures.size())
	quit(0 if failures.is_empty() else 1)
