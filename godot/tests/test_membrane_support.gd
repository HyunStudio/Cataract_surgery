extends SceneTree
var failures:=0
func check(ok:bool,message:String)->void:
	if not ok:failures+=1;push_error(message)
func total(values:PackedFloat64Array)->float:
	var result:=0.
	for value in values:result+=value
	return result
func areas(points:PackedVector3Array,indices:PackedInt32Array)->PackedFloat64Array:
	var result:=PackedFloat64Array()
	for off in range(0,indices.size(),3):result.append((points[indices[off+1]]-points[indices[off]]).cross(points[indices[off+2]]-points[indices[off]]).length()*.5)
	return result
func exercise(support,base:PackedVector3Array,original:PackedInt32Array,points:PackedVector3Array,indices:PackedInt32Array,parents:PackedInt32Array,material_area:PackedFloat64Array)->Dictionary:
	var result:Dictionary=support.build(base,original,points,indices,parents,material_area,2.)
	check(result.valid,"embedded material supports build: "+result.reason)
	if not result.valid:return result
	check(absf(total(result.mass)-2.*total(material_area))<1e-10,"real material mass is preserved without a support mass clamp")
	var rotation:=Basis(Vector3(.2,.7,-.1).normalized(),.67);var offset:=Vector3(.23,-.11,.37)
	for face in range(parents.size()):
		for corner in range(3):
			var reconstructed:=Vector3.ZERO;var moved:=Vector3.ZERO;var sum:=0.
			for j in range(3):
				var weight:float=result.weights[face*9+corner*3+j]
				var control:int=result.controls[result.elements[face*3+j]]
				reconstructed+=base[control]*weight;moved+=(rotation*base[control]+offset)*weight;sum+=weight
			check(absf(sum-1.)<1e-12,"embedded shape functions preserve partition of unity")
			check(reconstructed.distance_to(points[indices[face*3+corner]])<2e-6,"fine material geometry is reconstructed from its original affine basis")
			check(moved.distance_to(rotation*points[indices[face*3+corner]]+offset)<2e-6,"fine geometry follows rigid rotation and translation without a fixed world offset")
	return result
