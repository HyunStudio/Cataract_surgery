extends SceneTree
var failures:=0
func check(ok:bool,message:String)->void:
	if not ok: failures+=1; push_error(message)
func _initialize()->void: call_deferred("run")
func tick(app,n:=1)->void:
	for i in range(n): app._physics_process(1./60.)
func place(app,p:Vector3)->void:
	app.targets[0]=p; app.target_valid[0]=true
	for i in range(200):
		tick(app)
		if app.rigs[0].tip.distance_to(p)<.001: return
	check(false,"exchange route remains reachable through normal control: "+str(p)+" -> "+str(app.rigs[0].tip))
func run()->void:
	var app=load("res://scripts/simulator.gd").new(); root.add_child(app); app.set_physics_process(false)
	await process_frame
	app.start_practice()
	for p in [Vector3(1.32,.8,0),Vector3(1.32,.65,0),Vector3(.9,.68,0),Vector3(0,.75,0)]: place(app,p)
	app.choose_tool("cannula")
	check(app.hand_tools[0]=="forceps","intraocular exchange is blocked")
	for p in [Vector3(1.32,.52,0),Vector3(1.32,.80,0)]: place(app,p)
	app.withdraw_tools(); app.choose_tool("cannula")
	check(app.hand_tools[0]=="forceps","scheduled withdrawal does not permit exchange before resolved movement")
	tick(app,100)
	check(app.rigs[0].insertion<0.,"withdrawal action actually carries the tip outside the portal")
	app.choose_tool("cannula")
	check(app.hand_tools[0]=="cannula","withdrawal action unlocks exchange after collision resolution")
	check(not app.injury.metrics().corneal_breached,"aligned withdrawal preserves the corneal wall")
	app.queue_free(); await process_frame
	print("Tool exchange: ",failures," failures"); quit(1 if failures else 0)
