extends SceneTree
var failures:Array[String]=[]
func check(ok:bool,message:String)->void:
	if not ok: failures.append(message)
func _initialize()->void: call_deferred("run")
func run()->void:
	var source=load("res://scripts/surgical_display.gd")
	check(source!=null and source.can_instantiate(),"Surgical display module loads")
	if source==null or not source.can_instantiate(): finish(); return
	var display=source.new()
	root.add_child(display)
	display.build()
	var capsule=load("res://scripts/capsule_solver.gd").new()
	var lens=load("res://scripts/lens_fluid_solver.gd").new()
	var iol=load("res://scripts/iol_dynamics.gd").new()
	var rigs=[load("res://scripts/instrument_rig.gd").new(),load("res://scripts/instrument_rig.gd").new()]
	rigs[0].portal=Vector3(-1.44,.86,0)
	rigs[0].axis=Vector3.RIGHT
	var before_particles=lens.particles.duplicate(true)
	var before_capsule=capsule.positions.duplicate()
	var before_iol=iol.positions.duplicate()
	var actions=[{"grip":true,"pedal":0},{"grip":false,"pedal":2}]
	display.apply(capsule,lens,iol,rigs,["forceps","phaco"],1,actions,{"room":false,"wireframe":true,"pupil_radius":.74,"wounds":[[Vector3(1,.86,0),Vector3(1.3,.86,0)]]})
	check(lens.particles==before_particles and capsule.positions==before_capsule and iol.positions==before_iol,"Applying display state never mutates authoritative solvers")
	check(display.membrane.mesh.surface_get_arrays(0)[Mesh.ARRAY_VERTEX]==capsule.positions,"Membrane mesh follows actual numerical positions")
	check(display.lens_display.mesh.get_surface_count()>0,"Smooth continuous lens mesh is integrated")
	check(display.has_node("NumericalEye/ComputedCornea") and display.has_node("NumericalEye/ComputedPosteriorCapsule"),"shared anatomical surfaces are rendered")
	check(not display.iol_display.visible,"Undelivered IOL cannot appear in eye")
	for hand in range(2):
		var id="forceps" if hand==0 else "phaco"
		var model=display.tool_models[hand][id]
		check(model.visible and model.position.is_equal_approx(rigs[hand].tip),"Each hand preserves its actual tool tip")
		var shaft=(model.basis*Vector3(1.55,.52,.20).normalized()).normalized()
		check(shaft.dot(-rigs[hand].axis)>.999,"Instrument shaft points back along constrained portal axis")
	var frame=display.capture_frame()
	check(frame.capsule.positions==capsule.positions and frame.lens.particles==lens.particles,"Visual frame includes numerical tissue state")
	frame.lens.particles[0].position+=Vector3(0,.2,0)
	check(lens.particles==before_particles,"Captured frames do not alias live numerical objects")
	display.apply_frame(frame)
	check(lens.particles==before_particles and capsule.positions==before_capsule,"Rendering a captured frame cannot advance or overwrite live solvers")
	for i in range(150): iol.step(1.0/60.0,Vector3(0,.72,0),true,Vector3(2,0,0),false)
	display.apply(capsule,lens,iol,rigs,["forceps","phaco"],1,actions,{"room":false})
	check(display.iol_display.visible,"Actual delivered IOL becomes visible")
	var optic=display.iol_display.find_child("Optic",true,false)
	var optic_positions=optic.mesh.surface_get_arrays(0)[Mesh.ARRAY_VERTEX]
	check(optic_positions[1].is_equal_approx(iol.positions[0]),"IOL optic follows actual dynamics points")
	display.apply(capsule,lens,iol,rigs,["forceps","phaco"],1,actions,{"room":true})
	check(display.world.room_camera.current and not display.membrane.is_visible_in_tree(),"Room mode isolates physical eye geometry")
	check(not display.tool_models[0]["forceps"].is_visible_in_tree(),"Room mode hides enlarged bimanual tools")
	var node_count=get_node_count()
	var material_id=display.membrane.material_override.get_instance_id()
	for i in range(3): display.apply(capsule,lens,iol,rigs,["forceps","phaco"],1,actions,{"room":false})
	check(get_node_count()==node_count and display.membrane.material_override.get_instance_id()==material_id,"Frame updates reuse scene nodes and materials")
	var captured_before_move=display.capture_frame()
	capsule.positions[1]+=Vector3(0,.025,0)
	check(display.capture_frame().capsule.positions==captured_before_move.capsule.positions,"Visual capture remains the last applied state after live solver changes")
	display.apply(capsule,lens,iol,rigs,["forceps","phaco"],1,actions,{"room":false})
	check(display.membrane.mesh.surface_get_arrays(0)[Mesh.ARRAY_VERTEX][1].is_equal_approx(capsule.positions[1]),"Geometry cache invalidates on actual membrane deformation")
	for x in [.2,-.3]:
		var damage=load("res://scripts/tissue_injury.gd").new()
		var data:Dictionary=damage.surfaces.posterior
		var query=load("res://scripts/surface_contact.gd").new()
		var hit:Dictionary=query.sweep(Vector3(x,.7,0),Vector3(x,.4,0),.01,data.positions,data.triangles)
		damage.step(.02,[{"surface":"posterior","point":hit.surface_point,"triangle":hit.triangle,"revision":0,"load":.03,"energy":0.,"cutting":true,"tool":"knife"}])
		display.apply(capsule,lens,iol,rigs,["forceps","phaco"],1,actions,{"room":false,"anatomy":{"posterior":damage.surfaces.posterior}})
		var posterior=display.get_node("NumericalEye/ComputedPosteriorCapsule")
		check(posterior.mesh.surface_get_arrays(0)[Mesh.ARRAY_VERTEX]==damage.surfaces.posterior.positions,"same revision from another recorded case still uses its own geometry")
	display.free()
	finish()
func finish()->void:
	for message in failures: push_error(message)
	print("SURGICAL DISPLAY: ","PASS" if failures.is_empty() else "FAIL (%d)"%failures.size())
	quit(0 if failures.is_empty() else 1)

