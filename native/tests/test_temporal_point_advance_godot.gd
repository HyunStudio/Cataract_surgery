extends SceneTree
var failures:=0
func check(ok:bool,message:String)->void:
 if not ok:failures+=1;push_error(message)
class Backend extends RefCounted:
 var inner:RefCounted
 var history:Array=[]
 func solve_fem(v:Dictionary)->Dictionary:return inner.solve_fem(v)
 func solve_grasp_fem(v:Dictionary)->Dictionary:return inner.solve_grasp_fem(v)
 func material_witness_fem(v:Dictionary)->Dictionary:return inner.material_witness_fem(v)
 func material_witnesses_fem(v:Dictionary)->Dictionary:return inner.material_witnesses_fem(v)
 func contact_fem(v:Dictionary)->Dictionary:return inner.contact_fem(v)
 func solve_contact_fem(v:Dictionary)->Dictionary:return inner.solve_contact_fem(v)
 func solve_precise_contact_fem(v:Dictionary)->Dictionary:return inner.solve_precise_contact_fem(v)
 func solve_material_points_fem(v:Dictionary)->Dictionary:
  var out:Dictionary=inner.solve_material_points_fem(v);history.append({"kind":"material_points","request":v.duplicate(true),"response":out.duplicate(true)});return out
 func solve_trajectory_material_points_fem(v:Dictionary)->Dictionary:
  var out:Dictionary=inner.solve_trajectory_material_points_fem(v);history.append({"kind":"material_points_trajectory","request":v.duplicate(true),"response":out.duplicate(true)});return out
 func solve_seeded_trajectory_material_points_fem(v:Dictionary)->Dictionary:
  var out:Dictionary=inner.solve_seeded_trajectory_material_points_fem(v);history.append({"kind":"material_points_trajectory_seeded","request":v.duplicate(true),"response":out.duplicate(true)});return out
 func solve_trajectory_fem(v:Dictionary)->Dictionary:
  var out:Dictionary=inner.solve_trajectory_fem(v);history.append({"kind":"ordinary_trajectory","request":v.duplicate(true),"response":out.duplicate(true)});return out
 func solve_seeded_trajectory_fem(v:Dictionary)->Dictionary:
  var out:Dictionary=inner.solve_seeded_trajectory_fem(v);history.append({"kind":"ordinary_seeded","request":v.duplicate(true),"response":out.duplicate(true)});return out
class Guard extends RefCounted:
 var inner:RefCounted
 var history:Array=[]
 func guard_motion(v:Dictionary)->Dictionary:
  var out:Dictionary=inner.guard_motion(v);history.append(out.duplicate(true));return out
 func guard_fine_motion(v:Dictionary)->Dictionary:
  var out:Dictionary=inner.guard_fine_motion(v);history.append(out.duplicate(true));return out
func _initialize()->void:
 var raw=ClassDB.instantiate("MembraneFEMKernel")
 check(raw!=null and raw.has_method("solve_trajectory_material_points_fem") and raw.has_method("material_witnesses_fem"),"owned180 needs actual temporal point kernel")
 if failures:quit(1);return
 var saved:Dictionary=FileAccess.open("res://tests/fixtures/operative-motion180-state.bin",FileAccess.READ).get_var()
 var model=load("res://scripts/embedded_membrane.gd").new();model._state=saved.state.duplicate(true)
 var before:Dictionary=model.snapshot();var backend:=Backend.new();backend.inner=raw
 var guard:=Guard.new();guard.inner=ClassDB.instantiate("MembraneContactKernel")
 var motion:Dictionary=saved.motion.duplicate(true);motion.guard=guard
 var started:=Time.get_ticks_msec()
 var result:Dictionary=model.advance_contact(saved.dt,saved.force,backend,saved.mu,saved.lambda,motion,saved.damping,saved.budget,saved.targets)
 var elapsed:=Time.get_ticks_msec()-started;var work:=0;var temporal_calls:=0;var ordinary_calls:=0
 for row in backend.history:
  work+=int(row.response.stats[2])
  if row.kind.begins_with("material_points_trajectory"):temporal_calls+=1
  if row.kind=="material_points_trajectory":
   check(not row.request.has("initial") and not row.request.has("multiplier_seed") and not row.request.has("penalty_seed"),"point temporal candidates never consume ordinary face seeds")
  if row.kind.begins_with("ordinary"):ordinary_calls+=1
 check(result.valid,"owned180 must pass original force/full motion gates: "+str(result))
 if result.valid:
  var after:Dictionary=model.snapshot()
  check(after.steps==before.steps+1 and after.events==before.events and after.previous==before.xyz and absf(after.time-before.time-saved.dt)<1e-12,"one accepted owned180 advances only physics/history once")
  check(result.force_inf<=1e-8 and result.trajectory_iterations<=250 and result.trajectory_iterations==work,"independent original force and shared work remain unchanged")
  check(temporal_calls>0 and .5 in result.trajectory_times,"middle collision uses temporal material points without ordinary seeds")
  check(not guard.history.is_empty() and guard.history[-1].status==0,"last complete large-geometry physical motion guard certifies clearance")
  check(after.contacts.has("material_points") and after.contacts.times==result.trajectory_times and after.contacts.source_steps==before.steps,"accepted temporal reactions keep original material/time provenance")
  var accepted:Dictionary=model.snapshot();var stopped:Dictionary=model.advance_contact(saved.dt,saved.force,backend,saved.mu,saved.lambda,motion,saved.damping,0,saved.targets)
  check(not stopped.valid and model.snapshot()==accepted,"zero remaining budget cannot alter accepted time or positions")
 else:check(model.snapshot()==before,"failed temporal exploration leaves owned state unchanged")
 DirAccess.make_dir_recursive_absolute("res://reports")
 FileAccess.open("res://reports/owned180-temporal-attempt.bin",FileAccess.WRITE).store_var({"state":before,"result":result,"native_history":backend.history,"guard_history":guard.history})
 var summary:={"qualified":false,"owned_step_qualified":result.valid and failures==0,"scope":"Owned180 actual engine step only; no full route, surgery, real-time or release qualification.","elapsed_ms":elapsed,"vertices":before.rest.size(),"faces":before.indices.size()/3,"controls":before.xyz.size()/3,"temporal_calls":temporal_calls,"ordinary_calls":ordinary_calls,"work":work,"result":result}
 FileAccess.open("res://reports/owned180-temporal-metrics.json",FileAccess.WRITE).store_string(JSON.stringify(summary,"  ",true,true))
 print("Temporal material point advance: ",failures," failures; elapsed_ms=",elapsed," result=",result);quit(1 if failures else 0)
