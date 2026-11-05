extends SceneTree
var failures:=0
class Backend extends RefCounted:
	var kernel=ClassDB.instantiate("MembraneFEMKernel")
	var request:Dictionary={}
	var answer:Dictionary={}
	func solve_precise_contact_fem(value:Dictionary)->Dictionary:
		request=value.duplicate(true);answer=kernel.solve_precise_contact_fem(value);return answer
	func solve_contact_fem(value:Dictionary)->Dictionary:
		request=value.duplicate(true);answer=kernel.solve_contact_fem(value);return answer
	func material_witness_fem(value:Dictionary)->Dictionary:return kernel.material_witness_fem(value)
	func contact_fem(value:Dictionary)->Dictionary:return kernel.contact_fem(value)
class Guard extends RefCounted:
	var kernel=ClassDB.instantiate("MembraneContactKernel")
	var request:Dictionary={}
	var answer:Dictionary={}
	func guard_motion(value:Dictionary)->Dictionary:
		request=value.duplicate(true);answer=kernel.guard_motion(value);return answer
func check(ok:bool,message:String)->void:
	if not ok:failures+=1;push_error(message)
func serial(value:Dictionary)->Dictionary:
	var result:Dictionary={}
	for key in value:
		var item=value[key]
		result[key]=Array(item) if item is PackedFloat64Array or item is PackedInt32Array else item
	return result
func save_failure(tissue,before:Dictionary,backend:Backend,guard:Guard,step:Dictionary,label:String)->void:
	DirAccess.make_dir_recursive_absolute("res://reports")
	var file:=FileAccess.open("res://reports/curved-coupled-failure.json",FileAccess.WRITE)
	if file:file.store_string(JSON.stringify({"label":label,"request":serial(backend.request),"answer":serial(backend.answer),"guard_request":serial(guard.request),"guard_answer":serial(guard.answer),"step":serial(step),"rollback":tissue.snapshot()==before},"",true,true))
	var state:=FileAccess.open("res://reports/curved-coupled-state.bin",FileAccess.WRITE)
	if state:state.store_var(before)
func geometry(state:Dictionary,face:int)->Dictionary:
	var points:=PackedVector3Array();var center:=PackedFloat64Array([0.,0.,0.])
	for j in range(3):
		var vertex:int=state.triangles[face*3+j]
		points.append(Vector3(state.fine[vertex*3],state.fine[vertex*3+1],state.fine[vertex*3+2]))
		for axis in range(3):center[axis]+=state.fine[vertex*3+axis]/3.
	var cross:Vector3=(points[1]-points[0]).cross(points[2]-points[0])
	return {"center":center,"normal":cross.normalized(),"area":cross.length()*.5}
func specimen():
	var source=load("res://scripts/capsule_solver.gd").new();source.geometry=load("res://scripts/anterior_segment.gd").new();source.reset()
	var tissue=load("res://scripts/embedded_membrane.gd").new();tissue.initialize(source.rest_positions,source.triangles,source.anchored,1.)
	var cut:Dictionary=tissue.incise_patches([PackedVector3Array([Vector3(-.4,.3,0),Vector3(.4,.3,0),Vector3(0,.8,0)])])
	check(cut.valid and cut.changed,"curved coupled specimen has an actual retained incision")
	return tissue
func _initialize()->void:
	check(ClassDB.class_exists("MembraneFEMKernel") and ClassDB.class_exists("MembraneContactKernel"),"curved coupling uses real native kernels")
	if failures:quit(1);return
	var metrics:Array=[]
	for settings in [[2.,1,1],[10000.,1,1],[10000.,2,2]]:
		var tissue=specimen();var before:Dictionary=tissue.snapshot();var view:Dictionary=tissue.contact_geometry()
		var chosen:Array[int]=[]
		for body in range(settings[2]):
			var best:=-1;var area:=0.
			for face in range(view.triangles.size()/3):
				var embedded:=false
				for k in range(9):
					var w:float=view.weights[face*9+k]
					if w>.05 and w<.95:embedded=true
				if not embedded:continue
				var candidate:=geometry(view,face);var separated:=true
				for previous in chosen:
					var center:PackedFloat64Array=geometry(view,previous).center;var distance:=0.
					for axis in range(3):distance+=pow(candidate.center[axis]-center[axis],2)
					if distance<.15*.15:separated=false
				if separated and candidate.area>area:best=face;area=candidate.area
			check(best>=0,"retained refined curved face is available for each separated body")
			if best<0:quit(1);return
			chosen.append(best)
		check(tissue.grasp(0,0).valid,"curved coupled case holds a real free capsule point")
		if settings[1]==2:check(tissue.grasp(1,1).valid,"curved coupled case has two independent hands")
		var packets:=PackedFloat64Array();var kinds:=PackedInt32Array()
		for face in chosen:
			var local:=geometry(view,face);var packet:=PackedFloat64Array();packet.resize(41)
			for off in [0,3,6,9]:
				for axis in range(3):packet[off+axis]=local.center[axis]+local.normal[axis]*(.012 if off<6 else .008)
			packet[12]=.01;packets.append_array(packet);kinds.append(0)
		var backend:=Backend.new();var guard:=Guard.new();var force:=PackedFloat64Array();force.resize(before.xyz.size())
		var label:="mu=%s hands=%s bodies=%s"%[settings[0],settings[1],settings[2]]
		before=tissue.snapshot();var started:=Time.get_ticks_usec()
		var result:Dictionary=tissue.advance_contact(1./60.,force,backend,settings[0],settings[0]*1.5,{"kinds":kinds,"packets":packets,"guard":guard},1.,250)
		print("Curved coupled ",label," result=",result)
		if not result.valid:
			save_failure(tissue,before,backend,guard,result,label);check(false,"actual refined curved coupled step failed: "+result.reason);quit(1);return
		var after:Dictionary=tissue.snapshot();var active:=0;var refined_active:=0;var active_bodies:Dictionary={}
		for pair in range(after.contacts.dual.size()):
			if after.contacts.dual[pair]<=0.:continue
			active+=1;active_bodies[pair%settings[2]]=true;var face:int=pair/settings[2]
			for k in range(9):
				if view.weights[face*9+k]>.05 and view.weights[face*9+k]<.95:refined_active+=1;break
		check(active>0 and refined_active>0 and active_bodies.size()==settings[2],"positive contact forces actually traverse nonidentity fine B and every face-major/body-minor column")
		check(after.steps==1 and after.events==1 and after.previous==before.xyz,"real retained curved candidate commits one guarded physical tick without changing incision topology")
		metrics.append({"label":label,"controls":after.xyz.size()/3,"faces":after.indices.size()/3,"selected_faces":chosen,"active":active,"refined_active":refined_active,"force":result.force_inf,"gap":result.gap,"penetration":result.stats[12],"complementarity":result.stats[13],"elapsed_ms":(Time.get_ticks_usec()-started)/1000.})
	DirAccess.make_dir_recursive_absolute("res://reports")
	var file:=FileAccess.open("res://reports/embedded-coupled-curved-metrics.json",FileAccess.WRITE)
	if file:file.store_string(JSON.stringify({"scope":"Direct setup of actual retained curved capsule, nonidentity B, original coupled force and supplied body guards. Synthetic pressure bodies, no actual jaw acquisition/controller, surrounding anatomy, cut-remap path, full surgery or active FPS qualification.","cases":metrics},"",true,true))
	print("Embedded native curved coupled step: ",failures," failures");quit(1 if failures else 0)
