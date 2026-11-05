extends SceneTree
var failures:=0
func check(ok:bool,message:String)->void:
 if not ok:failures+=1;push_error(message)
class ScalarBackend extends RefCounted:
 var inner:RefCounted
 var scalar_calls:=0
 var work:=0
 func record(v:Dictionary)->Dictionary:work+=int(v.stats[2]);return v
 func material_witness_fem(v:Dictionary)->Dictionary:scalar_calls+=1;return inner.material_witness_fem(v)
 func contact_fem(v:Dictionary)->Dictionary:return inner.contact_fem(v)
 func solve_fem(v:Dictionary)->Dictionary:return record(inner.solve_fem(v))
 func solve_grasp_fem(v:Dictionary)->Dictionary:return record(inner.solve_grasp_fem(v))
 func solve_contact_fem(v:Dictionary)->Dictionary:return record(inner.solve_contact_fem(v))
 func solve_precise_contact_fem(v:Dictionary)->Dictionary:return record(inner.solve_precise_contact_fem(v))
 func solve_material_points_fem(v:Dictionary)->Dictionary:return record(inner.solve_material_points_fem(v))
 func solve_trajectory_material_points_fem(v:Dictionary)->Dictionary:return record(inner.solve_trajectory_material_points_fem(v))
 func solve_seeded_trajectory_material_points_fem(v:Dictionary)->Dictionary:return record(inner.solve_seeded_trajectory_material_points_fem(v))
 func solve_trajectory_fem(v:Dictionary)->Dictionary:return record(inner.solve_trajectory_fem(v))
 func solve_seeded_trajectory_fem(v:Dictionary)->Dictionary:return record(inner.solve_seeded_trajectory_fem(v))
class BatchBackend extends ScalarBackend:
 var batch_calls:=0
 var pairs:=0
 func material_witnesses_fem(v:Dictionary)->Dictionary:
  batch_calls+=1;pairs+=int(v.controls.size()/9)*int(v.capsules.size()/7)
  return inner.material_witnesses_fem(v)
func run_case(number:int,backend)->Dictionary:
 var saved:Dictionary=FileAccess.open("res://tests/fixtures/operative-motion%s-state.bin"%number,FileAccess.READ).get_var()
 var model=load("res://scripts/embedded_membrane.gd").new();model._state=saved.state.duplicate(true)
 var before:Dictionary=model.snapshot();var motion:Dictionary=saved.motion.duplicate(true);motion.guard=ClassDB.instantiate("MembraneContactKernel")
 var started:=Time.get_ticks_msec()
 var result:Dictionary=model.advance_contact(saved.dt,saved.force,backend,saved.mu,saved.lambda,motion,saved.damping,saved.budget,saved.targets)
 var elapsed:=Time.get_ticks_msec()-started
 check(result.valid,"complete owned%s scalar/bulk candidate passes original physics and motion gates"%number)
 check(result.get("trajectory_iterations",-1)==backend.work and backend.work<=saved.budget,"candidate methods share original recorded Newton budget")
 var after:Dictionary=model.snapshot()
 if result.valid:check(after.steps==before.steps+1 and after.previous==before.xyz and after.events==before.events,"only original accepted clock and history advance once")
 else:check(after==before,"failed candidate is atomic")
 return {"result":result,"state":after,"elapsed_ms":elapsed}
func _initialize()->void:
 var raw=ClassDB.instantiate("MembraneFEMKernel")
 check(raw!=null and raw.has_method("material_witnesses_fem"),"parity requires actual bulk capability, never a falsely advertising proxy")
 if failures:quit(1);return
 var metrics:Array=[]
 for number in [150,180]:
  var scalar:=ScalarBackend.new();scalar.inner=raw;var a:=run_case(number,scalar)
  var bulk:=BatchBackend.new();bulk.inner=raw;var b:=run_case(number,bulk)
  check(var_to_bytes(a.result)==var_to_bytes(b.result) and var_to_bytes(a.state)==var_to_bytes(b.state),"entire owned%s accepted state, contact rows/duals, history and result bits match scalar"%number)
  check(scalar.scalar_calls>0 and bulk.scalar_calls==0 and bulk.batch_calls>0 and bulk.pairs==scalar.scalar_calls,"bulk still inspects exactly all original face/body/layer pairs")
  metrics.append({"case":number,"scalar_ms":a.elapsed_ms,"batch_ms":b.elapsed_ms,"scalar_calls":scalar.scalar_calls,"batch_calls":bulk.batch_calls,"pairs":bulk.pairs,"work":bulk.work,"force_inf":b.result.get("force_inf"),"equal_state_and_result":var_to_bytes(a.result)==var_to_bytes(b.result) and var_to_bytes(a.state)==var_to_bytes(b.state)})
  print("Witness batch owned",number,": ",metrics[-1])
 DirAccess.make_dir_recursive_absolute("res://reports")
 FileAccess.open("res://reports/witness-batch-owned-metrics.json",FileAccess.WRITE).store_string(JSON.stringify({"qualified":failures==0,"scope":"Two exact owned steps scalar/batch whole-state bit parity only; not full route, real-time, GPU or release qualification.","cases":metrics},"  ",true,true))
 print("Native witness batch advance: ",failures," failures");quit(1 if failures else 0)
