extends SceneTree
var failures:=0
func check(ok:bool,message:String)->void:
	if not ok: failures+=1; push_error(message)
func _initialize()->void: call_deferred("run")
func run()->void:
	var app=load("res://scripts/simulator.gd").new()
	root.add_child(app); app.set_physics_process(false); await process_frame
	app.start_practice()
	var entry_target:=Vector3(1.32,.95,-.25)
	app.targets[0]=entry_target; app.target_valid[0]=true
	for i in range(100):
		var prior:Vector3=app.rigs[0].tip
		app._physics_process(1./60.)
		check(app.rigs[0].tip.distance_to(prior)<.0251,"default pointer entry keeps actual per-tick travel bounded")
		if app.rigs[0].tip.distance_to(entry_target)<.001: break
	check(app.rigs[0].tip.distance_to(entry_target)<.001 and app.rigs[0].insertion>0.,"default pointer enters through pivot and reaches oblique interior target")
	app.release_controls()
	for target in [Vector3(1.32,.8,0),Vector3(1.32,.65,0),Vector3(.9,.68,0),Vector3(0,.75,0)]:
		app._set_tip(0,target); app._physics_process(1./60.)
	var initial:PackedVector3Array=app.capsule.positions.duplicate()
	var contacts:=0; var uncertain:=0; var elapsed:=Time.get_ticks_msec()
	for i in range(25):
		app._set_tip(0,Vector3(0,.75-.01*i,0)); app._physics_process(1./60.)
		contacts+=app.capsule.body_contact_count; uncertain+=app.capsule.body_contact_uncertain
	check(contacts>0 and app.capsule.positions!=initial,"default app produces actual distributed tool-body contact and membrane deformation")
	check(app.rigs[0].tip.y<.54,"anterior response owns the tip instead of duplicate rigid blocking")
	check(app.capsule.metrics().finite and app.director.snapshot().alert=="","gentle central press remains finite without structural injury alert")
	print("Body press contacts=",contacts," uncertain=",uncertain," elapsed_ms=",Time.get_ticks_msec()-elapsed)
	if DisplayServer.get_name()!="headless":
		await process_frame; await RenderingServer.frame_post_draw
		root.get_texture().get_image().save_png("res://reports/body-contact.png")
	app.new_case("standard")
	check(app.capsule.body_contact_count==0 and app._body_poses[0].tip==app.rigs[0].tip,"new case resets body metrics and prior pose")
	app.queue_free(); await process_frame
	print("Body application: ",failures," failures"); quit(1 if failures else 0)
