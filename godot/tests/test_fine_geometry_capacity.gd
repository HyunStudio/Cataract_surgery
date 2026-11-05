extends SceneTree
var failures:=0
func check(ok:bool,message:String)->void:
	if not ok:failures+=1;push_error(message)
class FineGuard extends RefCounted:
	func guard_fine_motion(_r:Dictionary)->Dictionary:return {}
class LegacyGuard extends RefCounted:
	func guard_motion(_r:Dictionary)->Dictionary:return {}
func _initialize()->void:
	var tissue=load("res://scripts/embedded_membrane.gd").new()
	check(tissue.has_method("set_fine_geometry_capacity"),"fine geometry must negotiate a separate owned capacity")
	if failures:quit(1);return
	var saved:Dictionary=FileAccess.open("res://tests/fixtures/operative-cut299-vertex-state.bin",FileAccess.READ).get_var()
	tissue._state=saved.state.duplicate(true);var before:Dictionary=tissue.snapshot()
	check(not tissue.set_fine_geometry_capacity(8192,LegacyGuard.new()).valid and tissue.snapshot()==before,"legacy guard cannot authorize larger fine geometry")
	check(not tissue.set_fine_geometry_capacity(16384,FineGuard.new()).valid and tissue.snapshot()==before,"fine capacity remains explicitly bounded")
	var old:Dictionary=tissue._incise_one(saved.patch)
	check(not old.valid and old.reason=="vertex_budget" and tissue.snapshot()==before,"default legacy cut retains its original atomic limit")
	check(tissue.set_fine_geometry_capacity(8192,FineGuard.new()).valid,"extended geometry capability can be selected without physics changes")
	var enabled:Dictionary=tissue.snapshot()
	check(enabled.xyz==before.xyz and enabled.previous==before.previous and enabled.steps==before.steps and enabled.time==before.time,"capacity negotiation changes no mechanical state or clock")
	var result:Dictionary=tissue._incise_one(saved.patch)
	check(result.valid and result.changed,"owned cut299 preserves detail beyond legacy fine-point capacity: "+str(result.get("reason")))
	if result.valid:
		var after:Dictionary=tissue.snapshot();var old_area:=0.;var new_area:=0.;var old_mass:=0.;var new_mass:=0.
		for value in before.areas:old_area+=value
		for value in after.areas:new_area+=value;check(value>0.,"every retained material face remains positive")
		for value in before.support.mass:old_mass+=value
		for value in after.support.mass:new_mass+=value;check(value>0.,"positive fragment inertia is retained")
		check(after.rest.size()>4096 and after.rest.size()<=8192 and after.indices.size()/3<=8192 and after.support.controls.size()<=4096,"fine geometry and mechanical DOFs have independent bounded counts")
		check(absf(old_area-new_area)<1e-10 and absf(old_mass-new_mass)<1e-10,"larger geometry retains original area and mass")
		check(after.events==before.events+1 and after.steps==before.steps and after.time==before.time,"one cut event changes no physical history clock")
		var current:Dictionary=tissue.snapshot()
		check(not tissue.set_fine_geometry_capacity(4096,LegacyGuard.new()).valid and tissue.snapshot()==current,"an existing large geometry cannot be silently downgraded")
	print("Fine geometry capacity: ",failures," failures");quit(1 if failures else 0)

