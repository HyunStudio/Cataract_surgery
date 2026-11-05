extends SceneTree
var failures:=0
func check(ok:bool,message:String)->void:
 if not ok:failures+=1;push_error(message)
func _initialize()->void:
 var backend=ClassDB.instantiate("MembraneFEMKernel");var guard=ClassDB.instantiate("MembraneContactKernel")
 check(backend!=null and backend.has_method("solve_material_points_fem"),"actual typed kernel needs material point normal candidates")
 if failures:quit(1);return
 var saved:Dictionary=FileAccess.open("res://tests/fixtures/operative-motion179-state.bin",FileAccess.READ).get_var()
 var model=load("res://scripts/embedded_membrane.gd").new();model._state=saved.state.duplicate(true)
 var before:Dictionary=model.snapshot();var motion:Dictionary=saved.motion.duplicate(true);motion.guard=guard
 var rejected:Dictionary=model.advance_contact(saved.dt,saved.force,backend,saved.mu,saved.lambda,motion,saved.damping,0,saved.targets)
 check(not rejected.valid and model.snapshot()==before,"zero-budget contact failure leaves original state bitwise unchanged")
 var started:=Time.get_ticks_msec()
 var answer:Dictionary=model.advance_contact(saved.dt,saved.force,backend,saved.mu,saved.lambda,motion,saved.damping,saved.budget,saved.targets)
 check(answer.valid,"owned179 passes original independent force and full motion gates: "+str(answer))
 if answer.valid:
  var after:Dictionary=model.snapshot()
  check(after.steps==before.steps+1 and after.time==before.time+saved.dt and after.previous==before.xyz,"exactly one physical clock/history update is committed")
  check(after.contacts.has("material_points") and not after.contacts.material_points.is_empty(),"distributed normal reactions retain their actual material point provenance")
  check(answer.trajectory_iterations<=saved.budget and answer.force_inf<=1e-8,"all retries share original budget and independent force tolerance")
  check(answer.get("candidate_ordinary_iterations",-1)==0 and answer.get("candidate_normal_iterations",-1)==answer.trajectory_iterations,"finite-axis owned179 completes without first running the stalled smooth solver")
  var data:={"qualified":true,"scope":"Owned179 actual native+engine transaction only; not full surgery, real-time or release.","result":answer,"elapsed_ms":Time.get_ticks_msec()-started,"points":after.contacts.material_points.size(),"steps":after.steps}
  DirAccess.make_dir_recursive_absolute("res://reports")
  FileAccess.open("res://reports/material-point-advance-metrics.json",FileAccess.WRITE).store_string(JSON.stringify(data,"  ",true,true))
 print("Material point native advance: ",failures," failures");quit(1 if failures else 0)
