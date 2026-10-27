extends SceneTree
var failures:=0
func check(ok:bool,message:String)->void:
	if not ok: failures+=1; push_error(message)
func step(model,tip:Vector3,grip:bool,cut:=false)->void:
	var tools:Array[Dictionary]=[{"hand":0,"tip":tip,"radius":.065,"contact_radius":.018,"grip":grip,"cut":cut}]
	model.step_tools(1./60.,tools)
func _initialize()->void:
	var shape=load("res://scripts/anterior_segment.gd").new()
	var model=load("res://scripts/capsule_solver.gd").new(); model.geometry=shape; model.reset()
	check(model.has_method("detached_components"),"capsule exposes actual detached retained components")
	if failures: quit(1); return
	check(model.detached_components().is_empty(),"intact anchored capsule is not an extractable flap")
	for i in range(145):
		var a:=TAU*i/144.; step(model,Vector3(.57*cos(a),shape.bag_front(.57)-.005,.57*sin(a)),false,true)
	var pieces:Array=model.detached_components()
	check(not pieces.is_empty(),"real circular blade trace detaches surviving membrane faces")
	if pieces.is_empty(): quit(1); return
	model.pressure_load=.3
	var acceleration:PackedVector3Array=model._pressure_acceleration()
	var free_force:=0.; var attached_force:=0.
	for v in pieces[0].vertices: free_force+=acceleration[v].length()
	for i in range(model.positions.size()): attached_force+=acceleration[i].length()
	check(free_force<1e-12 and attached_force>0.,"compartment pressure acts on supported bag, not both-wetted free flap")
	model.pressure_load=0.
	var retained_frame:Dictionary=model.visual_state()
	var retained_indices:PackedInt32Array=retained_frame.triangles.duplicate()
	var boundary=load("res://scripts/flap_boundary.gd").new(); boundary.configure(shape.cornea(),shape.iris(.96))
	boundary.portals=shape.portals.duplicate()
	boundary.wounds=[[Vector3(1.32,.8,-.25),Vector3(1.32,.8,.25)]]; model.tissue_boundary=boundary
	var vertex:int=pieces[0].vertices[0]
	for v in pieces[0].vertices:
		if model.positions[v].x>model.positions[vertex].x: vertex=v
	var tip:Vector3=model.positions[vertex]+Vector3(0,.025,0)
	for i in range(10): step(model,tip,true)
	check(model.metrics().extracted_flaps==0,"a held but intraocular flap cannot disappear")
	step(model,tip,false)
	check(model.metrics().extracted_flaps==0 and not model.detached_components().is_empty(),"release cannot delete retained flap")
	step(model,tip,true)
	for target in [Vector3(tip.x,.9,0),Vector3(.9,.70,0),Vector3(1.32,.5,0),Vector3(1.32,1.05,0),Vector3(2.1,.98,0)]:
		for i in range(700):
			if tip.distance_to(target)<.0001: break
			tip=tip.move_toward(target,.005); step(model,tip,true)
		print("Flap at ",target," area=",model.metrics().retained_detached_area," extracted=",model.metrics().extracted_area," strain=",model.metrics().max_strain)
	for i in range(180): step(model,tip,true)
	for component in model.detached_components():
		for v in component.vertices:
			if model._outside[v]==0: print("Unpassed ",v," ",model.positions[v])
	print("Extraction metrics ",model.metrics()," retained=",model.detached_components().size())
	check(model.metrics().extracted_flaps>0 and model.metrics().extracted_area>0.,"complete held flap exits through the wound and retires actual material")
	check(model.metrics().retained_detached_area<1e-8,"entire retained flap exits rather than only the held vertex")
	check(retained_frame.triangles==retained_indices and retained_indices.size()>model.triangles.size(),"earlier capture retains the real flap after live extraction")
	check(model.metrics().finite,"traction and contact remain finite")
	var initial:float=model.metrics().initial_area
	check(absf(initial-model.metrics().retained_area-model.metrics().extracted_area-model.metrics().cut_loss_area)<1e-8,"rest-area accounting separates retained extracted and cut-away material")
	model.reset()
	check(model.metrics().extracted_flaps==0 and model.detached_components().is_empty(),"new specimen restores topology and extraction state")
	var center:Vector3=model.positions[0]
	step(model,center,true)
	var cutting:Array[Dictionary]=[{"hand":0,"tip":center,"radius":.065,"contact_radius":.018,"grip":true,"cut":false},{"hand":1,"tip":center,"radius":.3,"grip":false,"cut":true}]
	model.step_tools(1./60.,cutting)
	check(model.metrics().grasped==-1,"cutting away every supported face releases an orphaned point grasp")
	print("Capsule extraction: ",failures," failures"); quit(1 if failures else 0)
