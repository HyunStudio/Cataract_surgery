extends SceneTree
var failures:=0
func check(ok:bool,message:String)->void:
	if not ok:failures+=1;push_error(message)
func _initialize()->void:call_deferred("run")
func place(app,target:Vector3)->void:
	app.targets[0]=target;app.target_valid[0]=true
	for i in range(200):
		var before:Vector3=app.rigs[0].tip;app._physics_process(1./60.)
		check(app.rigs[0].tip.distance_to(before)<.0251,"blade operator moves through bounded physical pose updates")
		if app.paused:
			check(false,"blade operation rejected: "+str(app.capsule.native_failure));return
		if app.rigs[0].tip.distance_to(target)<.001:return
	check(false,"actual blade route cannot reach "+str(target)+" from "+str(app.rigs[0].tip))
func run()->void:
	var app=load("res://scripts/simulator.gd").new();root.add_child(app);app.set_physics_process(false);app.set_process(false);await process_frame
	app.start_practice();app.choose_tool("knife")
	for target in [Vector3(1.32,.80,0),Vector3(1.32,.65,0),Vector3(1.20,.65,0),Vector3(.90,.68,0),Vector3(0,.75,0)]:
		place(app,target)
		if failures:break
	var area:float=app.capsule.metrics().retained_area;var count:int=app.capsule.positions.size()
	app.grip_down=true
	var target:=Vector3(.57,app.geometry.bag_front(.57)-.005,0)
	if not failures:place(app,target)
	var state:Dictionary=app.capsule.metrics()
	print("Actual geometric blade: ",JSON.stringify({"metrics":state,"reason":app.capsule.native_failure,"status":app.status,"tip":str(app.rigs[0].tip),"clock":app.clock},"",true,true))
	check(app.capsule._incision_events>0 and app.capsule.positions.size()>count,"normal operator target motion creates retained geometric blade banks")
	check(absf(state.retained_area-area)<1e-9 and state.cut_loss_area<1e-9,"actual blade motion preserves material instead of deleting the contacted tissue")
	check(state.finite and app.capsule.native_failure.is_empty(),"actual prepared blade operation stays finite and accepts its physics ticks")
	if DisplayServer.get_name()!="headless":
		app.update_geometry();await process_frame;await RenderingServer.frame_post_draw
		root.get_texture().get_image().save_png("res://reports/geometric-blade.png")
	app.free();await process_frame;print("Actual blade operation: ",failures," failures");quit(1 if failures else 0)
