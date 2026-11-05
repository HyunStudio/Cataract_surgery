extends SceneTree
var failures:=0
func check(ok:bool,message:String)->void:
	if not ok:failures+=1;push_error(message)
class Guard extends RefCounted:
	var inner:RefCounted
	var fine_calls:=0
	var legacy_calls:=0
	var request:Dictionary
	func guard_motion(value:Dictionary)->Dictionary:
		legacy_calls+=1;request=value.duplicate(true);return inner.guard_motion(value)
	func guard_fine_motion(value:Dictionary)->Dictionary:
		fine_calls+=1;request=value.duplicate(true);return inner.guard_fine_motion(value)
func _initialize()->void:
	var kernel=ClassDB.instantiate("MembraneFEMKernel");var raw_guard=ClassDB.instantiate("MembraneContactKernel")
	check(raw_guard!=null and raw_guard.has_method("guard_fine_motion"),"actual typed kernel needs the extended geometry interface")
	if failures:quit(1);return
	var guard:=Guard.new();guard.inner=raw_guard
	var packet:Dictionary=FileAccess.open("res://tests/fixtures/operative-cut299-vertex-state.bin",FileAccess.READ).get_var()
	var model=load("res://scripts/embedded_membrane.gd").new();model._state=packet.state.duplicate(true)
	var old:Dictionary=model.snapshot();check(model.set_fine_geometry_capacity(8192,guard).valid,"actual extended guard authorizes only the bounded fine capacity")
	var cut:Dictionary=model._incise_one(packet.patch);check(cut.valid and cut.changed,"owned cut299 passes with original material detail")
	if not cut.valid:print(cut);quit(1);return
	var after_cut:Dictionary=model.snapshot();var physical:PackedFloat64Array=model.physical_positions()
	check(after_cut.rest.size()>4096 and after_cut.support.controls.size()<=4096,"fine capacity creates no oversized mechanical solve")
	var motion_packet:=PackedFloat64Array();motion_packet.resize(41)
	for off in [0,6]:
		motion_packet[off]=4.;motion_packet[off+1]=4.;motion_packet[off+2]=4.;motion_packet[off+3]=4.1;motion_packet[off+4]=4.;motion_packet[off+5]=4.
	motion_packet[12]=.01
	var request:={"previous":physical,"current":physical.duplicate(),"triangles":after_cut.indices,"kinds":PackedInt32Array([0]),"packets":motion_packet,"budget":128,"gap_tolerance":1e-9}
	var before_guard:=var_to_bytes(request)
	check(raw_guard.guard_motion(request).status==-1,"legacy typed guard retains its4096point limit")
	var checked:Dictionary=raw_guard.guard_fine_motion(request)
	check(checked.status==0 and checked.stats[1]==after_cut.indices.size()/3,"actual extended guard checks every fine face")
	check(var_to_bytes(request)==before_guard,"actual extended guard owns no input arrays")
	var bad:Dictionary=request.duplicate(true);bad.current[-1]=NAN
	check(raw_guard.guard_fine_motion(bad).status==-1,"high-index invalid geometry is rejected by the actual bridge")
	var force:=PackedFloat64Array();force.resize(after_cut.xyz.size())
	var motion:={"kinds":PackedInt32Array([0]),"packets":motion_packet,"guard":guard}
	var started:=Time.get_ticks_msec();var step:Dictionary=model.advance_contact(1./60.,force,kernel,2.,3.,motion,1.,250)
	check(step.valid,"actual FEM tick after owned large cut passes independent force/full geometry: "+str(step))
	if step.valid:
		var after:Dictionary=model.snapshot()
		check(after.steps==old.steps+1 and after.events==old.events+1 and after.previous==after_cut.xyz,"one accepted tick preserves cut and history semantics")
		check(guard.fine_calls>0 and guard.legacy_calls==0 and guard.request.current.size()==physical.size(),"operative physics dispatches complete large geometry to the extended guard")
		check(step.force_inf<=1e-8 and step.trajectory_iterations<=250,"large geometry retains original mechanical force and work gates")
		var saved:Dictionary=model.snapshot();var rejected:Dictionary=model.advance_contact(1./60.,force,kernel,2.,3.,motion,1.,0)
		check(not rejected.valid and model.snapshot()==saved,"exhausted large-geometry candidate cannot advance state")
		DirAccess.make_dir_recursive_absolute("res://reports")
		FileAccess.open("res://reports/fine-geometry-owned-cut-metrics.json",FileAccess.WRITE).store_string(JSON.stringify({"qualified":failures==0,"scope":"Owned cut299 plus synthetic far-body actual FEM tick only; not actual full operative route or real-time.","vertices":after.rest.size(),"faces":after.indices.size()/3,"controls":after.support.controls.size(),"step":step,"elapsed_ms":Time.get_ticks_msec()-started},"  ",true,true))
	print("Fine geometry native state: ",failures," failures");quit(1 if failures else 0)
