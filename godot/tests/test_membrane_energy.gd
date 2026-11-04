extends SceneTree
var failures:=0
func check(ok:bool,message:String)->void:
	if not ok:failures+=1;push_error(message)
func maximum(values:PackedFloat64Array)->float:
	var result:=0.
	for value in values:result=maxf(result,absf(value))
	return result
func coordinates(base:PackedVector3Array,controls:PackedInt32Array)->PackedFloat64Array:
	var result:=PackedFloat64Array()
	for control in controls:
		for j in range(3):result.append(base[control][j])
	return result
func _initialize()->void:
	check(ResourceLoader.exists("res://scripts/membrane_energy.gd"),"embedded membrane energy module exists")
	if failures:quit(1);return
	var energy=load("res://scripts/membrane_energy.gd").new()
	var base:=PackedVector3Array([Vector3(-1,0,-1),Vector3(1,0,-1),Vector3(1,0,1),Vector3(-1,0,1)])
	var ids:=PackedInt32Array([0,2,1,0,3,2])
	var support:Dictionary=load("res://scripts/membrane_support.gd").build(base,ids,base,ids,PackedInt32Array([0,1]),PackedFloat64Array([2.,2.]),1.)
	check(energy.configure(base,ids,support),"original material cells configure the elastic energy")
	var rest:=coordinates(base,support.controls)
	var initial:Dictionary=energy.evaluate(rest,2.,3.)
	check(initial.valid and absf(initial.energy)<1e-12 and maximum(initial.gradient)<1e-12,"undeformed original material is stress free")
	var deformed:=rest.duplicate()
	for node in range(support.controls.size()):
		deformed[node*3]=1.1*rest[node*3]+.07*rest[node*3+2]
		deformed[node*3+1]=.08*rest[node*3]*rest[node*3+2]
		deformed[node*3+2]=.94*rest[node*3+2]
	var result:Dictionary=energy.evaluate(deformed,2.,3.)
	check(result.valid and result.energy>0.,"nonrigid membrane deformation carries positive material energy")
	for i in range(deformed.size()):
		var plus:=deformed.duplicate();var minus:=deformed.duplicate();var h:=1e-6
		plus[i]+=h;minus[i]-=h
		var difference:float=(energy.evaluate(plus,2.,3.).energy-energy.evaluate(minus,2.,3.).energy)/(2.*h)
		check(absf(difference-result.gradient[i])<1e-7,"analytic membrane energy gradient agrees with independent coordinate differences")
	var angle:=.63;var rotated:=deformed.duplicate()
	for node in range(support.controls.size()):
		rotated[node*3]=cos(angle)*deformed[node*3]+sin(angle)*deformed[node*3+2]+.3
		rotated[node*3+1]=deformed[node*3+1]-.2
		rotated[node*3+2]=-sin(angle)*deformed[node*3]+cos(angle)*deformed[node*3+2]+.1
	var objective:Dictionary=energy.evaluate(rotated,2.,3.)
	check(objective.valid and absf(objective.energy-result.energy)<1e-12,"material energy is invariant under a superposed rigid motion")
	for node in range(support.controls.size()):
		check(absf(objective.gradient[node*3]-(cos(angle)*result.gradient[node*3]+sin(angle)*result.gradient[node*3+2]))<1e-12,"membrane forces rotate with the deformed material")
	var collapsed:=rest.duplicate()
	for i in range(collapsed.size()):collapsed[i]=0.
	check(not energy.evaluate(collapsed,2.,3.).valid,"collapsed membrane rejects instead of publishing a nonfinite barrier gradient")
	check(not energy.evaluate(rest,NAN,3.).valid and not energy.evaluate(rest,2.,-1.).valid,"invalid constitutive parameters reject")
	var cut:Dictionary=load("res://scripts/membrane_cut.gd").new().slice(base,ids,Vector3(.25,0,-1.1),Vector3(.25,0,1.1),Vector3.UP,.2)
	var areas:=PackedFloat64Array()
	for off in range(0,cut.indices.size(),3):areas.append((cut.points[cut.indices[off+1]]-cut.points[cut.indices[off]]).cross(cut.points[cut.indices[off+2]]-cut.points[cut.indices[off]]).length()*.5)
	var split:Dictionary=load("res://scripts/membrane_support.gd").build(base,ids,cut.points,cut.indices,cut.sources,areas,1.)
	check(energy.configure(base,ids,split),"elastic integration uses actual retained cut-cell area")
	var separated:=coordinates(base,split.controls)
	var right:={}
	for face in range(cut.sources.size()):
		var x:float=(cut.points[cut.indices[face*3]].x+cut.points[cut.indices[face*3+1]].x+cut.points[cut.indices[face*3+2]].x)/3.
		if x>.25:
			for j in range(3):right[split.elements[face*3+j]]=true
	for node in right:separated[node*3+1]+=.2
	var independent:Dictionary=energy.evaluate(separated,2.,3.)
	check(independent.valid and absf(independent.energy)<1e-12 and maximum(independent.gradient)<1e-12,"severed banks move independently without a hidden elastic tether")
	print("Embedded membrane energy: ",failures," failures");quit(1 if failures else 0)
