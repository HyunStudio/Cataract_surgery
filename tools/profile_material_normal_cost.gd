extends SceneTree
class Backend extends RefCounted:
 var inner:RefCounted
 var point_us:=0
 var witness_us:=0
 var point_calls:=0
 var witness_calls:=0
 func solve_material_points_fem(value:Dictionary)->Dictionary:
  var started:=Time.get_ticks_usec();var result:Dictionary=inner.solve_material_points_fem(value)
  point_us+=Time.get_ticks_usec()-started;point_calls+=1;return result
 func material_witness_fem(value:Dictionary)->Dictionary:
  var started:=Time.get_ticks_usec();var result:Dictionary=inner.material_witness_fem(value)
  witness_us+=Time.get_ticks_usec()-started;witness_calls+=1;return result
 func solve_contact_fem(value:Dictionary)->Dictionary:return inner.solve_contact_fem(value)
class Guard extends RefCounted:
 var inner:RefCounted
 var elapsed_us:=0
 func guard_motion(value:Dictionary)->Dictionary:
  var started:=Time.get_ticks_usec();var result:Dictionary=inner.guard_motion(value)
  elapsed_us+=Time.get_ticks_usec()-started;return result
func _initialize()->void:
 var backend:=Backend.new();backend.inner=ClassDB.instantiate("MembraneFEMKernel")
 var guard:=Guard.new();guard.inner=ClassDB.instantiate("MembraneContactKernel")
 var saved:Dictionary=FileAccess.open("res://tests/fixtures/operative-motion179-state.bin",FileAccess.READ).get_var()
 var model=load("res://scripts/embedded_membrane.gd").new();model._state=saved.state.duplicate(true)
 var motion:Dictionary=saved.motion.duplicate(true);motion.guard=guard
 var started:=Time.get_ticks_usec()
 var result:Dictionary=model.advance_contact(saved.dt,saved.force,backend,saved.mu,saved.lambda,motion,saved.damping,saved.budget,saved.targets)
 var elapsed:=Time.get_ticks_usec()-started
 var evidence:={"qualified":false,"scope":"Cost observation of owned179 only. No real-time, full case or release claim.","step_valid":result.valid,"result":result,"total_us":elapsed,"point_calls":backend.point_calls,"point_us":backend.point_us,"witness_calls":backend.witness_calls,"witness_us":backend.witness_us,"guard_us":guard.elapsed_us,"other_us":elapsed-backend.point_us-backend.witness_us-guard.elapsed_us}
 var passed:bool=result.valid and result.candidate_ordinary_iterations==0 and result.force_inf<=1e-8 and model.snapshot().steps==saved.state.steps+1
 FileAccess.open("res://reports/material-normal-cost-profile.json",FileAccess.WRITE).store_string(JSON.stringify(evidence,"  ",true,true))
 print(JSON.stringify(evidence,"",true,true));quit(0 if passed else 1)
