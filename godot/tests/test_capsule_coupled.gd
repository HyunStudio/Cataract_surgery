extends SceneTree
var failures:=0
func check(ok:bool,message:String)->void:
	if not ok: failures+=1; push_error(message)
class FailedKernel extends RefCounted:
	func solve_contact(request:Dictionary)->Dictionary:
		return {"status":1,"xyz":request.initial,"dual":PackedFloat64Array(),"stats":PackedFloat64Array()}
class RecordingKernel extends RefCounted:
	var inner=ClassDB.instantiate("MembraneContactKernel")
	var requests:Array[Dictionary]=[]
	var trajectory_requests:Array[Dictionary]=[]
	func solve_trajectory(request:Dictionary)->Dictionary:
		trajectory_requests.append(request.duplicate(true)); return inner.solve_trajectory(request)
	func guard_motion(request:Dictionary)->Dictionary: return inner.guard_motion(request)
	func solve_contact(request:Dictionary)->Dictionary:
		requests.append(request.duplicate(true)); return inner.solve_contact(request)
class UncertainKernel extends RefCounted:
	var inner=ClassDB.instantiate("MembraneContactKernel")
	func solve_contact(request:Dictionary)->Dictionary: return inner.solve_contact(request)
	func guard_motion(_request:Dictionary)->Dictionary: return {"status":2}
class FailedSecond extends RefCounted:
	var inner=ClassDB.instantiate("MembraneContactKernel")
	var calls:=0
	func guard_motion(request:Dictionary)->Dictionary: return inner.guard_motion(request)
	func solve_contact(request:Dictionary)->Dictionary:
		calls+=1
		if calls==2: return {"status":1}
		return inner.solve_contact(request)
class UnsettledBoundary extends RefCounted:
	func resolve(_before:Vector3,after:Vector3,outside:bool)->Dictionary:
		return {"valid":true,"position":after+Vector3(.001,0,0),"outside":outside,"contact":true}
