extends SceneTree
var failures:=0
func check(ok:bool,message:String)->void:
	if not ok:failures+=1;push_error(message)
func _initialize()->void:
	var rig=load("res://scripts/instrument_rig.gd").new()
	check(rig.has_method("adjust_roll"),"operative rig provides axial rotation")
	if failures:quit(1);return
	var point:Vector3=rig.tip;var axis:Vector3=rig.axis
	rig.adjust_roll(PI*.5)
	check(rig.tip==point and rig.axis==axis and absf(rig.roll-PI*.5)<1e-12,"pure axial rotation preserves incision pivot tip and direction")
	var saved:Dictionary=rig.capture_state();rig.adjust_roll(.2);rig.restore_state(saved)
	check(rig.roll==saved.roll,"transaction restores accepted axial orientation")
	rig.adjust_roll(NAN);check(rig.roll==saved.roll,"nonfinite roll intent is ignored")
	var profile=load("res://scripts/instrument_profile.gd")
	var frame:Basis=profile.frame(Vector3.LEFT,PI*.5)
	check(frame.x.is_equal_approx(Vector3.RIGHT) and (frame*Vector3.BACK).is_equal_approx(Vector3.DOWN),"shared frame rotates jaws about the longitudinal tool axis")
	var path=load("res://scripts/instrument_path.gd")
	var body:Array=path.build("forceps",.018,Vector3.ZERO,Vector3.LEFT,false,Vector3.ZERO,Vector3.LEFT,false,false,0.,PI*.5)
	check(body.size()==3 and path.valid(body[0]),"rolled forceps retains valid actual-body packet")
	var middle:Dictionary=path.sample(body[0],.5)
	check(middle.a.distance_to(profile.frame(Vector3.LEFT,PI*.25)*Vector3(0,0,-.025))<1e-7,"jaw midpoint follows the same axial rotation arc")
	var blade=load("res://scripts/blade_sweep.gd")
	var swept:Dictionary=blade.build("knife",Vector3.ZERO,Vector3.LEFT,Vector3.ZERO,Vector3.LEFT,true,0.,PI*.5)
	check(swept.valid and swept.steps>1 and not swept.patches.is_empty(),"stationary-tip knife rotation sweeps its real sharp edges")
	var collision=load("res://scripts/pivot_body_contact.gd").new()
	var portal:=Vector3(1.5,0,0);var tip:=Vector3.ZERO
	var center:Vector3=profile.frame(Vector3.LEFT,PI*.25)*Vector3(.1,0,.034)
	var surface:={"positions":PackedVector3Array([center+Vector3(-.006,-.003,0),center+Vector3(.006,-.003,0),center+Vector3(0,.003,0)]),"triangles":PackedInt32Array([0,1,2]),"revision":1}
	var hit:Dictionary=collision.resolve(portal,tip,Vector3.LEFT,tip,Vector3.LEFT,"forceps",.018,false,{"iris":surface},false,0.,PI*.5)
	for angle in [0.,PI*.5]:
		var static_pose:Dictionary=collision.resolve(portal,tip,Vector3.LEFT,tip,Vector3.LEFT,"forceps",.018,false,{"iris":surface},false,angle,angle)
		check(static_pose.valid and static_pose.fraction==1. and static_pose.contacts.is_empty(),"intermediate obstacle leaves both endpoint jaw poses clear")
	check(hit.valid and hit.fraction<1. and not hit.contacts.is_empty(),"rotating jaw cannot cross an intermediate obstacle despite clear endpoint poses")
	check(absf(hit.roll-hit.fraction*PI*.5)<1e-7,"accepted roll stops at the collision-certified fraction")
	print("Instrument roll: ",failures," failures");quit(1 if failures else 0)
