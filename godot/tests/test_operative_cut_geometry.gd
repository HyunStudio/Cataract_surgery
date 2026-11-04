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
	# Historical display topology may be oriented after rounding while its
	# affine material triangle is inverted. Preserve the geometric API, but
	# never admit that topology into the original-material mechanical state.
	var thin:Dictionary=FileAccess.open("res://tests/fixtures/blade-continuous-nonmanifold.bin",FileAccess.READ).get_var()
	var strict:Dictionary=cutter.slice_triangle(thin.points,thin.indices,thin.patch[0],thin.patch[1],thin.patch[2],4096,8192,true)
	if strict.valid or strict.reason!="material_subdivision_winding":failures+=1;push_error("material mode rejects inverted affine support even when display geometry is oriented")
	var geometric:Dictionary=cutter.slice_triangle(thin.points,thin.indices,thin.patch[0],thin.patch[1],thin.patch[2])
	if not geometric.valid or not geometric.fractions.is_empty():failures+=1;push_error("explicit material mode cannot leak into the legacy geometry contract")
	print("Operative cut geometry: ",failures," failures")
	quit(1 if failures else 0)
