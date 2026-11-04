extends SceneTree
var failures:=0
func check(ok:bool,message:String)->void:
	if not ok:failures+=1;push_error(message)
func _initialize()->void:
	check(ClassDB.class_exists("MembraneFEMKernel"),"exact tiny-support dynamics requires the actual native kernel")
	if failures:quit(1);return
	var saved:Dictionary=FileAccess.open("res://tests/fixtures/operative-embedded-mass.bin",FileAccess.READ).get_var()
	var model=load("res://scripts/embedded_membrane.gd").new();model._state=saved.state.duplicate(true)
	var cut:Dictionary=model.incise_patches([saved.patch])
	check(cut.valid and cut.changed,"exact operative tiny-support cut commits without material substitution")
	if not cut.valid:quit(1);return
	var before:Dictionary=model.snapshot();var force:=PackedFloat64Array();force.resize(before.xyz.size())
	var result:Dictionary=model.advance(1./60.,force,ClassDB.instantiate("MembraneFEMKernel"),10000.,15000.,.98,250)
	check(result.valid,"actual native implicit step for the exact operative microfragment: "+result.reason)
	if result.valid:
		var after:Dictionary=model.snapshot()
		check(after.steps==before.steps+1 and after.support==before.support,"native tick preserves the original tiny support and advances only dynamics")
		check(result.force_inf<=1e-8 and result.stats[5]<=1e-5,"exact native candidate passes independent force and linear residual gates")
		print("Operative tiny-support native evidence: ",JSON.stringify({"force_inf":result.force_inf,"stats":result.stats,"minimum_mass":after.support.minimum_mass,"controls":after.support.controls.size()},"",true,true))
	print("Operative resolution native: ",failures," failures");quit(1 if failures else 0)
