extends SceneTree
func _initialize()->void:
	var fixture:Dictionary=FileAccess.open("res://tests/fixtures/operative-blade-area.bin",FileAccess.READ).get_var()
	var cutter=load("res://scripts/membrane_cut.gd").new();var patch:PackedVector3Array=fixture.patch
	var result:Dictionary=cutter.slice_triangle(fixture.points,fixture.indices,patch[0],patch[1],patch[2],4096,8192,true)
	if not result.valid:push_error("actual operative blade subdivision preserves all source area: "+result.reason)
	var failures:=0 if result.valid else 1
	if result.valid:
		var sums:=PackedFloat64Array();sums.resize(fixture.indices.size()/3)
		for i in range(result.sources.size()):sums[result.sources[i]]+=result.fractions[i]
		for value in sums:
			if absf(value-1.)>1e-10:failures+=1;push_error("each source material triangle is partitioned without missing or duplicate area")
	# This historical thin case used to invert its affine midpoint triangle.
	# Canonical midpoint bindings must now preserve its strict partition too.
	var thin:Dictionary=FileAccess.open("res://tests/fixtures/blade-continuous-nonmanifold.bin",FileAccess.READ).get_var()
	var strict:Dictionary=cutter.slice_triangle(thin.points,thin.indices,thin.patch[0],thin.patch[1],thin.patch[2],4096,8192,true)
	if not strict.valid:failures+=1;push_error("thin historical geometry retains positive affine support: "+strict.reason)
	else:
		var partition:=PackedFloat64Array();partition.resize(thin.indices.size()/3)
		for i in range(strict.sources.size()):
			if strict.fractions[i]<=0.:failures+=1;push_error("thin material triangles retain positive orientation")
			partition[strict.sources[i]]+=strict.fractions[i]
		for portion in partition:
			if absf(portion-1.)>1e-10:failures+=1;push_error("thin material partition remains complete")
	var geometric:Dictionary=cutter.slice_triangle(thin.points,thin.indices,thin.patch[0],thin.patch[1],thin.patch[2])
	if not geometric.valid or not geometric.fractions.is_empty():failures+=1;push_error("explicit material mode cannot leak into the legacy geometry contract")
	var tiny:Dictionary=FileAccess.open("res://tests/fixtures/operative-blade-degenerate.bin",FileAccess.READ).get_var()
	var model=load("res://scripts/embedded_membrane.gd").new();model._state=tiny.state
	var continued:Dictionary=cutter.slice_triangle(model.positions(),tiny.state.indices,tiny.patch[0],tiny.patch[1],tiny.patch[2],4096,8192,true)
	if not continued.valid:failures+=1;push_error("positive retained output faces remain admissible on the next material incision: "+continued.reason)
	var material:Dictionary=model.incise_patches([tiny.patch])
	if not material.valid:failures+=1;push_error("exact next operative incision retains its original material and history: "+material.reason)
	var collapsed:Dictionary=cutter.slice_triangle(PackedVector3Array([Vector3.ZERO,Vector3.RIGHT,Vector3.RIGHT*2.]),PackedInt32Array([0,1,2]),tiny.patch[0],tiny.patch[1],tiny.patch[2],4096,8192,true)
	if collapsed.valid or collapsed.reason!="degenerate_face":failures+=1;push_error("material mode still rejects truly collapsed source geometry")
	print("Operative cut geometry: ",failures," failures")
	quit(1 if failures else 0)
