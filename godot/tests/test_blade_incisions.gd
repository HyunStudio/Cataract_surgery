extends SceneTree
var failures:=0
class TraceCutter extends RefCounted:
	var inner=load("res://scripts/membrane_cut.gd").new()
	var calls:=0
	var fail_second:=false
	func slice_triangle(points,indices,a,b,c)->Dictionary:
		calls+=1
		if fail_second and calls==2:return {"valid":false,"changed":false,"reason":"injected_patch_failure","work":0}
		return inner.slice_triangle(points,indices,a,b,c)
class UnusedNative extends RefCounted:
	func solve_contact(_value:Dictionary)->Dictionary:return {}
func check(ok:bool,message:String)->void:
	if not ok:failures+=1;push_error(message)
func total(values:PackedFloat64Array)->float:
	var result:=0.
	for value in values:result+=value
	return result
func _initialize()->void:
	var model=load("res://scripts/capsule_solver.gd").new()
	check(model.has_method("incise_patches"),"capsule accepts transactional finite blade patch batches")
	if failures:quit(1);return
	model.geometry=load("res://scripts/anterior_segment.gd").new();model.reset()
	var velocity:=Vector3(.001,.002,-.001)
	for i in range(model.positions.size()):model._previous[i]=model.positions[i]-velocity
	var before:Dictionary=model.visual_state();var area:float=model.metrics().retained_area;var mass:float=total(model._rest_area)
	var patch:=PackedVector3Array([Vector3(-.4,.3,0),Vector3(.4,.3,0),Vector3(0,.8,0)])
	var result:Dictionary=model.incise_patches([patch])
	check(result.valid and result.changed,"finite blade patch opens actual curved anterior tissue")
	check(model.positions.size()>before.positions.size() and model.triangles.size()>before.triangles.size(),"incision adds retained banks instead of deleting contacted faces")
	check(absf(model.metrics().retained_area-area)<1e-10 and model.metrics().cut_loss_area<1e-10 and absf(total(model._rest_area)-mass)<1e-10,"blade incision preserves material rest area and lumped mass")
	for i in range(model.positions.size()):check((model.positions[i]-model._previous[i]).distance_to(velocity)<1e-6,"all new bank histories retain the existing material velocity")
	check(model.metrics().integration_steps==0,"pure geometric incision does not secretly integrate time")
	var saved:Dictionary=model.visual_state();var saved_history:PackedVector3Array=model._previous.duplicate();var saved_area:PackedFloat64Array=model._rest_area.duplicate();var events:int=model._incision_events
	var repeated:Dictionary=model.incise_patches([patch])
	check(repeated.valid and not repeated.changed and model.visual_state()==saved and model._previous==saved_history,"repeated stationary material cut does not heal banks or change histories")
	model.reset();var trace:=TraceCutter.new();trace.fail_second=true;model._cutter=trace
	before=model.visual_state();saved_history=model._previous.duplicate();saved_area=model._rest_area.duplicate();events=model._incision_events
	var bad:=PackedVector3Array([Vector3.ZERO,Vector3.ZERO,Vector3.UP])
	var rejected:Dictionary=model.incise_patches([patch,patch])
	check(not rejected.valid and trace.calls==2,"a later geometric patch failure exercises the whole-batch rejection")
	check(model.visual_state()==before and model._previous==saved_history and model._rest_area==saved_area and model._incision_events==events,"later failure rolls back preceding accepted cut topology area history and events")
	var empty:Dictionary=model.incise_patches([])
	check(empty.valid and not empty.changed and model.visual_state()==before,"inactive blade batch has no material side effects")
	var distant:=patch.duplicate()
	for i in range(distant.size()):distant[i]+=Vector3(3,0,0)
	var cheap:=TraceCutter.new();model._cutter=cheap
	var outside:Dictionary=model.incise_patches([distant])
	check(outside.valid and not outside.changed and cheap.calls==0 and model.visual_state()==before,"blade strokes wholly outside the capsule skip global topology work")
	var invalid:Dictionary=model.incise_patches([bad])
	check(not invalid.valid and cheap.calls==0,"collapsed blade patches reject before either broad-phase skipping or topology mutation")
	for oversized in [PackedVector3Array([Vector3(5,0,0),Vector3(10,0,0),Vector3(5,1,0)]),PackedVector3Array([Vector3(5,0,0),Vector3(6,0,0),Vector3(5,5,0)])]:
		var excessive:Dictionary=model.incise_patches([oversized])
		check(not excessive.valid and cheap.calls==0,"oversized finite blade patches reject even outside the tissue bounds")
	model._cutter=load("res://scripts/membrane_cut.gd").new();check(model.set_contact_backend(UnusedNative.new()),"packed64 material state can receive geometric cuts without a numerical solve")
	var precision=load("res://scripts/membrane_precision.gd")
	for i in range(model.positions.size()):
		model._physical_xyz[3*i+1]+=1e-12;model._physical_previous[3*i+1]+=2e-12
	model.positions=precision.publish(model._physical_xyz);model._previous=precision.publish(model._physical_previous)
	var physical_before:PackedFloat64Array=model._physical_xyz.duplicate();var native_result:Dictionary=model.incise_patches([patch])
	check(native_result.valid and native_result.changed,"finite incision transfers authoritative packed64 material state")
	check(model._physical_xyz.size()==model.positions.size()*3 and precision.publish(model._physical_xyz)==model.positions,"packed64 geometry and rendering proxies remain synchronized after cutting")
	check(absf(model._physical_xyz[1]-physical_before[1])<1e-15,"unchanged original material point keeps its double coordinate rather than repacking a float proxy")
	print("Blade material incision: ",failures," failures");quit(1 if failures else 0)
