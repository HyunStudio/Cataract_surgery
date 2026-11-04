extends SceneTree
var failures:=0
func check(ok:bool,message:String)->void:
	if not ok:failures+=1;push_error(message)
func mass(state:Dictionary)->float:
	var total:=0.
	for value in state.support.mass:total+=value
	return total
func momentum(state:Dictionary)->PackedFloat64Array:
	var result:=PackedFloat64Array([0.,0.,0.])
	for node in range(state.support.mass.size()):
		for j in range(3):result[j]+=state.support.mass[node]*(state.xyz[node*3+j]-state.previous[node*3+j])
	return result
func _initialize()->void:
	check(ClassDB.class_exists("MembraneFEMKernel"),"real embedded dynamics require the loaded native FEM extension")
	if failures:quit(1);return
	var backend=ClassDB.instantiate("MembraneFEMKernel")
	var original=load("res://scripts/capsule_solver.gd").new();original.geometry=load("res://scripts/anterior_segment.gd").new();original.reset()
	var model=load("res://scripts/embedded_membrane.gd").new()
	check(model.initialize(original.rest_positions,original.triangles,original.anchored,1.).valid,"real curved embedded mechanical state initializes independently")
	var radius:=.4;var y:float=original.geometry.bag_front(radius);var prior:=Vector3(radius,y,0.)
	for i in range(1,65):
		var next:=Vector3(radius*cos(TAU*i/64.),y,radius*sin(TAU*i/64.));var down:=Vector3.UP*.05
		var cut:Dictionary=model.incise_patches([PackedVector3Array([prior-down,next-down,next+down]),PackedVector3Array([prior-down,next+down,prior+down])])
		check(cut.valid,"real dynamics setup retained cut %d: %s"%[i,cut.reason])
		if not cut.valid:quit(1);return
		prior=next
	var initial:Dictionary=model.snapshot();var initial_mass:=mass(initial);var center:PackedFloat64Array=model.physical_positions()
	check(initial.steps==0 and initial.time==0. and initial.events==128,"preparing retained topology does not secretly integrate time")
	var times:=PackedFloat64Array();var residual:=0.
	for i in range(30):
		var force:Dictionary=model.point_force(0,PackedFloat64Array([0.,.005,0.]))
		var started:=Time.get_ticks_usec()
		var step:Dictionary=model.advance(1./60.,force.force,backend,10000.,15000.)
		times.append((Time.get_ticks_usec()-started)/1000.)
		check(step.valid,"actual retained flap implicit traction %d: %s"%[i,step.reason])
		if not step.valid:print("FAILED_STEP ",step);quit(1);return
		residual=maxf(residual,step.force_inf)
	var moved:PackedFloat64Array=model.physical_positions();var before:Dictionary=model.snapshot()
	check(moved[1]>center[1]+1e-5,"real fine-point force moves the retained free flap through native implicit dynamics")
	check(before.steps==30 and absf(before.time-.5)<1e-12,"real backend advances exactly thirty accepted steps")
	check(absf(mass(before)-initial_mass)<1e-10 and before.indices==initial.indices,"small traction preserves retained material and topology")
	var old_momentum:=momentum(before)
	var recut:Dictionary=model.incise_patches([PackedVector3Array([Vector3(-.12,.35,0),Vector3(.12,.35,0),Vector3(0,.75,0)])])
	check(recut.valid and recut.changed,"already moving material can receive another genuine finite geometric incision")
	if not recut.valid:print("FAILED_RECUT ",recut);quit(1);return
	var recut_state:Dictionary=model.snapshot();var recut_momentum:=momentum(recut_state)
	check(recut_state.steps==before.steps and recut_state.time==before.time,"recutting moving material cannot advance or reset its time history")
	for j in range(3):check(absf(recut_momentum[j]-old_momentum[j])<1e-8,"moving cut-control remapping retains material momentum")
	for i in range(5):
		var force:Dictionary=model.point_force(0,PackedFloat64Array([0.,.005,0.]))
		var step:Dictionary=model.advance(1./60.,force.force,backend,10000.,15000.)
		check(step.valid,"newly refined moving material continues its real native dynamics")
		if not step.valid:print("FAILED_POSTCUT ",step);quit(1);return
		residual=maxf(residual,step.force_inf)
	var saved:Dictionary=model.snapshot();var force:Dictionary=model.point_force(0,PackedFloat64Array([0.,.02,0.]))
	var exhausted:Dictionary=model.advance(1./60.,force.force,backend,10000.,15000.,1.,0)
	check(not exhausted.valid and model.snapshot()==saved,"real numerical budget failure cannot publish even one partial state/history/time update")
	for node in range(saved.fixed.size()):
		if saved.fixed[node]==0:continue
		for j in range(3):check(saved.xyz[node*3+j]==saved.original[saved.support.controls[node]][j],"retained rim controls remain exactly fixed during actual native traction")
	check(absf(mass(saved)-initial_mass)<1e-10 and saved.steps==35,"actual cuts and dynamics preserve mass and accepted-step count")
	DirAccess.make_dir_recursive_absolute("res://reports")
	var file:=FileAccess.open("res://reports/embedded-native-metrics.json",FileAccess.WRITE)
	if file:file.store_string(JSON.stringify({"scope":"Actual native embedded model; direct geometric setup and fine-point force, not operator body/contact or a full surgical case.","steps":saved.steps,"clock":saved.time,"events":saved.events,"vertices":saved.rest.size(),"triangles":saved.indices.size()/3,"controls":saved.support.controls.size(),"mass":mass(saved),"independent_force_inf":residual,"center_lift":moved[1]-center[1],"traction_step_ms":times},"",true,true))
	print("Embedded native dynamics: ",failures," failures; steps=",saved.steps," mass=",mass(saved)," force=",residual," lift=",moved[1]-center[1]);quit(1 if failures else 0)
