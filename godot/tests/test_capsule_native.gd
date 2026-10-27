extends SceneTree
var failures:=0
func check(ok:bool,message:String)->void:
	if not ok: failures+=1; push_error(message)
class FailedBackend extends RefCounted:
	func project(_p,_w,_a,_b,_r,_active,_lambda,_alpha)->Dictionary:
		return {"valid":false,"reason":"deliberate_backend_failure"}
class BadOutputBackend extends RefCounted:
	func project(p,_w,_a,_b,_r,_active,multipliers,_alpha)->Dictionary:
		var changed:PackedVector3Array=p.duplicate(); changed[0]=Vector3(INF,0,0)
		return {"valid":true,"positions":changed,"lambda":multipliers.duplicate()}
class BodyFailure extends RefCounted:
	var inner=load("res://scripts/membrane_contact.gd").new()
	var calls:=0
	func valid_body(body:Array)->bool: return inner.valid_body(body)
	func project(_p,_t,_w,_body,_previous)->Dictionary:
		calls+=1; return {"valid":false}
class BoundaryFailure extends RefCounted:
	var calls:=0
	func resolve(start:Vector3,_finish:Vector3,outside:bool)->Dictionary:
		calls+=1; return {"valid":false,"position":start,"outside":outside,"contact":true}
class UnsettledBoundary extends RefCounted:
	var calls:=0
	var shift:=Vector3(.001,0,0)
	func resolve(_start:Vector3,finish:Vector3,outside:bool)->Dictionary:
		calls+=1; return {"valid":true,"position":finish+shift,"outside":outside,"contact":true}
class PrescribedBoundary extends RefCounted:
	var material_point:Vector3
	func resolve(start:Vector3,finish:Vector3,outside:bool)->Dictionary:
		return {"valid":true,"position":material_point+Vector3(.001,0,0) if start==material_point else finish,"outside":outside,"contact":start==material_point}
class CancellingBody extends RefCounted:
	var inner=load("res://scripts/membrane_contact.gd").new()
	var world:WeakRef
	func valid_body(body:Array)->bool: return inner.valid_body(body)
	func project(p,_t,_w,_body,_previous)->Dictionary:
		var changed:PackedVector3Array=p.duplicate()
		for v in world.get_ref().detached_components()[0].vertices: changed[v]+=Vector3(.001,0,0)
		return {"valid":true,"positions":changed,"contacts":1,"residual":0.,"uncertain":0}
