extends SceneTree
var failures: Array[String] = []
func check(ok: bool, message: String) -> void:
	if not ok: failures.append(message)
func _initialize() -> void:
	call_deferred("run")
func run() -> void:
	var source = load("res://scripts/surgical_world.gd")
	check(source != null and source.can_instantiate(), "World script must load and instantiate")
	if source == null or not source.can_instantiate():
		finish()
		return
	var world = source.new()
	root.add_child(world)
	world.build()
	check(world.normalized_to_world(Vector3(0.75, 0.25, -0.1)).is_equal_approx(Vector3(1.0, 0.7, -1.0)), "Eye coordinates map to correct world axes")
	check(world.world_to_normalized(Vector3(-1.0, 1.0, 1.0)).is_equal_approx(Vector3(0.25, 0.75, 0.2)), "World coordinates map to normalized surgical inputs")
	for part in ["Sclera", "Iris", "Pupil", "Cornea", "Capsule", "LensRegions", "CortexRegions", "IOL", "Instruments", "Room"]:
		check(world.find_child(part, true, false) != null, "Separate anatomy/room node: " + part)
	var pupil_mesh = world.find_child("Pupil",true,false).mesh
	var arr = pupil_mesh.surface_get_arrays(0)
	var tri = arr[Mesh.ARRAY_INDEX]
	var verts = arr[Mesh.ARRAY_VERTEX]
	check((verts[tri[4]]-verts[tri[3]]).cross(verts[tri[5]]-verts[tri[3]]).y<0, "Operative surfaces use top visible clockwise winding")
	var head = world.find_child("PatientHead",true,false)
	check(head.mesh.radius<0.7, "Room patient head uses human scale independent of magnified eye")
	for id in ["knife", "forceps", "cannula", "phaco", "ia", "injector", "manipulator"]:
		check(world.tools.has(id), "Distinct instrument: " + id)
	var regions = []
	for i in range(8): regions.append({"x": 0.5 + 0.16*cos(i*TAU/8.0), "y":0.5+0.16*sin(i*TAU/8.0), "opacity":1.0,"cortex":1.0})
	world.update_state({"phase":"PHACO", "eye":{"regions":regions}}, Vector3(0.7,0.3,-0.1), "phaco", true)
	check(world.tools["phaco"].position.is_equal_approx(Vector3(0.8,0.7,-0.8)), "Instrument origin follows normalized tip")
	check(world.lens_regions[0].visible, "Cloudy region initially visible")
	regions[0]["opacity"] = 0.0
	regions[0]["cortex"] = 0.0
	world.update_state({"phase":"CORTEX", "eye":{"regions":regions}}, Vector3(0.5,0.5,0), "ia", false)
	check(not world.lens_regions[0].visible, "Removed nuclear tissue disappears locally")
	check(world.lens_regions[1].visible, "Neighboring tissue remains")
	check(not world.cortex_regions[0].visible, "Removed cortex disappears locally")
	world.update_state({"phase":"IOL", "eye":{"iol_deployment":0.25,"iol_alignment":0.0,"opacity":0.0}}, Vector3(0.5,0.5,0), "injector", false)
	check(world.iol.visible, "Implant is shown during delivery")
	var folded_width: float = world.iol.scale.x
	world.update_state({"phase":"ALIGN", "eye":{"iol_deployment":1.0,"iol_alignment":1.0,"opacity":0.0}}, Vector3(0.5,0.5,0), "manipulator", false)
	check(world.iol.scale.x > folded_width, "Implant visibly unfolds")
	check(world.iol.position.distance_to(Vector3(0,0.835,0)) < 0.01, "Aligned implant centers in capsule")
	world.update_state({"phase":"HYDRO","tutorial":true,"eye":{}},Vector3(.68,.5,0),"cannula",false)
	check(world.target.get_child(0).position.is_equal_approx(Vector3(.72,.95,0)), "Hydro guide marks actual hydro contact target")
	world.update_state({"phase":"HYDRO","tutorial":false,"eye":{}},Vector3(.68,.5,0),"cannula",false)
	check(not world.target.visible, "Tutorial off hides operative guides")
	world.update_state({"phase":"PHACO","paused":true,"eye":{}},Vector3(.5,.5,0),"phaco",true)
	check(not world.tools["phaco"].visible, "Pause hides active instrument")
	world.update_state({"phase":"PHACO","alert":"movement","eye":{}},Vector3(.5,.5,0),"phaco",true)
	check(not world.tools["phaco"].visible, "Hazard hides active instrument")
	var path=[]
	for i in range(300): path.append([.5+.22*cos(i*TAU/299.0),.5+.22*sin(i*TAU/299.0),0])
	world.update_state({"phase":"HYDRO","eye":{"capsule_path":path}},Vector3(.5,.5,0),"cannula",false)
	check(world.capsule_trace.get_child(79).position.distance_to(Vector3(.88,.845,0))<.01, "Long capsule trace includes final point instead of truncating path")
	world.update_state({"phase":"CAPSULE","progress":0.5,"eye":{}},Vector3(.72,.5,0),"forceps",false)
	var membrane=world.find_child("CapsuleMembrane",true,false)
	check(membrane.visible and membrane.scale.x<1, "Capsule tracing opens actual membrane geometry")
	world.update_state({"phase":"HYDRO","eye":{}},Vector3(.68,.5,0),"cannula",false)
	check(not membrane.visible, "Completed capsulotomy removes central membrane")
	world.update_state({"phase":"PHACO","tick":100,"eye":{"opacity":1.0}},Vector3(.66,.5,0),"phaco",true)
	var fragments=world.find_child("AspirationFragments",true,false)
	check(fragments.visible and fragments.get_child_count()<=16, "Aspiration produces a bounded visual fragment pool")
	world.update_state({"phase":"PHACO","tick":100,"paused":true,"eye":{"opacity":1.0}},Vector3(.66,.5,0),"phaco",true)
	check(not fragments.visible, "Pause clears aspiration effect")
	world.update_state({"phase":"PHACO","reduced_motion":true,"eye":{"opacity":1.0}},Vector3(.66,.5,0),"phaco",true)
	check(not fragments.visible, "Reduced motion suppresses moving debris")
	var readonly={"phase":"PHACO","eye":{"opacity":0.5,"regions":regions}}
	var original=readonly.duplicate(true)
	world.update_state(readonly,Vector3(.66,.5,0),"phaco",true)
	check(readonly==original, "Renderer cannot mutate authoritative snapshot")
	world.set_room_view(true)
	check(world.room_camera.current and not world.microscope.current, "Room view activates room camera")
	check(not world.find_child("Eye",true,false).visible and not world.find_child("Instruments",true,false).visible, "Room view hides enlarged operative anatomy and instruments")
	check(world.find_child("Room",true,false).visible and world.find_child("RoomEyeProxy",true,false)!=null, "Room view includes patient with small eye proxy")
	world.update_state({"phase":"PHACO","tutorial":true,"eye":{}},Vector3(.5,.5,0),"phaco",true)
	check(not world.find_child("Instruments",true,false).visible and not world.target.visible, "Per-frame state updates preserve room visibility isolation")
	world.set_room_view(false)
	check(world.microscope.current, "Microscope view restores operative camera")
	check(not world.find_child("Room",true,false).visible and world.find_child("Eye",true,false).visible, "Microscope isolates enlarged operative anatomy from room furniture")
	world.free()
	finish()
func finish() -> void:
	if failures.is_empty():
		print("WORLD PASS: coordinates, layers, tools, local removal, IOL and cameras")
	else:
		for failure in failures: push_error(failure)
	quit(0 if failures.is_empty() else 1)
