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
	check(rig.has_method("place_tip"),"rig supports a tip moving outside the incision pivot during extraction")
	if rig.has_method("place_tip"):
		rig.allow_withdrawal=true
		var exterior:Vector3=rig.portal+Vector3(.6,.4,0)
		rig.place_tip(exterior)
		check(rig.insertion<0. and rig.tip.distance_to(exterior)<.0001,"signed withdrawal moves the actual tip outside without reversing the shaft")
	rig.axis=Vector3.LEFT
	var close_tip:Vector3=rig.portal+Vector3(-.02,.02,0)
	rig.place_tip(close_tip)
	check(rig.tip.distance_to(close_tip)<.00001,"near-pivot correction preserves oblique contact position")
	check(rig.has_method("advance_toward"),"signed pointer motion has a continuous pivot-crossing path")
	if rig.has_method("advance_toward"):
		rig.axis=Vector3(-1,-.1,.5).normalized(); rig.insertion=-.2
		var target:=Vector3(1.32,.95,-.25)
		var crossed:=false
		for i in range(150):
			var old_tip:Vector3=rig.tip; var old_insertion:float=rig.insertion
			rig.advance_toward(target,.025)
			check(rig.tip.distance_to(old_tip)<=.02501,"each continuous step respects tip speed bound")
			check((rig.tip-rig.portal).cross(rig.axis).length()<.00001,"continuous path preserves pivot constraint")
			if old_insertion<0. and rig.insertion>=0.: crossed=true; check(rig.tip.distance_to(rig.portal)<.00001,"crossing between outside and inside passes through the portal")
		check(crossed and rig.tip.distance_to(target)<.0001,"oblique inside target reaches after withdrawal through portal")
		var exterior_target:Vector3=rig.portal+Vector3(.3,.1,.3)
		for i in range(150): rig.advance_toward(exterior_target,.025)
		check(rig.tip.distance_to(exterior_target)<.0001 and rig.insertion<0.,"continuous return withdraws before changing exterior aim")
		var stable:Vector3=rig.tip
		rig.advance_toward(Vector3(NAN,0,0),.025); rig.advance_toward(target,NAN)
		check(rig.tip==stable,"invalid continuous request cannot alter pose")
	print("Instrument rig tests: ",failures," failures")
	quit(1 if failures else 0)
