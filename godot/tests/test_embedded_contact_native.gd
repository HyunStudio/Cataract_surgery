extends SceneTree
var failures:=0
func check(ok:bool,message:String)->void:
	if not ok:failures+=1;push_error(message)
func _initialize()->void:
	check(ClassDB.class_exists("MembraneFEMKernel"),"real retained contact needs actual extension")
	if failures:quit(1);return
	var kernel=ClassDB.instantiate("MembraneFEMKernel")
	var source=load("res://scripts/capsule_solver.gd").new();source.geometry=load("res://scripts/anterior_segment.gd").new();source.reset()
	var model=load("res://scripts/embedded_membrane.gd").new()
	check(model.initialize(source.rest_positions,source.triangles,source.anchored,1.).valid,"actual curved tissue initializes its own material state")
	var patch:=PackedVector3Array([Vector3(-.4,.3,0),Vector3(.4,.3,0),Vector3(0,.8,0)])
	var cut:Dictionary=model.incise_patches([patch])
	check(cut.valid and cut.changed,"actual finite incision produces retained fine collision faces")
	if failures:quit(1);return
	var state:Dictionary=model.snapshot();var motion:PackedFloat64Array=state.xyz.duplicate()
	for node in range(state.support.controls.size()):
		if state.fixed[node]!=0:continue
		motion[node*3+1]+=.0003*sin(node*.7)
	check(model.set_motion(motion,state.previous).valid,"contact uses live double deformed material, not rest or float display")
	var saved:Dictionary=model.snapshot();var view:Dictionary=model.contact_geometry();var chosen:=-1;var largest:=0.
	for face in range(view.triangles.size()/3):
		var refined:=false;var points:=PackedVector3Array()
		for j in range(3):
			var vertex:int=view.triangles[face*3+j]
			refined=refined or vertex>=source.rest_positions.size()
			points.append(Vector3(view.fine[vertex*3],view.fine[vertex*3+1],view.fine[vertex*3+2]))
		var area:float=(points[1]-points[0]).cross(points[2]-points[0]).length()
		if refined and area>largest:chosen=face;largest=area
	check(chosen>=0,"actual retained contact specimen contains a refined fine triangle")
	if chosen<0:quit(1);return
	var fine:=PackedVector3Array();var center:=PackedFloat64Array([0.,0.,0.])
	for j in range(3):
		var vertex:int=view.triangles[chosen*3+j]
		fine.append(Vector3(view.fine[vertex*3],view.fine[vertex*3+1],view.fine[vertex*3+2]))
		for axis in range(3):center[axis]+=view.fine[vertex*3+axis]/3.
	var normal:Vector3=(fine[1]-fine[0]).cross(fine[2]-fine[0]).normalized()
	var segment:=PackedFloat64Array()
	for repeat in range(2):
		for axis in range(3):segment.append(center[axis]+.03*normal[axis])
	var answer:Dictionary=model.contact_face(chosen,segment,.01,kernel)
	check(answer.valid,"actual refined curved contact passes independent witness checks: "+answer.reason)
	if not answer.valid:quit(1);return
	check(absf(answer.values[1]-.02)<1e-8,"actual retained fine plane has expected physical clearance")
	var maximum_point:=0.;var coarse_work:=0.;var fine_work:=0.
	for axis in range(3):
		var point:=0.;var displacement:=0.
		for j in range(3):
			point+=answer.material_weights[j]*view.xyz[answer.nodes[j]*3+axis]
			var delta:=.0001*sin(answer.nodes[j]*.23+axis)
			displacement+=answer.material_weights[j]*delta;coarse_work+=answer.gradient[j*3+axis]*delta
		maximum_point=maxf(maximum_point,absf(point-answer.values[5+axis]))
		fine_work+=2.*(answer.values[5+axis]-answer.values[2+axis])*displacement
	check(maximum_point<1e-11 and absf(coarse_work-fine_work)<1e-14,"actual fine contact material point and transpose-force map preserve virtual work")
	check(model.snapshot()==saved and answer.events==1 and answer.steps==0,"static contact never mutates accepted topology, time, histories or attachments")
	DirAccess.make_dir_recursive_absolute("res://reports")
	var file:=FileAccess.open("res://reports/embedded-contact-metrics.json",FileAccess.WRITE)
	if file:file.store_string(JSON.stringify({"scope":"Actual retained curved static contact and virtual work only; no coupled force equilibrium, CCD, instrument/controller or full case.","face":chosen,"fine_faces":view.triangles.size()/3,"controls":view.xyz.size()/3,"events":answer.events,"gap":answer.values[1],"material_point_error":maximum_point,"virtual_work_error":absf(coarse_work-fine_work)},"",true,true))
	print("Embedded native contact: ",failures," failures");quit(1 if failures else 0)
