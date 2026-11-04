extends SceneTree
var failures:=0
func check(ok:bool,message:String)->void:
 if not ok:failures+=1;push_error(message)
func decoded(encoded:String)->PackedFloat64Array:return Marshalls.base64_to_raw(encoded).to_float64_array()
func points(values:PackedFloat64Array)->PackedVector3Array:
 var result:=PackedVector3Array()
 for i in range(0,values.size(),3):result.append(Vector3(values[i],values[i+1],values[i+2]))
 return result
func _initialize()->void:
 var detail:Dictionary=JSON.parse_string(FileAccess.get_file_as_string("res://tests/fixtures/fine-material-orientation.json"))
 var original:=points(decoded(detail.original_rest_le));var published:=points(decoded(detail.published_rest_le));var rows:=decoded(detail.material_weights_le)
 var ids:=PackedInt32Array([0,1,2]);var ancestors:=PackedInt32Array([0]);var areas:=PackedFloat64Array([detail.area]);var support=load("res://scripts/membrane_support.gd")
 var accepted:Dictionary=support.build(original,ids,published,ids,ancestors,areas,1.,rows)
 check(accepted.valid,"positive original material survives a flipped float32 rest publication")
 var legacy:Dictionary=support.build(original,ids,published,ids,ancestors,areas,1.)
 check(not legacy.valid,"display-only path retains its original geometric rejection")
 var reversed:=rows.duplicate()
 for j in range(3):reversed[3+j]=rows[6+j];reversed[6+j]=rows[3+j]
 var reversed_points:=PackedVector3Array([published[0],published[2],published[1]])
 check(not support.build(original,ids,reversed_points,ids,ancestors,areas,1.,reversed).valid,"negative original material cannot use a positive display orientation and area field to bypass winding")
 var zero:=rows.duplicate()
 for j in range(3):zero[6+j]=zero[3+j]
 check(not support.build(original,ids,published,ids,ancestors,areas,1.,zero).valid,"zero material orientation remains invalid")
 if accepted.valid:
  check(accepted.cells.size()==1 and accepted.cells[0].area==detail.area,"every positive retained area reaches its original mechanical cell")
  for value in accepted.mass:check(value>0. and is_finite(1./value),"tiny positive support remains physically representable")
  var bindings:Array=[]
  for j in range(3):bindings.append({"ids":Vector3i(j,j,j),"weights":Vector3(1,0,0)})
  var cut:={"valid":true,"points":published,"points64":decoded(detail.published_rest_le),"indices":ids,"sources":ancestors,"bindings":bindings,"fractions":PackedFloat64Array([1.])}
  var state:={"rest":published,"previous":published,"anchored":PackedByteArray([0,0,0]),"removed":PackedByteArray([0,0,0]),"outside":PackedByteArray([0,0,0]),"indices":ids,"face_areas":areas}
  var prepared:Dictionary=load("res://scripts/membrane_refinement.gd").prepare(state,cut,rows)
  check(prepared.valid and prepared.face_areas==areas,"physical refinement uses the same positive original material proof instead of rejecting its display rest proxy")
  var display_only:=cut.duplicate(true);display_only.erase("points64")
  check(load("res://scripts/membrane_refinement.gd").prepare(state,cut)==load("res://scripts/membrane_refinement.gd").prepare(state,display_only),"points64 metadata alone cannot change the legacy refinement contract")
  check(not load("res://scripts/membrane_refinement.gd").prepare(state,cut,reversed).valid and not load("res://scripts/membrane_refinement.gd").prepare(state,cut,zero).valid,"physical refinement rejects negative and zero composed material orientation")
  for bad in [cut.merged({"points64":PackedFloat64Array()},true),cut.merged({"fractions":PackedFloat64Array([-1.])},true),cut.merged({"fractions":PackedFloat64Array([.5])},true)]:
   check(not load("res://scripts/membrane_refinement.gd").prepare(state,bad,rows).valid,"physical proof cannot bypass geometry shape, positive fractions or complete material partition")
 var captured:Dictionary=FileAccess.open("res://tests/fixtures/operative-fine-orientation-state.bin",FileAccess.READ).get_var();var model=load("res://scripts/embedded_membrane.gd").new();model._state=captured.state.duplicate(true);var before:Dictionary=model.snapshot()
 var result:Dictionary=model._incise_one(captured.patch)
 check(result.valid and result.changed,"exact177-step290-event physical incision clears flipped display rest orientation: "+result.reason)
 if result.valid:
  var after:Dictionary=model.snapshot();var old_area:=0.;var new_area:=0.
  for area in before.areas:old_area+=area
  for area in after.areas:check(area>0.,"owned cut retains every positive fragment");new_area+=area
  check(absf(old_area-new_area)<1e-10 and after.rest.size()<=4096 and after.indices.size()/3<=8192,"owned cut preserves material and original geometry budgets")
  check(after.steps==before.steps and after.time==before.time and after.events==before.events+1,"incision changes only its geometry event, not accepted physics time/history")
  var followup:Dictionary=model._incise_one(PackedVector3Array([Vector3(2,2,2),Vector3(2.1,2,2),Vector3(2,2.1,2)]))
  check(followup.valid and not followup.changed and model.snapshot()==after,"accepted sliver remains usable physical input after display publication")
  DirAccess.make_dir_recursive_absolute("res://reports")
  var f:=FileAccess.open("res://reports/material-orientation.json",FileAccess.WRITE)
  f.store_string(JSON.stringify({"scope":"Owned177-step290-event incision only; not full route, real-time or surgical completion.","passed":failures==0,"before_vertices":before.rest.size(),"after_vertices":after.rest.size(),"before_events":before.events,"after_events":after.events,"physical_steps":after.steps,"triangles":after.indices.size()/3,"area_error":new_area-old_area,"positive_sliver_area":detail.area,"material_determinant":detail.predicate.value},"  ",true,true))
 print("Original material orientation: ",failures," failures");quit(1 if failures else 0)
