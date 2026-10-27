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
	check(path.sample(jaws[0],1.).a.is_equal_approx(Vector3(0,0,-.00875)),"closing jaw path reaches shared rendered endpoint")
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
