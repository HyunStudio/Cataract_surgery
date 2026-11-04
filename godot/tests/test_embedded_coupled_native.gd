extends SceneTree
var failures:=0
func check(ok:bool,message:String)->void:
	if not ok:failures+=1;push_error(message)
class Backend extends RefCounted:
	var inner:RefCounted
	var trajectory_calls:=0
	func solve_contact_fem(request:Dictionary)->Dictionary:return inner.solve_contact_fem(request)
	func solve_trajectory_fem(request:Dictionary)->Dictionary:
		trajectory_calls+=1;return inner.solve_trajectory_fem(request)
	func contact_fem(request:Dictionary)->Dictionary:return inner.contact_fem(request)
class Guard extends RefCounted:
	var inner:RefCounted
	var collisions:=0
	func guard_motion(request:Dictionary)->Dictionary:
		var result:Dictionary=inner.guard_motion(request)
		if result.status==1:collisions+=1
		return result
func model():
	var tissue=load("res://scripts/embedded_membrane.gd").new()
	tissue.initialize(PackedVector3Array([Vector3.ZERO,Vector3.RIGHT,Vector3.BACK]),PackedInt32Array([0,1,2]),PackedByteArray([0,0,0]),1.)
	return tissue
func path(old_y:float,new_y:float,guard)->Dictionary:
	var packet:=PackedFloat64Array();packet.resize(41)
	for off in [0,3,6,9]:packet[off]=.3;packet[off+1]=old_y if off<6 else new_y;packet[off+2]=.3
	packet[12]=.1
	return {"kinds":PackedInt32Array([0]),"packets":packet,"guard":guard}
func _initialize()->void:
	check(ClassDB.class_exists("MembraneFEMKernel") and ClassDB.class_exists("MembraneContactKernel"),"guarded coupled engine test needs both actual native kernels")
	if failures:quit(1);return
	var backend:=Backend.new();backend.inner=ClassDB.instantiate("MembraneFEMKernel")
	var guard:=Guard.new();guard.inner=ClassDB.instantiate("MembraneContactKernel")
	var force:=PackedFloat64Array();force.resize(9);var metrics:Array=[]
	for hands in [1,2]:
		var tissue=model();tissue.grasp(0,0)
		if hands==2:tissue.grasp(1,1)
		var previous_y:=.12
		for step in range(3):
			var next_y:=.08-.002*step;var saved:Dictionary=tissue.snapshot();var started:=Time.get_ticks_usec()
			var result:Dictionary=tissue.advance_contact(1./60.,force,backend,2.,3.,path(previous_y,next_y,guard),1.,250)
			check(result.valid,"actual coupled motion meets original force, contact and full interval: "+str(result))
			if not result.valid:quit(1);return
			var after:Dictionary=tissue.snapshot()
			check(after.steps==step+1 and after.previous==saved.xyz,"actual guarded coupled step commits accepted time and histories together")
			var witness:Dictionary=tissue.contact_face(0,PackedFloat64Array([.3,next_y,.3,.3,next_y,.3]),.1,backend)
			check(witness.valid,"accepted actual body clearance can be queried independently")
			if step==0:check(after.contacts.dual[0]>0.,"first body pressure produces positive unilateral reaction")
			else:check(after.contacts.dual[0]==0. and witness.values[1]>.01,"inertial tissue separation releases contact without an adhesive reaction")
			for hand in range(hands):
				for axis in range(3):check(absf(after.xyz[hand*3+axis]-after.grasps[hand].target[axis])<=1e-9,"actual held target remains exact under body pressure")
			metrics.append({"hands":hands,"step":step,"force":result.force_inf,"gap":result.gap,"penetration":result.stats[12],"complementarity":result.stats[13],"dual":after.contacts.dual[0],"endpoint_clearance":witness.values[1],"elapsed_ms":(Time.get_ticks_usec()-started)/1000.})
			previous_y=next_y
	var crossing=model();var before:Dictionary=crossing.snapshot()
	var rejected:Dictionary=crossing.advance_contact(1./60.,force,backend,2.,3.,path(.12,-.12,guard),1.,250)
	check(not rejected.valid and guard.collisions>0 and backend.trajectory_calls>0,"actual midinterval crossing triggers a trajectory attempt and still cannot publish an invalid candidate")
	check(crossing.snapshot()==before,"actual continuous collision rolls back positions histories attachments reactions and time")
	var h:=sqrt(.5)
	var old_collisions:=guard.collisions;var old_attempts:=backend.trajectory_calls
	var curved:=PackedFloat64Array([0.,-1.,0.,0.,-1.,0.,0.,1.,0.,0.,1.,0.,.05,0.,0.,0.,0.,0.,0.,0.,0.,-h,h,0.,0.,h,h,1.,0.,0.,1.,0.,0.,1.,0.,0.,1.,0.,0.,0.,1.])
	var arc:Dictionary=crossing.advance_contact(1./60.,force,backend,2.,3.,{"kinds":PackedInt32Array([1]),"packets":curved,"guard":guard},1.,250)
	check(not arc.valid and guard.collisions>old_collisions and backend.trajectory_calls>old_attempts and crossing.snapshot()==before,"actual quaternion-arc collision triggers a staged attempt and preserves rollback when exact contact cannot be resolved")
	DirAccess.make_dir_recursive_absolute("res://reports")
	var file:=FileAccess.open("res://reports/embedded-coupled-metrics.json",FileAccess.WRITE)
	if file:file.store_string(JSON.stringify({"scope":"Actual original coupled FEM/grasp/body candidates with whole supplied linear/pose body interval guard. Synthetic triangle only; no anatomy, true jaw acquisition, controller, cut-remap motion, full surgery or active FPS qualification.","steps":metrics,"crossing_rejected":not rejected.valid,"arc_rejected":not arc.valid,"rollback":crossing.snapshot()==before},"",true,true))
	print("Embedded native coupled step: ",failures," failures");quit(1 if failures else 0)
