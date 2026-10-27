extends SceneTree
var failures:=0
class ObservedCapsule:
	extends "res://scripts/capsule_solver.gd"
	var received:Array=[]
	func step_tools(dt:float,tools:Array[Dictionary])->void:
		received=tools.duplicate(true); super.step_tools(dt,tools)
func check(ok:bool,message:String):
	if not ok: failures+=1; push_error(message)
func _initialize(): call_deferred("run")
func run():
	var app=load("res://scripts/simulator.gd").new(); root.add_child(app); app.set_physics_process(false)
	await process_frame
	for key in ["patient","side","equipment"]: app.prepare_check(key)
	app.begin_operation()
	# Isolate rigid motion in the real default iris geometry. Both requested
	# tip endpoints are in the pupil and clear of the posterior bag.
	app.hand_tools[0]="injector"; app.incision.opened[0]=true
	app._set_tip(0,Vector3(.4,.1,0)); app.previous_tips[0]=app.rigs[0].tip
	app._body_poses[0]={"tip":app.rigs[0].tip,"axis":app.rigs[0].axis,"grip":false}
	app.targets[0]=Vector3(.4,-.4,0); app.target_valid[0]=true
	var body_hit:=false
	for i in range(30):
		var old:Vector3=app.rigs[0].tip
		app._advance_motion(1./60.)
		check(app.rigs[0].tip.distance_to(old)<=.0251,"body response preserves ordinary input speed bound")
		check((app.rigs[0].tip-app.rigs[0].portal).cross(app.rigs[0].axis).length()<1e-6,"default rigid response stays on incision pivot")
		for c in app._contact_records[0]:
			if c.surface=="iris" and c.get("part","")=="shaft": body_hit=true
		app._body_poses[0]={"tip":app.rigs[0].tip,"axis":app.rigs[0].axis,"grip":false}
	check(body_hit and app.rigs[0].tip.y>-.35,"actual iris blocks shaft-only crossing while tip remains inside pupil")
	if DisplayServer.get_name()!="headless":
		app.room_view=false; app.update_geometry()
		await process_frame; await RenderingServer.frame_post_draw
		root.get_texture().get_image().save_png("res://reports/rigid-iris-contact.png")
	app.new_case("standard")
	check(app.last_contacts==[[],[]] and app._contact_records==[[],[]],"reset clears rigid body contact evidence")
	app.rigs[0].portal=Vector3(2,0,0); app.rigs[0].axis=Vector3.LEFT
	app._set_tip(0,Vector3.ZERO); app.previous_tips[0]=Vector3.ZERO
	app._body_poses[0]={"tip":Vector3.ZERO,"axis":Vector3.LEFT,"grip":true}
	app.hand_tools[0]="forceps"; app.incision.opened[0]=true
	app.anatomy.iris={"positions":PackedVector3Array([Vector3(.2,-.001,.043),Vector3(.201,.001,.043),Vector3(.2,.001,.044)]),"triangles":PackedInt32Array([0,1,2]),"revision":0}
	# Separate the small articulation fixture from the anatomical bag equator.
	app.anatomy.posterior={"positions":PackedVector3Array(),"triangles":PackedInt32Array(),"revision":0}
	app.case_active=true; app.practice=true; app.room_view=false
	var observed=ObservedCapsule.new(); observed.geometry=app.geometry; observed.reset()
	observed.tissue_boundary=app._flap_boundary; app.capsule=observed
	app._physics_process(1./60.)
	check(app._body_poses[0].grip and app.display.capture_frame().actions[0].grip,"blocked jaw opening preserves accepted grip in capsule history and rendering")
	check(not observed.received[0].grip,"released input cannot re-grasp tissue merely because opening is blocked")
	app.targets[0]=Vector3(0,.1,0); app.target_valid[0]=true
	for i in range(8): app._physics_process(1./60.)
	check(app.rigs[0].tip.y>.09,"rejected jaw opening cannot freeze a clear closed-jaw withdrawal")
	check(not app._body_poses[0].grip and not app.display.capture_frame().actions[0].grip,"opening commits after the accepted tool pose has clearance")
	app.rigs[0].set_insertion(-.2); app.previous_tips[0]=app.rigs[0].tip
	app._body_poses[0]={"tip":app.rigs[0].tip,"axis":app.rigs[0].axis,"grip":true}; app._resolved_grips[0]=true
	app.choose_tool("cannula"); app.choose_tool("forceps")
	check(not app._body_poses[0].grip and not app.display.capture_frame().actions[0].grip,"new exterior instrument cannot inherit removed tool jaw articulation")
	app.queue_free(); await process_frame
	print("Rigid body application: ",failures," failures"); quit(1 if failures else 0)
