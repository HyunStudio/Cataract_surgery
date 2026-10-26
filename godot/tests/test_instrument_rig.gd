extends SceneTree
var failures := 0
func check(ok: bool, message: String) -> void:
	if not ok:
		failures += 1
		push_error(message)
func _initialize() -> void:
	var source = load("res://scripts/instrument_rig.gd")
	if source == null:
		push_error("constrained instrument rig missing")
		quit(1)
		return
	var rig = source.new()
	rig.aim_at(Vector3(0,.8,.2))
	rig.set_insertion(1.3)
	check(absf(rig.tip.distance_to(rig.portal)-1.3)<.00001,"insertion is measured from incision pivot")
	check((rig.tip-rig.portal).cross(rig.axis).length()<.00001,"shaft passes exactly through incision")
	var before: Vector3 = rig.tip
	rig.aim_at(Vector3(NAN,0,0))
	check(rig.tip == before,"nonfinite pointer cannot move instrument")
	rig.set_insertion(100.)
	check(rig.insertion <= 2.7,"insertion limit enforced")
	rig.adjust_pitch(.3)
	check(absf((rig.tip-rig.portal).length()-rig.insertion)<.00001,"pitch preserves insertion constraint")
	check(rig.tip.is_finite(),"finite tool pose")
	print("Instrument rig tests: ",failures," failures")
	quit(1 if failures else 0)
