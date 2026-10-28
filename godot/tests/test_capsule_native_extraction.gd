extends SceneTree
var failures:=0
var ticks:=0
var total_contacts:=0
var total_uncertain:=0
const Path=preload("res://scripts/instrument_path.gd")
const ENTRY=Vector3(1.32,.8,0)
class JointBackend extends RefCounted:
	var kernel=ClassDB.instantiate("MembraneContactKernel")
	var calls:=0
	var last_stats:=PackedFloat64Array()
	func solve_contact(request:Dictionary)->Dictionary:
		calls+=1
		var result:Dictionary=kernel.solve_contact(request); last_stats=result.stats.duplicate()
		return result
	func diagnostics()->Dictionary: return {"calls":calls,"last_stats":last_stats}
func check(ok:bool,message:String)->void:
	if not ok: failures+=1; push_error(message)
func advance(model,old_tip:Vector3,tip:Vector3,grip:bool,old_grip:bool)->bool:
	var axis0:Vector3=(old_tip-ENTRY).normalized(); var axis1:Vector3=(tip-ENTRY).normalized()
	var body:Array=Path.build("forceps",.018,old_tip,axis0,old_grip,tip,axis1,grip,false)
	var tools:Array[Dictionary]=[{"hand":0,"tip":tip,"radius":.065,"contact_radius":.018,"grip":grip,"cut":false,"body":body}]
	var before:PackedVector3Array=model.positions.duplicate()
	var saved:Dictionary=model._checkpoint()
	model.step_tools(1./60.,tools); ticks+=1
	if not model.native_failure.is_empty():
		check(model.positions==before and model._previous==saved._previous and model.metrics().integration_steps==saved._integration_steps,"rejected actual extraction step preserves tissue history and time")
		for key in saved.keys():
			if typeof(saved[key])==TYPE_OBJECT: saved.erase(key)
		var capture:=FileAccess.open("res://rejected-extraction-step.bin",FileAccess.WRITE)
		if capture: capture.store_var({"state":saved,"tools":tools,"tick":ticks,"failure":model.native_failure})
		check(false,"refined extraction numerical failure at tick "+str(ticks)+": "+str(model.native_failure)); return false
	total_contacts+=model.metrics().body_contacts; total_uncertain+=model.metrics().body_uncertain
	if model.metrics().cut_loss_area>1e-10:
		for e in range(model._edge_a.size()):
			if model._edge_active[e]!=0: continue
			var a:int=model._edge_a[e]; var b:int=model._edge_b[e]
			print("Failed edge ",e," rest=",model._edge_rest[e]," ids=",a,",",b," before=",before[a],",",before[b]," after=",model.positions[a],",",model.positions[b]," pinned=",model._pinned[a],",",model._pinned[b])
		check(false,"gentle refined extraction lost material at tick "+str(ticks)); return false
	return true
func _initialize()->void:
	var shape=load("res://scripts/anterior_segment.gd").new()
	var model=load("res://scripts/capsule_solver.gd").new(); model.geometry=shape; model.reset()
	var backend=load("res://scripts/native_membrane_backend.gd").new()
	backend.diagnostic_capture="res://native-extraction-failure.json"
	if "--joint-contact" in OS.get_cmdline_user_args():
		backend=JointBackend.new(); check(model.set_contact_backend(backend),"packed64 joint backend available")
	else: check(model.set_stretch_backend(backend),"native backend available")
	var initial:float=model.metrics().initial_area
	var radius:=.4; var y:float=shape.bag_front(radius); var prior:=Vector3(radius,y,0)
	for i in range(1,65):
		var next:=Vector3(radius*cos(TAU*i/64.),y,radius*sin(TAU*i/64.))
		check(model.incise(prior,next,Vector3.UP,.05).valid,"refined actual incision"); prior=next
	var pieces:Array=model.detached_components()
	check(pieces.size()==1 and model.metrics().cut_loss_area<1e-10,"one area-preserved flap")
	if failures: quit(1); return
	var flap_area:float=pieces[0].area
	var boundary=load("res://scripts/flap_boundary.gd").new()
	check(boundary.configure(shape.cornea(),shape.iris(.96)),"real anatomical boundary")
	boundary.portals=shape.portals.duplicate(); boundary.wounds=[[ENTRY+Vector3(0,0,-.25),ENTRY+Vector3(0,0,.25)]]
	model.tissue_boundary=boundary
	var vertex:int=pieces[0].vertices[0]
	for v in pieces[0].vertices:
		if model.positions[v].x>model.positions[vertex].x: vertex=v
	var tip:Vector3=model.positions[vertex]+Vector3(0,.025,0)
	if not advance(model,tip,tip,true,false): quit(1); return
	check(model.metrics().grasped>=0,"actual forceps grasps the refined flap")
	check(model.metrics().extracted_flaps==0,"held internal flap remains material")
	if not advance(model,tip,tip,false,true): quit(1); return
	check(model.metrics().extracted_flaps==0,"release does not delete flap")
	if not advance(model,tip,tip,true,false): quit(1); return
	var started:=Time.get_ticks_msec()
	for target in [Vector3(tip.x,.9,0),Vector3(.9,.70,0),Vector3(1.32,.5,0),Vector3(1.32,1.05,0),Vector3(2.1,.98,0)]:
		for i in range(700):
			if tip.distance_to(target)<.0001: break
			var old_tip:=tip; tip=tip.move_toward(target,.005)
			if not advance(model,old_tip,tip,true,true):
				print("Extraction failure metrics ",model.metrics()," backend=",backend.diagnostics()); quit(1); return
			if ticks%25==0: print("Native extraction tick ",ticks," elapsed_ms=",Time.get_ticks_msec()-started," area=",model.metrics().retained_detached_area)
		print("Refined flap target ",target," metrics=",model.metrics())
	for i in range(180):
		if model.metrics().extracted_flaps>0: break
		if not advance(model,tip,tip,true,true): quit(1); return
	check(model.metrics().extracted_flaps==1 and absf(model.metrics().extracted_area-flap_area)<1e-8,"complete original flap exits through the actual wound")
	check(model.metrics().retained_detached_area<1e-8,"every flap vertex passes the boundary before retirement")
	check(absf(initial-model.metrics().retained_area-model.metrics().extracted_area)<1e-8,"extraction conserves original rest material")
	check(total_uncertain==0,"actual body contact stays resolved throughout extraction")
	print("Native extraction metrics ",model.metrics()," contacts=",total_contacts," uncertain=",total_uncertain," elapsed_ms=",Time.get_ticks_msec()-started)
	print("Native capsule extraction: ",failures," failures"); quit(1 if failures else 0)