func _initialize()->void:
	check(ResourceLoader.exists("res://scripts/membrane_support.gd"),"embedded membrane support module exists")
	if failures:quit(1);return
	var support=load("res://scripts/membrane_support.gd")
	var base:=PackedVector3Array([Vector3(-1,0,-1),Vector3(1,0,-1),Vector3(1,0,1),Vector3(-1,0,1)])
	var ids:=PackedInt32Array([0,2,1,0,3,2]);var material_area:=areas(base,ids)
	var intact:=exercise(support,base,ids,base,ids,PackedInt32Array([0,1]),material_area)
	if intact.valid:check(intact.controls.size()==4,"uncut neighboring faces share exactly the original four material controls")
	var cut:Dictionary=load("res://scripts/membrane_cut.gd").new().slice(base,ids,Vector3(.25,0,-1.1),Vector3(.25,0,1.1),Vector3.UP,.2)
	check(cut.valid and cut.changed,"fixture produces a full finite material cut")
	if cut.valid:
		var refinement=load("res://scripts/membrane_refinement.gd")
		check(refinement.get_script_method_list().any(func(method):return method.name=="prepare"),"material geometry preparation is available independently of the fine-node inverse-mass gate")
		var refined:=exercise(support,base,ids,cut.points,cut.indices,cut.sources,areas(cut.points,cut.indices))
		if refined.valid:
			check(refined.controls.size()>4,"cut across support stars introduces independent virtual controls")
			var left:={};var right:={}
			for face in range(cut.sources.size()):
				var centroid:Vector3=(cut.points[cut.indices[face*3]]+cut.points[cut.indices[face*3+1]]+cut.points[cut.indices[face*3+2]])/3.
				for j in range(3):
					if centroid.x<.25:left[refined.elements[face*3+j]]=true
					else:right[refined.elements[face*3+j]]=true
			for control in left:check(not right.has(control),"geometrically coincident cut banks never share a material support")
			var first_moment:=Vector3.ZERO
			for i in range(refined.controls.size()):first_moment+=base[refined.controls[i]]*refined.mass[i]
			check(first_moment.length()<2e-6,"integrated virtual control mass preserves the material's first moment")
	var shifted:=base.duplicate();shifted[0]+=Vector3.UP*.01
	var malformed:Dictionary=support.build(base,ids,shifted,ids,PackedInt32Array([0,1]),material_area,1.)
	check(not malformed.valid,"fine geometry off its original material plane rejects instead of silently changing the embedding")
	for parents in [PackedInt32Array([0]),PackedInt32Array([0,2]),PackedInt32Array([-1,1])]:
		check(not support.build(base,ids,base,ids,parents,material_area,1.).valid,"invalid material face ancestry rejects atomically")
	check(not support.build(base,ids,base,ids,PackedInt32Array([0,1]),PackedFloat64Array([2.,-1.]),1.).valid,"negative material mass rejects")
	check(not support.build(base,ids,base,ids,PackedInt32Array([0,1]),material_area,NAN).valid,"nonfinite density rejects")
	var noisy:=base.duplicate();noisy.append(Vector3(1e-7,0,0))
	var split_ids:=PackedInt32Array([0,4,1,4,2,1,0,3,4,4,3,2])
	var consistent:Dictionary=support.build(base,ids,noisy,split_ids,PackedInt32Array([0,0,1,1]),areas(noisy,split_ids),1.)
	check(consistent.valid,"rounded shared coarse-edge material fixture builds")
	if consistent.valid:
		for face in range(4):
			for corner in range(3):
				if split_ids[face*3+corner]!=4:continue
				for j in range(3):
					var control:int=consistent.controls[consistent.elements[face*3+j]]
					check(control in [0,2] or consistent.weights[face*9+corner*3+j]==0.,"shared material edge interpolation cannot acquire an off-edge control through float roundoff")
	# Deliberately characterize the base method's unresolved partial-crack scale.
	# A connected affine support star cannot open a slit wholly within one cell.
	var single:=PackedVector3Array([Vector3.ZERO,Vector3.RIGHT,Vector3.BACK]);var single_ids:=PackedInt32Array([0,2,1])
	var slit:Dictionary=load("res://scripts/membrane_cut.gd").new().slice(single,single_ids,Vector3(.2,0,.2),Vector3(.4,0,.2),Vector3.UP,.1)
	check(slit.valid and slit.changed,"partial interior-slit fixture retains a genuine geometric crack")
	if slit.valid:
		var partial:=exercise(support,single,single_ids,slit.points,slit.indices,slit.sources,areas(slit.points,slit.indices))
		if partial.valid:check(partial.controls.size()==3,"current connected-star basis explicitly requires enrichment or controlled refinement to open a partial interior slit")
	var model=load("res://scripts/capsule_solver.gd").new()
	check(model.has_method("material_support"),"capsule exposes original-material support ancestry through actual geometric incisions")
	if model.has_method("material_support"):
		model.geometry=load("res://scripts/anterior_segment.gd").new();model.reset()
		var source_rest:PackedVector3Array=model.rest_positions.duplicate();var source_indices:PackedInt32Array=model.triangles.duplicate()
		var before:Dictionary=model.material_support()
		check(before.valid and before.controls.size()==source_rest.size(),"actual uncut capsule has its original material basis")
		for patch in [PackedVector3Array([Vector3(-.4,.3,0),Vector3(.4,.3,0),Vector3(0,.8,0)]),PackedVector3Array([Vector3(0,.3,-.4),Vector3(0,.3,.4),Vector3(0,.8,0)])]:
			var incision:Dictionary=model.incise_patches([patch]);check(incision.valid and incision.changed,"lineage test creates sequential real geometric incisions")
			var current:Dictionary=model.material_support()
			check(current.valid,"repeated cut lineage produces valid supports: "+current.reason)
			if current.valid:check(absf(total(current.mass)-model.metrics().retained_area*model.surface_density)<1e-10,"capsule support integration retains the authoritative material mass after repeated cuts")
			check(model._material_rest==source_rest and model._material_indices==source_indices,"original material basis remains immutable through repeated cuts")
		var checkpoint:Dictionary=model._checkpoint();var ancestry:PackedInt32Array=model._material_ids.duplicate()
		model.reset()
		for key in checkpoint:model.set(key,checkpoint[key])
		check(model._material_ids==ancestry and model.material_support().valid,"whole-state restore includes material lineage and original basis")
	print("Embedded membrane support: ",failures," failures");quit(1 if failures else 0)
