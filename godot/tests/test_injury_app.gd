extends SceneTree
var failures:=0
func check(ok:bool,message:String)->void:
	if not ok: failures+=1; push_error(message)
func _initialize()->void: call_deferred("run")
func begin(app)->void:
	app.new_case("standard")
	for key in ["patient","side","equipment"]: app.prepare_check(key)
	app.begin_operation(); app.choose_tool("knife"); app.grip_down=true
	for i in range(41):
		app._set_tip(0,Vector3(1.32,.84,-.1+.005*i)); app._physics_process(1./60.)
	app.release_controls()
	for p in [Vector3(1.32,.84,0),Vector3(1.22,.847,0),Vector3(1.1,.864,0),Vector3(.9,.89,0),Vector3(0,.9,0)]:
		app._set_tip(0,p); app._physics_process(1./60.)
	app.grip_down=true
	for i in range(100):
		var a:=TAU*i/99.
		app._set_tip(0,Vector3(.32*cos(a),.81,.32*sin(a))); app._physics_process(1./60.)
func run()->void:
	var app=load("res://scripts/simulator.gd").new(); root.add_child(app); app.set_physics_process(false)
	await process_frame; begin(app)
	check(not app.injury.metrics().posterior_breached and not app.injury.metrics().corneal_breached,"normal entry and anterior cutting preserve posterior surface")
	app.update_geometry(); app.recording.record(app.clock,app.display.capture_frame(),true)
	var clean_frame:int=app.recording.frames.size()-1
	app._set_tip(0,Vector3(.32,.40,0)); app._physics_process(1./60.)
	check(app.injury.metrics().posterior_breached,"wrong-depth active blade makes actual local posterior puncture")
	check(app.director.snapshot().alert=="tissue_injury" and not app.grip_down and not app.pedal_down,"measured injury stops actions and requests assessment")
	check(app.lens.metrics().rupture_outflow>0.,"actual puncture couples posterior compartment flow immediately")
	app.recording.record(app.clock,app.display.capture_frame(),true)
	var harmed_frame:int=app.recording.frames.size()-1
	var data:Dictionary=app.injury.surfaces.posterior
	var posterior=app.display.get_node("NumericalEye/ComputedPosteriorCapsule")
	check(posterior.mesh.surface_get_arrays(0)[Mesh.ARRAY_INDEX]==data.triangles,"display uses actual locally damaged posterior topology")
	if DisplayServer.get_name()!="headless":
		await process_frame; await RenderingServer.frame_post_draw
		root.get_texture().get_image().save_png("res://reports/injury-contact.png")
	var live_ids:PackedInt32Array=data.triangles.duplicate()
	app.preview_frame(clean_frame)
	check(app.injury.surfaces.posterior.triangles==live_ids,"pre-injury review cannot heal authoritative tissue")
	check(posterior.mesh.surface_get_arrays(0)[Mesh.ARRAY_INDEX]!=live_ids,"pre-injury review restores earlier displayed geometry")
	app.preview_frame(harmed_frame)
	check(posterior.mesh.surface_get_arrays(0)[Mesh.ARRAY_INDEX]==live_ids,"post-injury review restores sampled damaged geometry")
	app.end_review(); app.acknowledge()
	check(not app.finish_case(),"acknowledged puncture cannot normal-complete")
	app.abort_case("posterior_damage_test")
	check(app.director.snapshot().ending=="safe_stop","intentional stop preserves adverse case record")
	if DisplayServer.get_name()!="headless":
		await process_frame; await RenderingServer.frame_post_draw
		root.get_texture().get_image().save_png("res://reports/injury-debrief.png")
	begin(app); app.release_controls(); app.choose_tool("phaco")
	app.set_machine("energy",1.); app.handle_pedal(false,false,true); app.handle_pedal(true,false,true)
	app._set_tip(0,Vector3(.32,.40,0)); app._physics_process(1./60.)
	for i in range(40): app._physics_process(1./60.)
	check(app.injury.metrics().posterior_breached,"sustained powered contact injures tissue even without new mouse motion")
	begin(app); app.release_controls(); app.choose_tool("cannula")
	app._set_tip(0,Vector3(.32,.40,0)); app._physics_process(1./60.)
	app.choose_tool("phaco"); app.set_machine("energy",1.)
	app.handle_pedal(false,false,true); app.handle_pedal(true,false,true)
	for i in range(40): app._physics_process(1./60.)
	check(app.injury.metrics().posterior_breached,"stationary powered contact after a tool switch is found from current geometry")
	app.start_practice()
	app.release_controls(); app.choose_tool("phaco")
	app._set_tip(0,Vector3(1.32,.84,0)); app._physics_process(1./60.)
	app.set_machine("energy",1.); app.handle_pedal(false,false,true); app.handle_pedal(true,false,true)
	for i in range(120): app._physics_process(1./60.)
	check(not app.injury.metrics().corneal_breached,"stationary power inside an open entry cannot injure excluded corneal geometry")
	app.new_case("standard")
	check(not app.injury.metrics().posterior_breached and app.lens.rupture_leak==0.,"new case restores mesh and clears rupture conductance")
	app.queue_free(); await process_frame
	print("Injury application: ",failures," failures"); quit(1 if failures else 0)
