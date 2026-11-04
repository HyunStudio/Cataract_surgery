extends SceneTree
var failures:=0
class RecordingCutter extends RefCounted:
	var inner=load("res://scripts/membrane_cut.gd").new()
	func slice_triangle(points,indices,a,b,c,max_vertices=4096,max_triangles=8192,material_partition=false)->Dictionary:
		var result:Dictionary=inner.slice_triangle(points,indices,a,b,c,max_vertices,max_triangles,material_partition)
		if not result.valid:
			DirAccess.make_dir_recursive_absolute("res://reports")
			var file:=FileAccess.open("res://reports/embedded-curved-cut-failure.bin",FileAccess.WRITE)
			if file:file.store_var({"points":points,"indices":indices,"patch":PackedVector3Array([a,b,c]),"reason":result.reason})
		return result
func check(ok:bool,message:String)->void:
	if not ok:failures+=1;push_error(message)
func _initialize()->void:
	var source=load("res://scripts/capsule_solver.gd").new();source.geometry=load("res://scripts/anterior_segment.gd").new();source.reset()
	var model=load("res://scripts/embedded_membrane.gd").new()
	check(model.initialize(source.rest_positions,source.triangles,source.anchored,source.surface_density).valid,"curved embedded specimen initializes from its own rest state")
	model._cutter=RecordingCutter.new()
	var initial:Dictionary=model.snapshot();var radius:=.4;var y:float=source.geometry.bag_front(radius)
	var prior:=Vector3(radius,y,0.)
	# Geometry/material-state qualification only. Finite curtain triangles are
	# specified directly; this does not claim a mouse or sharp-blade encounter.
	for i in range(1,65):
		var next:=Vector3(radius*cos(TAU*i/64.),y,radius*sin(TAU*i/64.))
		var down:=Vector3.UP*.05
		var result:Dictionary=model.incise_patches([PackedVector3Array([prior-down,next-down,next+down]),PackedVector3Array([prior-down,next+down,prior+down])])
		check(result.valid,"curved embedded incision %d: %s"%[i,result.reason])
		if not result.valid:break
		prior=next
	var state:Dictionary=model.snapshot();var total_mass:=0.;var minimum:=INF
	for mass in state.support.mass:total_mass+=mass;minimum=minf(minimum,mass)
	check(absf(total_mass-source.metrics().retained_area*source.surface_density)<1e-10,"curved closed route retains all actual material mass")
	check(state.xyz==state.previous,"geometric cutting does not secretly advance or reset material time history")
	var adjacency:Dictionary={}
	for off in range(0,state.indices.size(),3):
		for j in range(3):
			var a:int=state.indices[off+j];var b:int=state.indices[off+(j+1)%3]
			if not adjacency.has(a):adjacency[a]=[]
			if not adjacency.has(b):adjacency[b]=[]
			adjacency[a].append(b);adjacency[b].append(a)
	var components:Dictionary={};var count:=0
	for vertex in adjacency:
		if components.has(vertex):continue
		var queue:Array=[vertex];components[vertex]=count
		while not queue.is_empty():
			for other in adjacency[queue.pop_back()]:
				if not components.has(other):components[other]=count;queue.append(other)
		count+=1
	check(count==2,"closed retained curved cut makes one real free flap and the anchored remainder")
	var control_components:Dictionary={}
	for face in range(state.ancestors.size()):
		var component:int=components[state.indices[face*3]]
		for j in range(3):
			var control:int=state.support.elements[face*3+j]
			check(not control_components.has(control) or control_components[control]==component,"detached curved flap has no shared mechanical control with the anchored remainder")
			control_components[control]=component
	print("Curved embedded state: ",JSON.stringify({"fine_vertices":state.rest.size(),"fine_triangles":state.indices.size()/3,"controls":state.support.controls.size(),"initial_controls":initial.support.controls.size(),"events":state.events,"components":count,"mass":total_mass,"minimum_mass":minimum},"",true,true))
	print("Embedded cut route: ",failures," failures");quit(1 if failures else 0)
