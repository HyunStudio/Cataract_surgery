extends SceneTree
var failures:=0
func check(ok:bool,message:String)->void:
 if not ok:failures+=1;push_error(message)
func _initialize()->void:
 var cutter=load("res://scripts/membrane_cut.gd").new()
 check(cutter.has_method("slice_triangle64"),"retained incision accepts physical binary64 geometry without display rounding")
 if failures:quit(1);return
 var skinny:=PackedFloat64Array([0.3183777264711941,0.4552728047208582,0.469767304940897,0.3275560558799335,0.4551676272477041,0.4637006211618173,0.3367343505939624,0.4550624536587914,0.45763394851565503])
 var result:Dictionary=cutter.slice_triangle64(skinny,PackedInt32Array([0,1,2]),Vector3(2,2,2),Vector3(2.1,2,2),Vector3(2,2.1,2))
 check(result.valid and not result.changed and result.points64==skinny and result.indices==PackedInt32Array([0,1,2]),"positive physical sliver survives even though its display points are exactly collinear")
 var points:=PackedFloat64Array([-1.,0.,-1.,1.,0.,-1.,0.,0.,1.]);var saved:=points.duplicate()
 result=cutter.slice_triangle64(points,PackedInt32Array([0,1,2]),Vector3(0,-.2,-2),Vector3(0,.2,-2),Vector3(0,0,2))
 check(result.valid and result.changed and result.bindings.size()>3,"finite transverse sharp-edge patch actually creates retained banks")
 if result.valid:
  var total:=0.
  for portion in result.fractions:check(portion>0.,"all material fractions remain positive");total+=portion
  check(absf(total-1.)<1e-10,"transverse cut preserves the full source material domain")
  var reconstructed=load("res://scripts/membrane_precision.gd").transfer(points,result.bindings)
  check(reconstructed==result.points64,"physical cut coordinates reproduce their normalized original source bindings exactly")
 check(points==saved,"cutter cannot mutate caller physical coordinates")
 for bad in [PackedFloat64Array([0.,0.]),PackedFloat64Array([NAN,0.,0.,1.,0.,0.,0.,1.,0.])]:
  result=cutter.slice_triangle64(bad,PackedInt32Array([0,1,2]),Vector3(0,-.2,-2),Vector3(0,.2,-2),Vector3(0,0,2))
  check(not result.valid and not result.changed,"malformed physical coordinates fail without a published cut")
 var file:=FileAccess.open("res://tests/fixtures/operative-motion155-cut-state.bin",FileAccess.READ)
 var captured:Dictionary=file.get_var();var solver=load("res://scripts/embedded_membrane.gd").new();solver._state=captured.state.duplicate(true)
 result=solver._incise_one(captured.patch)
 check(result.valid,"exact incision after154 physical ticks clears binary32 display collapse")
 if result.valid:
  var after:Dictionary=solver.snapshot();var before:Dictionary=captured.state
  check(after.steps==before.steps and after.time==before.time and after.events==before.events+int(result.changed),"incision publishes only actual geometry changes without advancing the physical clock")
  var old_area:=0.;var new_area:=0.
  for area in before.areas:old_area+=area
  for area in after.areas:check(area>0.,"checkpoint retains every positive material fragment");new_area+=area
  check(absf(old_area-new_area)<1e-10,"checkpoint material area is conserved")
 print("Binary64 incision geometry: ",failures," failures");quit(1 if failures else 0)
