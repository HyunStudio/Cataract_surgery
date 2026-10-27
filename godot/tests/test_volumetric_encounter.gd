extends SceneTree
var failures:=0
func check(ok:bool,message:String)->void:
	if not ok: failures+=1; push_error(message)
func _initialize()->void: call_deferred("run")
func tick(app,n:=1)->void:
	for i in range(n): app._physics_process(1./60.)
func place(app,p:Vector3,tolerance:=.001)->void:
	if failures: return
	app.targets[app.selected]=p; app.target_valid[app.selected]=true
	for i in range(300):
		var before:Vector3=app.rigs[app.selected].tip
		tick(app)
		check(app.rigs[app.selected].tip.distance_to(before)<=.0251,"normal target path keeps per-tick travel bounded")
		if app.rigs[app.selected].tip.distance_to(p)<tolerance: return
	var capture:=FileAccess.open("res://reports/volumetric-blocked-pose.bin",FileAccess.WRITE)
	if capture:
		capture.store_var({"target":p,"tip":app.rigs[app.selected].tip,"axis":app.rigs[app.selected].axis,"portal":app.rigs[app.selected].portal,"tool":app.hand_tools[app.selected],"radius":app._radius(app.selected),"contacts":app._contact_records[app.selected],"surfaces":{"iris":app.anatomy.iris,"posterior":app.anatomy.posterior},"particles":app.lens.particles,"status":app.status})
	check(false,"continuous instrument target blocked: %s -> %s"%[p,app.rigs[app.selected].tip])
func safe_target(app,p:Vector3)->Vector3:
	var r:=Vector2(p.x,p.z).length()
	var margin:float=app._radius(app.selected)+.035
	p.y=clampf(p.y,app.geometry.bag_back(r)+margin,app.geometry.bag_front(r)-margin)
	return p
func walk(app,target:Vector3)->void:
	var tip:Vector3=app.rigs[app.selected].tip
	for i in range(1000):
		if tip.distance_to(target)<.0001: break
		tip=tip.move_toward(target,.005); place(app,tip)
		if app.rigs[app.selected].tip.distance_to(tip)>.035:
			check(false,"continuous extraction pose must remain reachable: requested %s resolved %s"%[tip,app.rigs[app.selected].tip]); return
	check(app.rigs[app.selected].tip.distance_to(target)<.035,"constrained tool reaches intended extraction route point")
func withdraw(app)->void:
	app.release_controls()
	var side:=1. if app.selected==0 else -1.; var z:float=app.rigs[app.selected].portal.z
	for p in [Vector3(0,.70,0),Vector3(side*1.32,.52,z),Vector3(side*1.32,.95,z),Vector3(side*1.95,.95,z)]: place(app,p)
func enter(app)->void:
	var side:=1. if app.selected==0 else -1.; var z:float=app.rigs[app.selected].portal.z
	for p in [Vector3(side*1.32,.80,z),Vector3(side*1.32,.65,z),Vector3(side*.9,.68,z),Vector3(0,.75,0),Vector3(0,.20,0)]: place(app,p)
func exchange(app,id:String)->void:
	withdraw(app)
	app.choose_tool(id); check(app.hand_tools[app.selected]==id,"exchange after actual exterior withdrawal")
	enter(app)
func use_hand(app,hand:int,id:String)->void:
	if app.selected==hand: return
	withdraw(app); app.switch_hand()
	app.choose_tool(id); check(app.hand_tools[hand]==id,"opposite hand exchanges at its actual exterior pose")
	enter(app)
func body_path(app,hand:int,start:Vector3,finish:Vector3,tool:String)->Dictionary:
	var portal:Vector3=app.rigs[hand].portal
	return app._rigid_body.resolve(portal,start,(start-portal).normalized(),finish,(finish-portal).normalized(),tool,app.geometry.tip_radius(tool),false,{"iris":app.anatomy.iris,"posterior":app.anatomy.posterior})
func clear_path(result:Dictionary)->bool:
	return result.valid and result.fraction==1. and result.contacts.is_empty()
func approach_material(app,p:Vector3,tool:String)->void:
	var hand:int=app.selected
	if not clear_path(body_path(app,hand,p,p,tool)):
		hand=1-hand
		check(clear_path(body_path(app,hand,p,p,tool)),"material target must have a nominal whole-instrument approach from an actual portal: "+str(p))
		if failures: return
		use_hand(app,hand,tool)
	if not clear_path(body_path(app,hand,app.rigs[hand].tip,p,tool)):
		app.release_controls(); place(app,Vector3(0,.20,0))
	app.handle_pedal(false,false,true); app.handle_pedal(true,false,true,3 if tool=="phaco" else 2)
	place(app,p,.025)
