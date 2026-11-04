extends SceneTree
var failures:=0
func check(ok:bool,message:String)->void:
	if not ok:failures+=1;push_error(message)
func total(values:PackedFloat64Array)->float:
	var result:=0.
	for value in values:result+=value
	return result
func _initialize()->void:
	var fixture:Dictionary=FileAccess.open("res://tests/fixtures/blade-material-resolution.bin",FileAccess.READ).get_var()
	var old:Dictionary=fixture.state;var cut:Dictionary=fixture.cut
	var state:={"rest":old.rest_positions,"previous":old._previous,"anchored":old.anchored,"removed":old._removed,"outside":old._outside,"indices":old.triangles,"face_areas":old._triangle_area,"grasps":{},"grasp_faces":{}}
	var before:Dictionary=state.duplicate(true)
	var refinement=load("res://scripts/membrane_refinement.gd")
	var transferred:Dictionary=refinement.transfer(state,cut,old.surface_density)
	check(not transferred.valid and transferred.reason=="mass_resolution","frozen real blade motion still reproduces the unmodified fine-node mechanical rejection")
	var prepared:Dictionary=refinement.prepare(state,cut)
	check(prepared.valid,"rejected fine-node mechanical state has valid retained geometry and material transfer")
	if not prepared.valid:quit(1);return
	var ancestors:=PackedInt32Array()
	for source in cut.sources:ancestors.append(old._material_ids[source])
	var support:Dictionary=load("res://scripts/membrane_support.gd").build(old._material_rest,old._material_indices,prepared.rest,cut.indices,ancestors,prepared.face_areas,old.surface_density)
	check(support.valid,"frozen blade cut admits an original-material support basis: "+support.reason)
	if support.valid:
		var fine_min:=INF
		for area in prepared.lumped:
			if area>0.:fine_min=minf(fine_min,area*old.surface_density)
		check(fine_min<1e-12 and support.minimum_mass>1e-12,"attached cut slivers are embedded without unresolved independent mechanical masses")
		check(absf(total(support.mass)-total(old._triangle_area)*old.surface_density)<1e-10,"embedded original supports retain every accepted material area and total mass")
		print("Frozen blade support: ",JSON.stringify({"fine_vertices":prepared.rest.size(),"fine_triangles":cut.indices.size()/3,"fine_minimum_mass":fine_min,"virtual_controls":support.controls.size(),"support_minimum_mass":support.minimum_mass,"mass":total(support.mass)},"",true,true))
	check(state==before,"support preparation never mutates or bypasses the rejected physical state")
	print("Embedded failure fixture: ",failures," failures");quit(1 if failures else 0)
