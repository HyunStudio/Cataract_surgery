extends SceneTree
var failures:=0
func check(ok:bool,message:String)->void:
	if not ok: failures+=1; push_error(message)
func _initialize()->void:
	var path=load("res://scripts/instrument_path.gd")
	if path==null: check(false,"instrument pose path exists"); quit(1); return
	var body:Array=path.build("phaco",.055,Vector3.ZERO,Vector3.LEFT,false,Vector3.ZERO,Vector3.RIGHT,false,false)
	check(body.size()==3,"actual working tip, shaft and sleeve generate paths")
	var shaft:Dictionary=body[1]
	var middle:Dictionary=path.sample(shaft,.5)
	check(absf(middle.b.length()-3.05)<.00001 and middle.b.distance_to(Vector3.ZERO)>3.,"half-turn follows full shaft arc instead of collapsed chord")
	check(path.steps(body)>=32,"large rotations get bounded angular substeps")
	var knives:Array=path.build("knife",.018,Vector3.ZERO,Vector3.LEFT,false,Vector3.ZERO,Vector3.LEFT,false,true)
	check(knives.size()==1 and knives[0].part=="shaft","active cutting exempts blade contact only, never shaft")
	var jaws:Array=path.build("forceps",.018,Vector3.ZERO,Vector3.LEFT,false,Vector3.ZERO,Vector3.LEFT,true,false)
	check(path.sample(jaws[0],1.).a.is_equal_approx(Vector3(0,0,-.010)),"closing jaw path reaches shared rendered endpoint")
	var rotating:Array=path.build("forceps",.018,Vector3.ZERO,Vector3.LEFT,true,Vector3.ZERO,Vector3(-1,.03,0).normalized(),true,false)
	var interval:Dictionary=path.interval(rotating[0],0.,.5)
	var motion:Dictionary=path.motion_request(PackedFloat64Array([0,0,0]),PackedFloat64Array([0,0,0]),PackedInt32Array(),[interval])
	check(motion.kinds==PackedInt32Array([1]) and motion.packets.size()==41 and motion.packets[39]==0. and motion.packets[40]==.5,"native packet retains original pose subinterval instead of replaying full motion")
	check(motion.packets[12]==.010 and motion.packets[0]==interval.previous_a.x and motion.packets[6]==interval.a.x,"native motion retains physical thickness and recorded endpoint axes")
	check(interval.get("physical_radius",INF)==.010,"rotation preserves the actual rendered jaw thickness")
	check(interval.radius>.010 and interval.get("sweep_padding",0.)>0. and absf(interval.radius-interval.get("physical_radius",INF)-interval.get("sweep_padding",0.))<1e-15,"angular enclosure padding remains explicit for swept checks")
	check(not path.valid(interval.merged({"physical_radius":interval.radius+.001},true)),"physical body cannot exceed its swept enclosure")
	for malformed in [{"physical_radius":.01,"radius":"bad"},{"physical_radius":NAN,"radius":.02},{"physical_radius":-.01,"radius":.02},{"sweep_padding":-1.},{"physical_radius":.01,"radius":INF}]:
		check(path.valid(malformed)==false,"malformed physical/enclosure metadata rejects explicitly")
	var enclosed:Dictionary={"a":Vector3.ZERO,"b":Vector3.RIGHT,"previous_a":Vector3.ZERO,"previous_b":Vector3.RIGHT,"radius":.03,"physical_radius":.01,"sweep_padding":.02}
	var retained:Dictionary=path.interval(enclosed,0.,.5)
	check(path.valid(enclosed) and retained.radius==enclosed.radius and retained.physical_radius==.01 and retained.sweep_padding>0.,"explicit chord-only enclosure is retained instead of losing caller padding")
	check(path.build("phaco",.055,Vector3.ZERO,Vector3.ZERO,false,Vector3.ZERO,Vector3.LEFT,false,false).is_empty(),"invalid prior axis rejects path")
	var cap=load("res://scripts/capsule_solver.gd").new()
	cap.stretch_compliance=1e303
	var original:Dictionary=cap.visual_state()
	var tools:Array[Dictionary]=[{"hand":0,"tip":Vector3.ZERO,"radius":.055,"grip":false,"cut":false,"body":body}]
	cap.step_tools(.01,tools)
	check(cap.visual_state()==original and cap.metrics().integration_steps==0,"angular substep compliance overflow rejects atomically")
	cap.stretch_compliance=.000005
	tools[0].body=path.build("cannula",.3,Vector3.ZERO,Vector3.LEFT,false,Vector3.ZERO,Vector3.RIGHT,false,false)
	cap.step_tools(.01,tools)
	check(cap.visual_state()==original and cap.metrics().integration_steps==0,"unsupported interval inflation rejects before changing tissue")
	print("Instrument path: ",failures," failures"); quit(1 if failures else 0)
