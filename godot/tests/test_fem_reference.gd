extends SceneTree
var failures:=0
func check(ok:bool,message:String)->void:
	if not ok:failures+=1;push_error(message)
func _initialize()->void:
	var model=load("res://scripts/capsule_solver.gd").new();model.geometry=load("res://scripts/anterior_segment.gd").new();model.reset()
	var cut:Dictionary=model.incise_patches([PackedVector3Array([Vector3(-.4,.3,0),Vector3(.4,.3,0),Vector3(0,.8,0)])])
	check(cut.valid and cut.changed,"native reference specimen contains a real retained curved cut")
	var support:Dictionary=model.material_support()
	check(support.valid,"native reference specimen has a valid original-material support basis")
	var energy=load("res://scripts/membrane_energy.gd").new()
	check(energy.configure(model._material_rest,model._material_indices,support),"independent Godot membrane energy configures")
	if failures:quit(1);return
	var xyz:=PackedFloat64Array();var rest:=PackedFloat64Array();var fixed:=PackedByteArray()
	for id in support.controls:
		var p:Vector3=model._material_rest[id]
		rest.append_array(PackedFloat64Array([p.x,p.y,p.z]))
		xyz.append_array(PackedFloat64Array([1.03*p.x+.01*p.z,.98*p.y+.02*p.x*p.z,.97*p.z]))
		fixed.append(model.anchored[id])
	var evaluated:Dictionary=energy.evaluate(xyz,2.,3.)
	check(evaluated.valid,"independent deformed curved reference energy evaluates")
	var cells:Array=[]
	for cell in energy._cells:
		var gradients:Array=Array(cell.gx);gradients.append_array(Array(cell.gy))
		cells.append({"nodes":[cell.nodes.x,cell.nodes.y,cell.nodes.z],"gradients":gradients,"area":cell.area})
	var hashes:Dictionary={}
	for file in ["res://scripts/membrane_energy.gd","res://scripts/membrane_support.gd","res://scripts/capsule_solver.gd","res://scripts/anterior_segment.gd","res://scripts/membrane_precision.gd","res://scripts/membrane_cut.gd","res://scripts/membrane_refinement.gd","res://tests/test_fem_reference.gd"]:hashes[file]=FileAccess.get_sha256(file)
	DirAccess.make_dir_recursive_absolute("res://reports")
	var output:=FileAccess.open("res://reports/fem-reference.json",FileAccess.WRITE)
	check(output!=null,"reference fixture can be saved")
	if output:output.store_string(JSON.stringify({"scope":"Synthetic retained curved capsule; independent Godot reference, no clinical calibration or full-operation claim.","engine":Engine.get_version_info().string,"sources":hashes,"mu":2.,"lambda":3.,"xyz":xyz,"rest":rest,"mass":support.mass,"fixed":Array(fixed),"cells":cells,"energy":evaluated.energy,"gradient":evaluated.gradient},"",true,true))
	print("FEM Godot reference: ",failures," failures; controls=",support.controls.size()," cells=",cells.size());quit(1 if failures else 0)
