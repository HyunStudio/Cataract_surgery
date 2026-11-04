extends SceneTree
var failures:=0
class CaptureBackend extends RefCounted:
	var kernel=ClassDB.instantiate("MembraneFEMKernel")
	var request:Dictionary
	var answer:Dictionary
	func solve_fem(value:Dictionary)->Dictionary:
		request=value.duplicate(true);answer=kernel.solve_fem(value);return answer
	func solve_grasp_fem(value:Dictionary)->Dictionary:
		request=value.duplicate(true);answer=kernel.solve_grasp_fem(value);return answer
func check(ok:bool,message:String)->void:
	if not ok:failures+=1;push_error(message)
func serial(value:Dictionary)->Dictionary:
	var result:Dictionary={}
	for key in value:
		var item=value[key]
		result[key]=Array(item) if item is PackedFloat64Array or item is PackedInt32Array else item
	return result
func advance(model,backend,targets:Dictionary)->Dictionary:
	var force:=PackedFloat64Array();force.resize(model.snapshot().xyz.size())
	var result:Dictionary=model.advance(1./60.,force,backend,10000.,15000.,1.,100,targets)
	if not result.valid:
		DirAccess.make_dir_recursive_absolute("res://reports")
		var file:=FileAccess.open("res://reports/grasp-step-failure.json",FileAccess.WRITE)
		if file:file.store_string(JSON.stringify({"request":serial(backend.request),"answer":serial(backend.answer),"step":serial(result)},"",true,true))
		check(false,"actual native attachment step failed: "+str(result))
	return result
func component(state:Dictionary)->Dictionary:
	var adjacent:Dictionary={}
	for off in range(0,state.indices.size(),3):
		for j in range(3):
			var a:int=state.indices[off+j];var b:int=state.indices[off+(j+1)%3]
			if not adjacent.has(a):adjacent[a]=[]
			if not adjacent.has(b):adjacent[b]=[]
			adjacent[a].append(b);adjacent[b].append(a)
	var seen:Dictionary={0:true};var queue:Array=[0]
	while not queue.is_empty():
		for next in adjacent[queue.pop_back()]:
			if not seen.has(next):seen[next]=true;queue.append(next)
	return seen
func _initialize()->void:
	check(ClassDB.class_exists("MembraneFEMKernel"),"real grasp validation requires the actual native FEM extension")
	if failures:quit(1);return
	var backend:=CaptureBackend.new()
	var source=load("res://scripts/capsule_solver.gd").new();source.geometry=load("res://scripts/anterior_segment.gd").new();source.reset()
	var model=load("res://scripts/embedded_membrane.gd").new();model.initialize(source.rest_positions,source.triangles,source.anchored,1.)
	var radius:=.4;var y:float=source.geometry.bag_front(radius);var prior:=Vector3(radius,y,0.)
	for i in range(1,65):
		var next:=Vector3(radius*cos(TAU*i/64.),y,radius*sin(TAU*i/64.));var down:=Vector3.UP*.05
		var cut:Dictionary=model.incise_patches([PackedVector3Array([prior-down,next-down,next+down]),PackedVector3Array([prior-down,next+down,prior+down])])
		check(cut.valid,"retained grasp setup incision %d: %s"%[i,cut.reason])
		if not cut.valid:quit(1);return
		prior=next
	var state:Dictionary=model.snapshot();var free:=component(state);var vertex:=-1
	for point in range(source.positions.size(),state.rest.size()):
		if not free.has(point) or state.support.point_weights[point].size()<2:continue
		var maximum:=0.
		for weight in state.support.point_weights[point]:maximum=maxf(maximum,weight)
		if maximum<.9:vertex=point;break
	check(vertex>=0,"real free flap has an interior-weighted fine point distinct from a mechanical node")
	if failures:quit(1);return
	check(model.grasp(0,vertex).valid,"actual fine material point acquires a source-face-bound attachment")
	var acquired:Dictionary=model.snapshot();var initial:PackedFloat64Array=acquired.grasps[0].target.duplicate()
	var max_force:=0.;var max_gap:=0.;var times:=PackedFloat64Array()
	for i in range(10):
		var target:=initial.duplicate();target[1]+=.005*(i+1)
		var started:=Time.get_ticks_usec();var step:=advance(model,backend,{0:target});times.append((Time.get_ticks_usec()-started)/1000.)
		if not step.valid:quit(1);return
		max_force=maxf(max_force,step.force_inf);max_gap=maxf(max_gap,step.gap)
	var held:Dictionary=model.snapshot();model.release_hand(0);var released:Dictionary=model.snapshot()
	check(released.xyz==held.xyz and released.previous==held.previous and released.time==held.time,"releasing actual moving material keeps accepted velocity and clock")
	if not advance(model,backend,{}).valid:quit(1);return
	check(model.grasp(0,vertex).valid and model.grasp(1,0).valid,"two distinct real material points can acquire independent hand constraints")
	var pair:Dictionary=model.snapshot();var left:PackedFloat64Array=pair.grasps[0].target.duplicate();var right:PackedFloat64Array=pair.grasps[1].target.duplicate()
	for i in range(5):
		var a:=left.duplicate();var b:=right.duplicate();a[1]+=.005*(i+1);b[1]+=.005*(i+1)
		var step:=advance(model,backend,{0:a,1:b})
		if not step.valid:quit(1);return
		max_force=maxf(max_force,step.force_inf);max_gap=maxf(max_gap,step.gap)
	var before:Dictionary=model.snapshot()
	var recut:Dictionary=model.incise_patches([PackedVector3Array([Vector3(-.28,.35,.1),Vector3(-.12,.35,.1),Vector3(-.2,.75,.1)])])
	check(recut.valid and recut.changed and model.snapshot().grasps.size()==2,"a unique two-hand attachment survives a separate incision in already moving material")
	if not recut.valid:print("FAILED_GRASP_RECUT ",recut);quit(1);return
	check(model.snapshot().steps==before.steps and model.snapshot().time==before.time,"recutting held material cannot advance or reset accepted dynamics")
	if not advance(model,backend,{}).valid:quit(1);return
	var final_state:Dictionary=model.snapshot();var total:=0.
	for value in final_state.support.mass:total+=value
	check(absf(total-source.metrics().retained_area)<1e-10,"actual held trajectory preserves all retained material mass")
	DirAccess.make_dir_recursive_absolute("res://reports")
	var file:=FileAccess.open("res://reports/embedded-grasp-metrics.json",FileAccess.WRITE)
	if file:file.store_string(JSON.stringify({"scope":"Actual exact embedded attachments/reactions with direct cut setup, not instrument-body/anatomy contact or mouse full case.","vertex":vertex,"weights":Array(state.support.point_weights[vertex]),"steps":final_state.steps,"clock":final_state.time,"events":final_state.events,"mass":total,"maximum_force":max_force,"maximum_gap":max_gap,"one_hand_step_ms":Array(times)},"",true,true))
	print("Embedded native grasp: ",failures," failures; steps=",final_state.steps," vertex=",vertex," force=",max_force," gap=",max_gap," mass=",total);quit(1 if failures else 0)
