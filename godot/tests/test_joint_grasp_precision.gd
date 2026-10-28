extends SceneTree
## Kinematic-only contract: all coordinates become prescribed on acquisition.
var failures:=0
class PrescribedKernel extends RefCounted:
	var request:Dictionary={}
	func solve_contact(value:Dictionary)->Dictionary:
		request=value.duplicate(true)
		return {"status":0,"xyz":value.initial.duplicate(),"stats":PackedFloat64Array([0,0,0,0,0,0,0,0,0,0,0,0])}
func check(ok:bool,message:String)->void:
	if not ok: failures+=1; push_error(message)
func _initialize()->void:
	var model=load("res://scripts/capsule_solver.gd").new()
	model.anchored.fill(1); model.anchored[0]=0
	var kernel:=PrescribedKernel.new(); model.set_contact_backend(kernel)
	var base:float=model.positions[0].y
	var target:float=base+pow(2.,floor(log(absf(base))/log(2.))-52.)
	model._physical_xyz[1]=target; model._physical_previous[1]=target
	var tip:Vector3=model.positions[0]+Vector3(0,.025,0)
	var path=load("res://scripts/instrument_path.gd")
	var body:Array=path.build("forceps",.018,tip,Vector3.LEFT,true,tip,Vector3.LEFT,true,false)
	var tools:Array[Dictionary]=[{"hand":0,"tip":tip,"radius":.065,"contact_radius":.018,"grip":true,"cut":false,"body":body}]
	model.step_tools(1./120.,tools)
	check(model.native_failure.is_empty() and model.metrics().grasped==0,"stationary physical attachment accepts")
	check(not kernel.request.is_empty() and kernel.request.predicted[1]==target,"zero proxy displacement must not round the prescribed double coordinate")
	check(model._physical_xyz[1]==target and model._physical_previous[1]==target,"stationary attachment retains position and history bit for bit")
	print("Joint grasp precision: ",failures," failures")
	quit(1 if failures else 0)
