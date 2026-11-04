extends SceneTree
var failures:=0
func check(ok:bool,message:String)->void:
	if not ok:failures+=1;push_error(message)
func _initialize()->void:
	var saved:Dictionary=FileAccess.open("res://tests/fixtures/operative-embedded-mass.bin",FileAccess.READ).get_var()
	var model=load("res://scripts/embedded_membrane.gd").new();model._state=saved.state.duplicate(true)
	var before:Dictionary=model.snapshot();var result:Dictionary=model.incise_patches([saved.patch])
	check(not result.valid and result.reason=="embedded_mass_resolution","exact operative state retains the unresolved native mass-envelope rejection")
	check(model.snapshot()==before,"rejected staged original-material incision cannot change accepted mechanics")
	if not result.valid:
		check(result.get("minimum_mass",0.)>0. and result.get("minimum_mass",1.)<1e-12 and result.get("inverse_mass",0.)>1e12,"failure reports a finite positive original support mass beyond the existing native envelope")
	var cut:Dictionary=model._cutter.slice_triangle(model.positions(),before.indices,saved.patch[0],saved.patch[1],saved.patch[2],4096,8192,true)
	check(cut.valid,"mass failure is distinct from geometric or affine-material cut rejection")
	if cut.valid:
		var refinement=load("res://scripts/membrane_refinement.gd")
		var prepared:Dictionary=refinement.prepare({"rest":before.rest,"previous":model.positions(),"anchored":before.anchored,"removed":before.removed,"outside":before.outside,"indices":before.indices,"face_areas":before.areas},cut)
		check(prepared.valid,"candidate retains material preparation before mechanical policy")
		if prepared.valid:
			var ancestors:=PackedInt32Array()
			for source in cut.sources:ancestors.append(before.ancestors[source])
			var weights:Dictionary=model._cut_material_weights(cut)
			var support:Dictionary=load("res://scripts/membrane_support.gd").build(before.original,before.original_indices,prepared.rest,cut.indices,ancestors,prepared.face_areas,before.density,weights.weights)
			check(support.valid,"tiny control has valid positive retained support rather than a missing or zero-mass node")
			if support.valid:
				var total:=0.;var original:=0.;var node:int=support.mass.find(support.minimum_mass);var affected:=0.;var count:=0
				for mass in support.mass:total+=mass
				for mass in before.support.mass:original+=mass
				for face in range(cut.sources.size()):
					for j in range(3):
						if support.elements[face*3+j]==node:affected+=prepared.face_areas[face];count+=1;break
				check(absf(total-original)<1e-12,"candidate conserves total mass without floors removal or welding")
				print("Operative resolution evidence: ",JSON.stringify({"minimum_mass":support.minimum_mass,"inverse_mass":1./support.minimum_mass,"controls":support.controls.size(),"total_mass":total,"mass_difference":total-original,"minimum_control_faces":count,"minimum_control_material_area":affected,"accepted_ticks":before.steps,"accepted_events":before.events},"",true,true))
	print("Operative resolution fixture: ",failures," failures");quit(1 if failures else 0)
