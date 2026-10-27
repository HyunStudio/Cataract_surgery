extends SceneTree
var failures:=0
func check(ok:bool,message:String)->void:
	if not ok: failures+=1; push_error(message)
func _initialize()->void: call_deferred("run")
func run()->void:
	var app=load("res://scripts/simulator.gd").new(); root.add_child(app); app.set_physics_process(false)
	await process_frame; app.start_practice()
	app.choose_tool("phaco")
	app.set_machine("energy",1.); app.set_machine("suction",1.)
	app.handle_pedal(false,false,true); app.handle_pedal(true,false,true)
	for i in range(3): app._set_tip(0,Vector3(0,.68,0)); app._physics_process(1./60.)
	print("Blocked attempt: ",app.rigs[0].tip," contacts ",app.last_contacts," status ",app.status)
	check(app.rigs[0].tip.y>.82,"intact capsule blocks direct phaco entry in application")
	var damage:=0.
	for bond in app.lens.bonds: damage+=float(bond.damage)
	check(app.lens.metrics().outflow>app.lens.metrics().leak_outflow,"blocked tissue access still permits anterior fluid aspiration")
	check(damage==0.,"phaco energy cannot pass through an intact intervening capsule")
	app.release_controls(); app.choose_tool("knife"); app.grip_down=true
	for i in range(100):
		var angle:=TAU*i/99.
		app._set_tip(0,Vector3(.32*cos(angle),.81,.32*sin(angle))); app._physics_process(1./60.)
	print("Blade attempt: ",app.rigs[0].tip," contacts ",app.last_contacts," capcenter ",app.capsule.positions[0]," status ",app.status)
	check(app.capsule.metrics().broken_edges>0,"active local blade opens actual capsule")
	app.release_controls(); app.choose_tool("phaco")
	app._set_tip(0,Vector3(.32,.68,0)); app._physics_process(1./60.)
	check(app.rigs[0].tip.y<.75,"phaco can enter through the actual local opening")
	check(app.metrics.get("capsule_contacts",0.)>0.,"surface contact duration enters case metrics")
	app.queue_free(); await process_frame
	print("Anatomical application: ",failures," failures"); quit(1 if failures else 0)