func _initialize()->void:
	var model=load("res://scripts/capsule_solver.gd").new()
	check(model.has_method("set_stretch_backend"),"actual capsule accepts a transactional native stretch backend")
	if failures: quit(1); return
	var backend=load("res://scripts/native_membrane_backend.gd").new()
	backend.diagnostic_capture="res://native-proximal-failure.json"
	check(backend.ready(),"native backend uses the registered Godot extension")
	var pinned:Dictionary=backend.project(PackedVector3Array([Vector3.ZERO,Vector3.RIGHT]),PackedFloat64Array([0.,0.]),PackedInt32Array([0]),PackedInt32Array([1]),PackedFloat64Array([.5]),PackedByteArray([1]),PackedFloat64Array([0.]),.1)
	check(pinned.valid and absf(pinned["lambda"][0]+5.)<1e-10,"two prescribed endpoints retain their compliant reaction dual without moving")
	check(model.set_stretch_backend(FailedBackend.new()),"explicit failure backend can exercise the same integration boundary")
	var before:Dictionary=model.visual_state(); var history:PackedVector3Array=model._previous.duplicate()
	var time_before:int=model.metrics().integration_steps
	model.step(1./60.,model.positions[0]+Vector3(0,.01,0),.05,true,false)
	check(model.visual_state()==before and model._previous==history and model.metrics().integration_steps==time_before,"backend failure rolls back positions history and time")
	check(model.metrics().grasped==-1 and model.native_failure.reason=="deliberate_backend_failure","failed acquisition rolls back while exposing its numerical failure")
	model.set_stretch_backend(BadOutputBackend.new())
	model.step(1./60.,Vector3(3,3,3),.018,false,false)
	check(model.visual_state()==before and model._previous==history and model.metrics().integration_steps==time_before and model.native_failure.reason=="native_output","nonfinite accepted-looking backend output is rejected atomically")
	check(model.set_stretch_backend(backend),"native stretch backend installs")
	var shape=load("res://scripts/anterior_segment.gd").new(); model.geometry=shape; model.reset()
	var original:Dictionary=model.metrics()
	var radius:=.4; var y:float=shape.bag_front(radius); var prior:=Vector3(radius,y,0)
	for i in range(1,65):
		var next:=Vector3(radius*cos(TAU*i/64.),y,radius*sin(TAU*i/64.))
		var cut:Dictionary=model.incise(prior,next,Vector3.UP,.05)
		check(cut.valid,"real curved incision transfers to native integration")
		prior=next
	var boundary_failure:=BoundaryFailure.new(); model.tissue_boundary=boundary_failure
	before=model.visual_state(); history=model._previous.duplicate()
	model.step(1./60.,Vector3(3,3,3),.018,false,false)
	check(boundary_failure.calls>0 and model.native_failure.reason=="native_tissue_boundary","native update retains the anatomical tissue boundary operator")
	check(model.visual_state()==before and model._previous==history and model.metrics().integration_steps==0 and model.metrics().extracted_area==0.,"tissue boundary failure rolls back material history and extraction")
	var boundary=load("res://scripts/flap_boundary.gd").new()
	check(boundary.configure(shape.cornea(),shape.iris(.96)),"actual corneal and iris boundary configured")
	boundary.portals=shape.portals.duplicate(); boundary.wounds=[[Vector3(1.32,.8,-.25),Vector3(1.32,.8,.25)]]
	model.tissue_boundary=boundary
	for i in range(30): model.step(1./60.,Vector3(3,3,3),.018,false,false)
	check(model.native_failure.is_empty(),"refined rest specimen advances without native failure: "+str(model.native_failure))
	var tools:Array[Dictionary]=[{"hand":0,"tip":model.positions[1]+Vector3(0,.025,0),"radius":.065,"contact_radius":.018,"grip":true,"cut":false}]
	model.step_tools(1./60.,tools); tools[0].tip.y+=.005; model.step_tools(1./60.,tools)
	check(model.native_failure.is_empty(),"actual small forceps traction converges: "+str(model.native_failure))
	check(model.metrics().cut_loss_area<1e-10 and absf(model.metrics().retained_area-original.initial_area)<1e-10,"native traction preserves the real refined flap material")
	check(model.metrics().integration_steps==32,"native integration advances all requested outer ticks")
	print("Native capsule metrics: ",model.metrics()," backend=",backend.diagnostics())
	var saved:Dictionary=model._checkpoint()
	var prescribed:=PrescribedBoundary.new(); prescribed.material_point=model.positions[model.metrics().grasped]
	model.tissue_boundary=prescribed; before=model.visual_state(); history=model._previous.duplicate(); time_before=model.metrics().integration_steps
	model.step_tools(1./60.,tools)
	check(model.native_failure.get("reason","")=="native_kinematic_boundary","anatomical contact cannot silently displace a prescribed tool attachment: "+str(model.native_failure))
	check(model.visual_state()==before and model._previous==history and model.metrics().integration_steps==time_before,"incompatible prescribed attachment rolls back the outer tick")
	for key in saved: model.set(key,saved[key])
	model.release_hand(0); model._previous=model.positions.duplicate()
	var unsettled:=UnsettledBoundary.new(); model.tissue_boundary=unsettled
	before=model.visual_state(); history=model._previous.duplicate(); time_before=model.metrics().integration_steps
	model.step(1./60.,Vector3(3,3,3),.018,false,false)
	check(model.native_failure.get("reason","")=="native_coupling_exhausted","valid-looking but unsettled boundary cannot count as accepted mechanics: "+str(model.native_failure))
	check(model.visual_state()==before and model._previous==history and model.metrics().integration_steps==time_before,"unsettled coupled contact rolls back instead of creating physical rupture")
	var cancelling:=CancellingBody.new(); cancelling.world=weakref(model); model._face_contact=cancelling
	unsettled.shift=Vector3(-.001,0,0)
	var path=load("res://scripts/instrument_path.gd")
	var far:=Vector3(3,3,3)
	var opposing_tools:Array[Dictionary]=[{"hand":0,"tip":far,"radius":.018,"contact_radius":.018,"grip":false,"cut":false,"body":path.build("forceps",.018,far,Vector3.RIGHT,false,far,Vector3.RIGHT,false,false)}]
	model.step_tools(1./60.,opposing_tools)
	check(model.native_failure.get("reason","")=="native_coupling_exhausted" and model.visual_state()==before and model.metrics().integration_steps==time_before,"opposing body and boundary corrections cannot conceal contact error through cancellation")
	var guard=load("res://scripts/capsule_solver.gd").new(); guard.set_stretch_backend(backend)
	var body_failure:=BodyFailure.new(); guard._face_contact=body_failure
	var tip:Vector3=guard.positions[0]+Vector3(0,.025,0)
	var body:Array=path.build("forceps",.018,tip,Vector3.RIGHT,true,tip+Vector3(.001,0,0),Vector3.RIGHT,true,false)
	var body_tools:Array[Dictionary]=[{"hand":0,"tip":tip+Vector3(.001,0,0),"radius":.065,"contact_radius":.018,"grip":true,"cut":false,"body":body}]
	before=guard.visual_state(); history=guard._previous.duplicate()
	guard.step_tools(1./60.,body_tools)
	check(body_failure.calls>0 and guard.native_failure.reason=="native_body_contact","native update retains actual tool-body contact projection")
	check(guard.visual_state()==before and guard._previous==history and guard.metrics().integration_steps==0 and guard.metrics().grasped==-1,"tool-body failure rolls back the entire accepted acquisition and motion")
	guard._face_contact=load("res://scripts/membrane_contact.gd").new()
	var center:Vector3=guard.positions[0]
	var start_tip:=center+Vector3(0,.04,0); var end_tip:=center+Vector3(0,.01,0)
	body=path.build("forceps",.018,start_tip,Vector3.RIGHT,false,end_tip,Vector3.RIGHT,false,false)
	body_tools=[{"hand":0,"tip":end_tip,"radius":.065,"contact_radius":.018,"grip":false,"cut":false,"body":body}]
	before=guard.visual_state()
	guard.step_tools(1./60.,body_tools)
	check(guard.native_failure.is_empty() and guard.metrics().integration_steps==1,"actual moving forceps body accepts a native elastic/contact step: "+str(guard.native_failure))
	check(guard.metrics().body_contacts>0 and guard.positions!=before.positions,"actual shaft sweep moves tissue through the retained face-contact operator")
	check(guard.metrics().cut_loss_area<1e-10,"gentle shaft contact does not spuriously remove material")
	print("Native body metrics: ",guard.metrics())
	print("Native capsule: ",failures," failures")
	quit(1 if failures else 0)
