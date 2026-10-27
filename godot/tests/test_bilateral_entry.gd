extends SceneTree
var failures:=0
func check(ok:bool,message:String):
	if not ok: failures+=1; push_error(message)
func _initialize(): call_deferred("run")
func place(app,target:Vector3):
	app.targets[app.selected]=target; app.target_valid[app.selected]=true
	for i in range(300):
		var before:Vector3=app.rigs[app.selected].tip
		app._physics_process(1./60.)
		check(app.rigs[app.selected].tip.distance_to(before)<=.0251,"bilateral entry respects normal movement speed")
		if app.rigs[app.selected].tip.distance_to(target)<.001: return
	check(false,"actual bilateral route blocked: "+str(target)+" -> "+str(app.rigs[app.selected].tip))
func run():
	var app=load("res://scripts/simulator.gd").new(); root.add_child(app); app.set_physics_process(false)
	await process_frame
	for id in ["patient","side","equipment"]: app.prepare_check(id)
	app.begin_operation()
	for hand in range(2):
		if app.selected!=hand: app.switch_hand()
		var sign_x:=1. if hand==0 else -1.; var z:float=app.rigs[hand].portal.z
		app.choose_tool("knife"); place(app,Vector3(sign_x*1.32,.95,z-.25)); app.grip_down=true
		for i in range(101): place(app,Vector3(sign_x*1.32,.8,z-.25+.005*i))
		check(app.incision.opened[hand],"hand%d creates its own actual traced entry"%hand)
		app.release_controls()
		for p in [Vector3(sign_x*1.32,.8,z),Vector3(sign_x*1.32,.65,z),Vector3(sign_x*.9,.68,z),Vector3(0,.75,0),Vector3(sign_x*.9,.68,z),Vector3(sign_x*1.32,.65,z),Vector3(sign_x*1.32,.95,z),Vector3(sign_x*1.95,.95,z)]: place(app,p)
		check(app.rigs[hand].insertion<0.,"hand%d actually withdraws before exchange"%hand)
		app.choose_tool("cannula"); check(app.hand_tools[hand]=="cannula","hand%d exchanges only after actual exterior withdrawal"%hand)
	check(app.incision.opened==[true,true],"both anatomical portals retain their own entry evidence")
	check(not app.injury.metrics().corneal_breached and not app.injury.metrics().posterior_breached,"bilateral entry route preserves structural surfaces")
	app.queue_free(); await process_frame
	print("Bilateral entry: ",failures," failures"); quit(1 if failures else 0)