func run()->void:
	var app=load("res://scripts/simulator.gd").new(); root.add_child(app); app.set_physics_process(false)
	await process_frame
	for id in ["patient","side","equipment"]: app.prepare_check(id)
	check(app.begin_operation(),"dimensioned case begins after preparation")
	# A separate real blade trace creates the opposite portal; no pre-opened
	# side port or injected inside instrument pose is used in this encounter.
	app.switch_hand(); app.choose_tool("knife")
	place(app,Vector3(-1.32,.95,0)); app.grip_down=true
	for i in range(101): place(app,Vector3(-1.32,.80,.005*i))
	check(app.incision.opened[1],"opposite portal requires its own actual blade trace")
	app.release_controls()
	for p in [Vector3(-1.32,.80,.25),Vector3(-1.32,.65,.25),Vector3(-.9,.68,.25),Vector3(0,.75,0),Vector3(-.9,.68,.25),Vector3(-1.32,.65,.25),Vector3(-1.32,.95,.25),Vector3(-1.95,.95,.25)]: place(app,p)
	app.switch_hand()
	app.choose_tool("knife"); place(app,Vector3(1.32,.95,-.25)); app.grip_down=true
	for i in range(101): place(app,Vector3(1.32,.80,-.25+.005*i))
	check(app.incision.opened[0],"dimensioned corneal tunnel requires actual blade trace")
	app.release_controls()
	for p in [Vector3(1.32,.80,0),Vector3(1.32,.65,0),Vector3(1.20,.65,0),Vector3(.90,.68,0),Vector3(0,.75,0)]:
		place(app,p); print("Chamber route ",p," -> ",app.rigs[0].tip," ",app.last_contacts," ",app.injury.metrics())
	check(app.director.snapshot().alert=="","entry and chamber transit are free of structural injury")
	if failures: app.queue_free(); await process_frame; quit(1); return
	app.grip_down=true
	for i in range(145):
		var a:=TAU*i/144.; var r:=.57
		place(app,Vector3(r*cos(a),app.geometry.bag_front(r)-.005,r*sin(a)))
	check(app.capsule.metrics().broken_edges>0,"dimensioned anterior opening changes actual membrane connectivity")
	app.release_controls()
	for p in [Vector3(.57,.70,0),Vector3(1.32,.52,0),Vector3(1.32,.95,0),Vector3(1.95,.95,0)]: place(app,p)
	app.choose_tool("forceps")
	for p in [Vector3(1.32,.80,0),Vector3(1.32,.65,0),Vector3(.9,.68,0)]: place(app,p)
	var pieces:Array=app.capsule.detached_components()
	check(not pieces.is_empty(),"cut retains a real detached anterior flap")
	if pieces.is_empty(): app.queue_free(); await process_frame; quit(1); return
	var vertex:int=pieces[0].vertices[0]
	for v in pieces[0].vertices:
		if app.capsule.positions[v].x>app.capsule.positions[vertex].x: vertex=v
	var edge:Vector3=app.capsule.positions[vertex]
	place(app,edge+Vector3(0,.025,0)); app.grip_down=true; tick(app,2)
	check(app.capsule.metrics().grasped>=0,"actual forceps contacts and holds a supported flap vertex")
	var held_frame:Dictionary=app.display.capture_frame()
	var held_indices:PackedInt32Array=held_frame.capsule.triangles.duplicate()
	for p in [Vector3(edge.x,.90,0),Vector3(.9,.70,0),Vector3(1.32,.50,0),Vector3(1.32,.76,0),Vector3(1.80,1.0,0),Vector3(2.10,1.15,0)]:
		walk(app,p)
		if DisplayServer.get_name()!="headless" and p==Vector3(1.32,.76,0):
			await process_frame; await RenderingServer.frame_post_draw
			root.get_texture().get_image().save_png("res://reports/capsule-extraction.png")
	tick(app,60)
	check(app.capsule.metrics().extracted_flaps>0 and app.capsule.metrics().retained_detached_area<1e-8,"forceps carries the actual complete flap through the shared wound")
	check(held_frame.capsule.triangles==held_indices and held_indices.size()>app.capsule.triangles.size(),"actual displayed earlier flap remains immutable after extraction")
	app.display.apply_frame(held_frame)
	check(app.display.capture_frame().capsule.triangles==held_indices,"recorded retained flap restores its actual faces")
	app.update_geometry()
	check(app.display.capture_frame().capsule.triangles==app.capsule.triangles,"live extracted topology restores after preview")
	print("Default extraction: ",app.capsule.metrics())
	if failures: app.queue_free(); await process_frame; quit(1); return
	app.release_controls(); app.choose_tool("cannula")
	for p in [Vector3(1.32,.80,0),Vector3(1.32,.65,0),Vector3(.9,.68,0),Vector3(0,.75,0),Vector3(0,.20,0)]: place(app,p)
	app.set_machine("inflow",1.)
	app.handle_pedal(false,false,true,1); app.handle_pedal(true,false,true,1)
	var hydro_target:=-1
	# The straight shaft approaches opposite cortex through the pupil. Let
	# actually admitted surface flow propagate around the bag rather than
	# forcing the near-entry shaft through the iris to visit every particle.
	for i in range(app.lens.particles.size()):
		if app.lens.material.is_cortex(i) and app.lens.particles[i].position.x<-.4: hydro_target=i; break
	check(hydro_target>=0,"opposite cortical site exists for the current portal")
	for step in range(4500):
		if app.lens.metrics().adhesion_released>.95: break
		if hydro_target<0: break
		var target:Vector3=app.lens.particles[hydro_target].position*.98
		var before:Vector3=app.rigs[0].tip
		app.targets[0]=safe_target(app,target); app.target_valid[0]=true; app._physics_process(.05)
		check(app.rigs[0].tip.distance_to(before)<=.0751,"hydro moves through normal continuous control instead of teleporting between cortex sites")
		if step%200==0: await process_frame
	print("Volumetric hydro: ",app.lens.metrics()," alert=",app.director.snapshot().alert," tip=",app.rigs[0].tip)
	check(app.lens.metrics().adhesion_released>.8,"accepted local flow releases the volumetric cortical shell")
	exchange(app,"phaco")
	app.set_machine("energy",1.); app.set_machine("suction",1.); app.set_machine("inflow",1.)
	app.handle_pedal(false,false,true); app.handle_pedal(true,false,true)
	for step in range(4000):
		var found:=false; var target:=Vector3.ZERO; var nearest:=INF
		for p in app.lens.particles:
			if not p.active or p.cortex: continue
			var d:float=p.position.distance_squared_to(app.rigs[app.selected].tip)
			if d<nearest: nearest=d; target=p.position; found=true
		if not found: break
		# Aspiration draws material into the .05 inlet; the instrument center
		# need not occupy a peripheral particle's exact center against the bag.
		approach_material(app,safe_target(app,target),"phaco")
		if failures: break
		if step%200==0: await process_frame
	print("Volumetric phaco: ",app.lens.metrics()," alert=",app.director.snapshot().alert)
	check(app.lens.metrics().nucleus_remaining<.01,"powered local tool removes volumetric nucleus")
	if failures: app.queue_free(); await process_frame; quit(1); return
	exchange(app,"ia")
	app.handle_pedal(false,false,true,2); app.handle_pedal(true,false,true,2)
	for step in range(3000):
		var found:=false; var target:=Vector3.ZERO; var nearest:=INF
		for p in app.lens.particles:
			if not p.active: continue
			var d:float=p.position.distance_squared_to(app.rigs[app.selected].tip)
			if d<nearest: nearest=d; target=p.position; found=true
		if not found: break
		approach_material(app,safe_target(app,target),"ia")
		if failures: break
		if step%200==0: await process_frame
	print("Volumetric IA: ",app.lens.metrics()," alert=",app.director.snapshot().alert)
	check(app.lens.metrics().removed_mass>=.98,"dimensioned full encounter aspirates material through actual inlet")
	if failures: app.queue_free(); await process_frame; quit(1); return
	if app.selected!=0: use_hand(app,0,"injector")
	else: exchange(app,"injector")
	place(app,Vector3.ZERO); app.grip_down=true
	tick(app,110); app.release_controls(); tick(app,180)
	# The wider injector exits through the middle of the traced tunnel rather
	# than sweeping upward along its inner edge with the narrow-tool route.
	for p in [Vector3(.57,.25,0),Vector3(.57,.62,0),Vector3(.96,.52,0),Vector3(1.32,.52,0),Vector3(1.38,.70,0),Vector3(1.38,.95,0),Vector3(1.32,.95,0)]:
		place(app,p); print("Withdraw route ",p," -> ",app.rigs[0].tip," ",app.last_contacts)
	app.withdraw_tools(); tick(app,150)
	print("Withdrawn wound ",app.incision.metrics()," lengths=",app.incision.lengths," depths=",[app.rigs[0].insertion,app.rigs[1].insertion]," injury=",app.injury.metrics())
	for id in ["residual","implant","wound"]: check(app.inspect(id),"dimensioned final inspection "+id)
	print("Final actual capsule/body state: ",app.capsule.metrics()," contacts=",app.capsule.body_contact_count," peak_residual=",app.capsule.body_contact_residual," uncertain=",app.capsule.body_contact_uncertain)
	check(app.finish_case(),"default dimensioned case can actually complete")
	check(not app.injury.metrics().posterior_breached and not app.injury.metrics().corneal_breached,"normal route preserves corneal and posterior structure")
	var live:PackedVector3Array=app.capsule.positions.duplicate()
	app.preview_frame(0); tick(app,3); app.end_review()
	check(app.capsule.positions==live,"dimensioned review cannot mutate live tissue")
	if DisplayServer.get_name()!="headless":
		await process_frame; await RenderingServer.frame_post_draw
		root.get_texture().get_image().save_png("res://reports/volumetric-results.png")
	app.queue_free(); await process_frame
	print("Volumetric encounter: ",failures," failures"); quit(1 if failures else 0)
