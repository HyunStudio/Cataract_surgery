extends "res://tests/test_blade_closed.gd"
class CaptureState:
	extends "res://scripts/embedded_membrane.gd"
	func _incise_one(patch:PackedVector3Array)->Dictionary:
		var before:=snapshot();var result:=super._incise_one(patch)
		if not result.valid:
			DirAccess.make_dir_recursive_absolute("res://reports")
			var file:=FileAccess.open("res://reports/operative-embedded-first-failure.bin",FileAccess.WRITE)
			if file:file.store_var({"state":before,"patch":patch,"result":result})
		return result
## Exact same operative route and physical tick, actual native material basis.
func configure_capsule(app)->bool:
	check(ClassDB.class_exists("MembraneFEMKernel") and ClassDB.class_exists("MembraneContactKernel"),"operative retained blade test requires both actual native kernels")
	if failures:return false
	var backend=ClassDB.instantiate("MembraneFEMKernel");var guard=ClassDB.instantiate("MembraneContactKernel")
	check(app.capsule.set_embedded_backend(backend,guard),"real operative capsule switches at pristine rest only")
	if failures==0:app.capsule._embedded_solver=CaptureState.new()
	return failures==0