func _initialize()->void:
	var static_kernel=ClassDB.instantiate("MembraneContactKernel")
	var anatomy_fixture:Dictionary=JSON.parse_string(FileAccess.get_file_as_string("res://iris_boundary265.json"))
	var anatomical_points:=PackedVector3Array()
	for i in range(0,anatomy_fixture.anatomy_xyz.size(),3): anatomical_points.append(Vector3(anatomy_fixture.anatomy_xyz[i],anatomy_fixture.anatomy_xyz[i+1],anatomy_fixture.anatomy_xyz[i+2]))
	var anatomy=load("res://scripts/anatomical_contact.gd").new()
	check(anatomy.configure({"positions":anatomical_points,"triangles":PackedInt32Array(anatomy_fixture.anatomy_triangles)},.004),"actual iris mesh freezes for nonmutating native queries")
	var anatomy_old:=PackedFloat64Array(); anatomy_old.resize(745*3)
	var anatomy_current:=anatomy_old.duplicate(); var anatomy_vertices:=PackedInt32Array()
	for body in anatomy_fixture.bodies:
		var v:=int(body.vertex); anatomy_vertices.append(v)
		for axis in range(3): anatomy_old[3*v+axis]=body.previous[axis]; anatomy_current[3*v+axis]=body.current[axis]
	var old_input:=anatomy_old.duplicate(); var current_input:=anatomy_current.duplicate()
	var anatomical_hit:Dictionary=anatomy.inspect(static_kernel,anatomy_old,anatomy_current,anatomy_vertices)
	check(anatomical_hit.status==1 and anatomical_hit.vertex==663 and anatomical_hit.face==252 and anatomical_hit.witness_t==0.,"actual265 iris penetration is rejected at the prior physical endpoint")
	check(anatomy_old==old_input and anatomy_current==current_input,"actual anatomy queries cannot project accepted tissue")
	for fixture in ["joint_physical264_second.json","joint_physical265.json"]:
		var physical_request:Dictionary=JSON.parse_string(FileAccess.get_file_as_string("res://"+fixture))
		for key in ["initial","predicted","inverse","rest","capsules"]: physical_request[key]=PackedFloat64Array(physical_request[key])
		for key in ["a","b","triangles"]: physical_request[key]=PackedInt32Array(physical_request[key])
		physical_request.budget=int(physical_request.budget)
		var original_request:Dictionary=physical_request.duplicate(true)
		var static_result:Dictionary=static_kernel.solve_contact(physical_request)
		check(static_result.status==0,fixture+" reaches original physical KKT gates: "+str(static_result.stats))
		check(physical_request==original_request,fixture+" preserves predictor, material and physical dimensions")
		if static_result.status==0:
			check(static_result.stats[1]<=1e-8 and static_result.stats[2]<=1e-9 and static_result.stats[3]<=1e-11,fixture+" retains physical residual gates")
		print(fixture," static stats: ",static_result.status," ",static_result.stats)
	var stalled_request:Dictionary=JSON.parse_string(FileAccess.get_file_as_string("res://joint_trajectory264_second.json"))
	for key in ["initial","predicted","inverse","rest","previous","packets","times"]: stalled_request[key]=PackedFloat64Array(stalled_request[key])
	for key in ["a","b","triangles","kinds"]: stalled_request[key]=PackedInt32Array(stalled_request[key])
	stalled_request.budget=int(stalled_request.budget)
	var stalled_before:Dictionary=stalled_request.duplicate(true)
	var recovered:Dictionary=static_kernel.solve_trajectory(stalled_request)
	check(recovered.status==0,"actual264 three-layer force stagnation reaches original gates: "+str(recovered.stats))
	check(stalled_request==stalled_before,"trajectory bridge preserves the captured predictor, material and motion")
	if recovered.status==0:
		check(recovered.stats[1]<=1e-8 and recovered.stats[2]<=1e-9 and recovered.stats[3]<=1e-11,"actual264 trajectory satisfies the unchanged force, gap and complementarity gates")
		for vertex in range(stalled_request.inverse.size()):
			if stalled_request.inverse[vertex]!=0.: continue
			for axis in range(3): check(recovered.xyz[vertex*3+axis]==stalled_request.initial[vertex*3+axis],"actual264 prescribed coordinates remain exact")
	print("Actual264 three-layer stats: ",recovered.status," ",recovered.stats)
	var source=load("res://scripts/capsule_solver.gd")
	if not source or not source.can_instantiate(): quit(1); return
	var trajectory_request:Dictionary=JSON.parse_string(FileAccess.get_file_as_string("res://joint_static262.json"))
	for key in ["initial","predicted","inverse","rest","capsules"]: trajectory_request[key]=PackedFloat64Array(trajectory_request[key])
	for key in ["a","b","triangles"]: trajectory_request[key]=PackedInt32Array(trajectory_request[key])
	trajectory_request.budget=int(trajectory_request.budget)
	var motion_data:Dictionary=JSON.parse_string(FileAccess.get_file_as_string("res://joint_motion262.json"))
	var recorded_body:Array=[]
	for index in range(motion_data.kinds.size()):
		var p:Array=motion_data.packets.slice(index*41,(index+1)*41)
		var vectors:Array=[]
		for off in [0,3,6,9,13,16,27,30,33,36]: vectors.append(Vector3(p[off],p[off+1],p[off+2]))
		recorded_body.append({"previous_a":vectors[0],"previous_b":vectors[1],"a":vectors[2],"b":vectors[3],"radius":p[12],"physical_radius":p[12],"path_t0":p[39],"path_t1":p[40],"path":{"tip0":vectors[4],"tip1":vectors[5],"a0":vectors[6],"b0":vectors[7],"a1":vectors[8],"b1":vectors[9],"rotation0":Quaternion(p[19],p[20],p[21],p[22]),"rotation1":Quaternion(p[23],p[24],p[25],p[26])}})
	var trajectory_model=source.new(); var trajectory_record:=RecordingKernel.new()
	trajectory_model.contact_backend=trajectory_record; trajectory_model._inverse_mass=trajectory_request.inverse; trajectory_model.triangles=trajectory_request.triangles
	var generated:Dictionary=trajectory_model._joint_contact_candidate(trajectory_request,recorded_body,PackedFloat64Array(motion_data.previous))
	check(not generated.is_empty() and not trajectory_record.trajectory_requests.is_empty(),"actual262 adds intermediate physical constraints and clears the complete represented motion: "+str(trajectory_model.native_failure))
	if not generated.is_empty():
		check(generated.times.size()<=8 and generated.times.size()>1,"actual262 uses bounded time constraint generation")
		for captured in trajectory_record.trajectory_requests: check(captured.predicted==trajectory_request.predicted and captured.previous==PackedFloat64Array(motion_data.previous),"actual refinement retains the original predictor and history")
		print("Actual262 continuous times: ",generated.times," stats=",generated.result.stats)
	var physical_check=source.new(); var physical_record:=RecordingKernel.new(); physical_check.set_contact_backend(physical_record)
	var pose=load("res://scripts/instrument_path.gd")
	var far_pose:=Vector3(3,3,3)
	var moving_body:Array=pose.build("forceps",.018,far_pose,Vector3.LEFT,true,far_pose,Vector3(-1,.03,0).normalized(),true,false)
	var moving_tools:Array[Dictionary]=[{"hand":0,"tip":far_pose,"radius":.018,"grip":false,"cut":false,"body":moving_body}]
	physical_check.step_tools(1./120.,moving_tools)
	check(physical_check.native_failure.is_empty() and physical_record.requests.size()==1,"rotating actual body reaches the joint static contact request")
	if physical_record.requests.size()==1:
		var packed:PackedFloat64Array=physical_record.requests[0].capsules
		check(packed[6]==.010 and packed[13]==.010 and packed[20]==.020,"joint endpoint forces use physical jaw/shaft radii while swept guards retain their enclosures")
	var model=source.new()
	check(model.has_method("set_contact_backend"),"actual capsule supports the packed64 joint timestep")
	if failures: quit(1); return
	check(model.set_contact_backend(ClassDB.instantiate("MembraneContactKernel")),"registered joint kernel installs")
	# A sub-float32 perturbation must survive an actual timestep and predictor.
	model._physical_xyz[1]+=1e-10; model._physical_previous[1]+=1e-10
	var original:PackedFloat64Array=model._physical_xyz.duplicate()
	model.step(1./120.,Vector3(3,3,3),.018,false,false)
	check(model.native_failure.is_empty() and model.metrics().integration_steps==1,"actual joint rest step accepts: "+str(model.native_failure))
	check(model._physical_previous[1]==original[1],"velocity history keeps the original double coordinate")
	check(model._physical_xyz[1]!=float(model.positions[0].y),"render publication cannot replace authoritative coordinates")
	var recording:=RecordingKernel.new(); model.set_contact_backend(recording)
	var before_xyz:PackedFloat64Array=model._physical_xyz.duplicate()
	var before_previous:PackedFloat64Array=model._physical_previous.duplicate()
	model.step(1./120.,Vector3(3,3,3),.018,false,false)
	check(model.native_failure.is_empty() and recording.requests.size()==1,"second actual substep retains the physical predictor")
	check(recording.requests[0].predicted[1]==before_xyz[1]+(before_xyz[1]-before_previous[1])*model.damping,"fixed inertial predictor uses doubles without publication feedback")
	for v in range(model.anchored.size()):
		if model.anchored[v]==0: continue
		for axis in range(3): check(model._physical_xyz[v*3+axis]==model._physical_rest[v*3+axis],"anchored physical coordinate remains exact")
	var saved:Dictionary=model._checkpoint()
	check(model.set_contact_backend(FailedKernel.new()),"failure injection retains physical state")
	var grip_tip:Vector3=model.positions[0]+Vector3(0,.025,0)
	var grip_path=load("res://scripts/instrument_path.gd")
	var grip_body:Array=grip_path.build("forceps",.018,grip_tip,Vector3.LEFT,true,grip_tip,Vector3.LEFT,true,false)
	var grip_tools:Array[Dictionary]=[{"hand":0,"tip":grip_tip,"radius":.065,"contact_radius":.018,"grip":true,"cut":false,"body":grip_body}]
	model.step_tools(1./60.,grip_tools)
	check(model._physical_xyz==saved._physical_xyz and model._physical_previous==saved._physical_previous and model.metrics().integration_steps==2 and model.metrics().grasped==-1,"failure rolls back packed64 state history time and acquisition")
	check(model.native_failure.get("reason","")=="native_joint_solve","failure is explicit")
	for key in saved: model.set(key,saved[key])
	var second:=FailedSecond.new(); model.set_contact_backend(second)
	model.step(1./60.,Vector3(3,3,3),.018,false,false)
	check(second.calls==2 and model._physical_xyz==saved._physical_xyz and model._physical_previous==saved._physical_previous and model.metrics().integration_steps==2,"later substep failure rolls back earlier accepted substeps")
	for key in saved: model.set(key,saved[key])
	var old_rest:PackedFloat64Array=model._physical_rest.duplicate()
	var old_previous:PackedFloat64Array=model._physical_previous.duplicate()
	var old_xyz:PackedFloat64Array=model._physical_xyz.duplicate()
	var planned:Dictionary=model._cutter.slice(model.positions,model.triangles,Vector3(-.4,.81,0),Vector3(.4,.81,0),Vector3.UP,.1)
	var cut:Dictionary=model.incise(Vector3(-.4,.81,0),Vector3(.4,.81,0),Vector3.UP,.1)
	check(cut.valid and cut.changed,"real incision applies with packed64 state")
	check(model._physical_xyz.size()==model.positions.size()*3 and model._physical_previous.size()==model._physical_xyz.size() and model._physical_rest.size()==model._physical_xyz.size(),"incision transfers all packed64 arrays")
	check(model._physical_rest.size()>old_rest.size() and model._physical_previous.size()>old_previous.size(),"cut allocates new material/history nodes")
	for i in range(planned.bindings.size()):
		var binding:Dictionary=planned.bindings[i]
		if binding.ids.x!=binding.ids.y or binding.ids.y!=binding.ids.z: continue
		for axis in range(3):
			check(model._physical_xyz[i*3+axis]==old_xyz[binding.ids.x*3+axis] and model._physical_previous[i*3+axis]==old_previous[binding.ids.x*3+axis],"uncut original nodes preserve physical positions and history bit for bit")
	var accepted:Dictionary=model._checkpoint()
	var invalid:Dictionary=model.incise(Vector3.ZERO,Vector3.ZERO,Vector3.UP,.1)
	check(not invalid.changed and model._physical_xyz==accepted._physical_xyz and model._physical_previous==accepted._physical_previous,"rejected incision preserves double state")
	var body_guard=source.new(); body_guard.set_contact_backend(UncertainKernel.new())
	var far:=Vector3(3,3,3)
	var tools:Array[Dictionary]=[{"hand":0,"tip":far,"radius":.018,"grip":false,"cut":false,"body":[{"a":far,"b":far+Vector3.RIGHT*.1,"previous_a":far,"previous_b":far+Vector3.RIGHT*.1,"radius":.018}]}]
	var guarded:Dictionary=body_guard._checkpoint(); body_guard.step_tools(1./120.,tools)
	check(body_guard.native_failure.get("reason","")=="native_joint_body_unresolved" and body_guard._physical_xyz==guarded._physical_xyz and body_guard._physical_previous==guarded._physical_previous and body_guard.metrics().integration_steps==0,"unresolved swept geometry rolls back an otherwise converged packed64 solve")
	tools[0].erase("body"); body_guard.step_tools(1./120.,tools)
	check(body_guard.native_failure.get("reason","")=="native_joint_body_unresolved" and body_guard.metrics().integration_steps==0,"tip-only sphere uses the same swept geometry guard")
	var shape=load("res://scripts/anterior_segment.gd").new()
	var specimen=source.new(); specimen.geometry=shape; specimen.reset()
	var coupled_capture:=RecordingKernel.new(); specimen.set_contact_backend(coupled_capture)
	var initial_area:float=specimen.metrics().initial_area
	var radius:=.4; var y:float=shape.bag_front(radius); var prior:=Vector3(radius,y,0)
	for i in range(1,65):
		var next:=Vector3(radius*cos(TAU*i/64.),y,radius*sin(TAU*i/64.))
		check(specimen.incise(prior,next,Vector3.UP,.05).valid,"actual curved incision retains double material state"); prior=next
	check(specimen.detached_components().size()==1 and specimen.metrics().cut_loss_area<1e-10,"joint specimen has the whole original flap")
	specimen.tissue_boundary=UnsettledBoundary.new()
	var prior_state:Dictionary=specimen._checkpoint()
	specimen.step(1./120.,far,.018,false,false)
	check(specimen.native_failure.get("reason","")=="native_joint_boundary_correction" and specimen._physical_xyz==prior_state._physical_xyz and specimen._physical_previous==prior_state._physical_previous and specimen.metrics().integration_steps==0,"anatomical correction rejects rather than changing a converged physical candidate")
	var boundary=load("res://scripts/flap_boundary.gd").new()
	boundary.configure(shape.cornea(),shape.iris(.96)); boundary.portals=shape.portals.duplicate()
	boundary.wounds=[[Vector3(1.32,.8,-.25),Vector3(1.32,.8,.25)]]; specimen.tissue_boundary=boundary
	var piece:Dictionary=specimen.detached_components()[0]; var vertex:int=piece.vertices[0]
	for v in piece.vertices:
		if specimen.positions[v].x>specimen.positions[vertex].x: vertex=v
	var tip:Vector3=specimen.positions[vertex]+Vector3(0,.025,0)
	var path=load("res://scripts/instrument_path.gd")
	for tick in range(3):
		var old_tip:=tip
		if tick>0: tip.y+=.005
		var entry:=Vector3(1.32,.8,0)
		var body:Array=path.build("forceps",.018,old_tip,(old_tip-entry).normalized(),tick>0,tip,(tip-entry).normalized(),true,false)
		var traction:Array[Dictionary]=[{"hand":0,"tip":tip,"radius":.065,"contact_radius":.018,"grip":true,"cut":false,"body":body}]
		specimen.step_tools(1./60.,traction)
		check(specimen.native_failure.is_empty(),"actual joint forceps traction accepts tick "+str(tick)+": "+str(specimen.native_failure))
		if not specimen.native_failure.is_empty():
			var capture:Dictionary=coupled_capture.requests[-1].duplicate(true)
			for key in capture:
				if typeof(capture[key]) in [TYPE_PACKED_FLOAT64_ARRAY,TYPE_PACKED_INT32_ARRAY]: capture[key]=Array(capture[key])
			var file:=FileAccess.open("res://joint-capsule-failure.json",FileAccess.WRITE)
			if file: file.store_string(JSON.stringify(capture))
			break
	check(specimen.metrics().integration_steps==3 and specimen.metrics().grasped>=0 and absf(specimen.metrics().retained_area-initial_area)<1e-10 and specimen.metrics().broken_edges==0,"actual joint traction retains the original area and attachment")
	print("Joint traction metrics: ",specimen.metrics()," stats=",specimen.joint_stats)
	print("Native coupled capsule: ",failures," failures")
	quit(0 if failures==0 else 1)
