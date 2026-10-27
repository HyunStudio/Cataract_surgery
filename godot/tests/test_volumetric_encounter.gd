extends SceneTree
var failures:=0
func check(ok:bool,message:String)->void:
	if not ok: failures+=1; push_error(message)
func _initialize()->void: call_deferred("run")
func tick(app,n:=1)->void:
	for i in range(n): app._physics_process(1./60.)
func place(app,p:Vector3)->void:
	app._set_tip(app.selected,p); tick(app)
func safe_target(app,p:Vector3)->Vector3:
	var r:=Vector2(p.x,p.z).length()
	var margin:float=app._radius(app.selected)+.035
	p.y=clampf(p.y,app.geometry.bag_back(r)+margin,app.geometry.bag_front(r)-margin)
	return p
func run()->void:
	var app=load("res://scripts/simulator.gd").new(); root.add_child(app); app.set_physics_process(false)
	await process_frame
	for id in ["patient","side","equipment"]: app.prepare_check(id)
	check(app.begin_operation(),"dimensioned case begins after preparation")
	app.choose_tool("knife"); app.grip_down=true
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
	app.release_controls(); place(app,Vector3(.57,.28,0))
	app.choose_tool("cannula"); app.set_machine("inflow",1.)
	app.handle_pedal(false,false,true,1); app.handle_pedal(true,false,true,1)
	for step in range(4500):
		var attached:=-1.; var target:=Vector3.ZERO
		for i in range(app.lens.particles.size()):
			if app.lens.material.is_cortex(i) and app.lens.material.adhesion[i]>attached:
				attached=app.lens.material.adhesion[i]; target=app.lens.particles[i].position*.98
		if attached<.1: break
		app._set_tip(0,safe_target(app,target)); app._physics_process(.05)
		if step%200==0: await process_frame
	print("Volumetric hydro: ",app.lens.metrics()," alert=",app.director.snapshot().alert," tip=",app.rigs[0].tip)
	check(app.lens.metrics().adhesion_released>.8,"accepted local flow releases the volumetric cortical shell")
	app.release_controls(); app.choose_tool("phaco")
	app.set_machine("energy",1.); app.set_machine("suction",1.); app.set_machine("inflow",1.)
	app.handle_pedal(false,false,true); app.handle_pedal(true,false,true)
	for step in range(4000):
		var found:=false; var target:=Vector3.ZERO; var nearest:=INF
		for p in app.lens.particles:
			if not p.active or p.cortex: continue
			var d:float=p.position.distance_squared_to(app.rigs[0].tip)
			if d<nearest: nearest=d; target=p.position; found=true
		if not found: break
		place(app,safe_target(app,target))
		if step%200==0: await process_frame
	print("Volumetric phaco: ",app.lens.metrics()," alert=",app.director.snapshot().alert)
	check(app.lens.metrics().nucleus_remaining<.01,"powered local tool removes volumetric nucleus")
	app.release_controls(); app.choose_tool("ia")
	app.handle_pedal(false,false,true,2); app.handle_pedal(true,false,true,2)
	for step in range(3000):
		var found:=false; var target:=Vector3.ZERO; var nearest:=INF
		for p in app.lens.particles:
			if not p.active: continue
			var d:float=p.position.distance_squared_to(app.rigs[0].tip)
			if d<nearest: nearest=d; target=p.position; found=true
		if not found: break
		place(app,safe_target(app,target))
		if step%200==0: await process_frame
	print("Volumetric IA: ",app.lens.metrics()," alert=",app.director.snapshot().alert)
	check(app.lens.metrics().removed_mass>=.98,"dimensioned full encounter aspirates material through actual inlet")
	app.release_controls(); app.choose_tool("injector"); place(app,Vector3.ZERO); app.grip_down=true
	tick(app,110); app.release_controls(); tick(app,180)
	for p in [Vector3(.57,.25,0),Vector3(.57,.62,0),Vector3(.96,.52,0),Vector3(1.32,.52,0),Vector3(1.32,.95,0)]:
		place(app,p); print("Withdraw route ",p," -> ",app.rigs[0].tip," ",app.last_contacts)
	app.withdraw_tools(); tick(app,150)
	print("Withdrawn wound ",app.incision.metrics()," lengths=",app.incision.lengths," depths=",[app.rigs[0].insertion,app.rigs[1].insertion]," injury=",app.injury.metrics())
	for id in ["residual","implant","wound"]: check(app.inspect(id),"dimensioned final inspection "+id)
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
