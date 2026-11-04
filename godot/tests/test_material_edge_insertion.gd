extends SceneTree
var failures:=0
func check(ok:bool,message:String)->void:
	if not ok:failures+=1;push_error(message)
func verify_subedge(reverse:bool)->void:
	var cutter=load("res://scripts/membrane_cut.gd").new();cutter._triangle_limit=8192
	cutter._points=PackedVector3Array([Vector3.ZERO,Vector3.RIGHT,Vector3.BACK,Vector3(.5,0,0),Vector3(.75,0,0)])
	for i in range(3):cutter._bindings.append({"ids":Vector3i(i,i,i),"weights":Vector3(1,0,0)})
	cutter._bindings.append({"ids":Vector3i(0,1,2),"weights":Vector3(.5,.5,0)})
	cutter._bindings.append({"ids":Vector3i(0,1,2),"weights":Vector3(.25,.75,0)})
	var initial:Array[PackedInt32Array]=[PackedInt32Array([2,1,0] if reverse else [0,1,2])]
	var first:Array[PackedInt32Array]=cutter._insert(initial,3);var second:Array[PackedInt32Array]=cutter._insert(first,4)
	var edges:Dictionary={}
	for triangle in second:
		for j in range(3):edges[Vector2i(mini(triangle[j],triangle[(j+1)%3]),maxi(triangle[j],triangle[(j+1)%3]))]=true
	check(cutter._failure=="" and second.size()==3 and edges.has(Vector2i(3,4)) and edges.has(Vector2i(1,4)) and not edges.has(Vector2i(0,4)),"material parameter selects the containing refined subedge in either traversal order")
func verify_interior_near_edge()->void:
	var cutter=load("res://scripts/membrane_cut.gd").new();cutter._triangle_limit=8192
	cutter._points=PackedVector3Array([Vector3.ZERO,Vector3.RIGHT,Vector3(0,0,.001),Vector3(.5,0,1e-7)])
	for i in range(3):cutter._bindings.append({"ids":Vector3i(i,i,i),"weights":Vector3(1,0,0)})
	cutter._bindings.append({"ids":Vector3i(0,1,2),"weights":Vector3(.4999,.5,.0001)})
	var initial:Array[PackedInt32Array]=[PackedInt32Array([0,1,2])]
	var output:Array[PackedInt32Array]=cutter._insert(initial,3)
	check(cutter._failure=="" and output.size()==3,"a positive interior material point creates all three faces even within display edge snapping distance")
func _initialize()->void:
	verify_subedge(false);verify_subedge(true);verify_interior_near_edge()
	var inside_cutter=load("res://scripts/membrane_cut.gd").new()
	var inside:Dictionary=inside_cutter.slice_triangle(PackedVector3Array([Vector3(-1,0,-1),Vector3(1,0,-1),Vector3(0,0,1)]),PackedInt32Array([0,2,1]),Vector3(-.2,-.2,0),Vector3(.2,-.2,0),Vector3(0,.2,0),4096,8192,true)
	var banks:=0
	if inside.valid:
		for point in inside.points:
			if point.length()<1e-7:banks+=1
	check(inside.valid and banks==2,"finite slit wholly inside one source face retains two distinct interior banks")
	var partition:Dictionary=FileAccess.open("res://tests/fixtures/operative-blade-partition.bin",FileAccess.READ).get_var()
	var partition_model=load("res://scripts/embedded_membrane.gd").new();partition_model._state=partition.state.duplicate(true)
	var partition_cut:Dictionary=partition_model.incise_patches([partition.patch])
	check(partition_cut.valid and partition_cut.changed,"near-boundary interior point retains the entire original material partition: "+partition_cut.reason)
	var saved:Dictionary=FileAccess.open("res://tests/fixtures/operative-blade-winding.bin",FileAccess.READ).get_var()
	var model=load("res://scripts/embedded_membrane.gd").new();model._state=saved.state.duplicate(true)
	var before:Dictionary=model.snapshot();var cutter=load("res://scripts/membrane_cut.gd").new()
	var cut:Dictionary=cutter.slice_triangle(model.positions(),before.indices,saved.patch[0],saved.patch[1],saved.patch[2],4096,8192,true)
	check(cut.valid and cut.changed,"exact edge-bound operative point splits its material edge: "+cut.reason)
	if cut.valid:
		var fractions:=PackedFloat64Array();fractions.resize(before.areas.size())
		for face in range(cut.sources.size()):fractions[cut.sources[face]]+=cut.fractions[face]
		for fraction in fractions:check(absf(fraction-1.)<1e-10,"edge insertion retains each parent material partition")
	var result:Dictionary=model.incise_patches([saved.patch])
	check(result.valid and result.changed,"exact operative cut preserves original support and histories: "+result.reason)
	if result.valid:
		var after:Dictionary=model.snapshot();var old_mass:=0.;var new_mass:=0.
		for mass in before.support.mass:old_mass+=mass
		for mass in after.support.mass:new_mass+=mass
		check(absf(new_mass-old_mass)<1e-12 and after.steps==before.steps and after.time==before.time,"feature insertion preserves real mass and never invents a physical tick")
		for face in range(cut.sources.size()):
			for j in range(3):
				var node:int=after.support.elements[face*3+j];var old:int=before.support.elements[cut.sources[face]*3+j]
				for axis in range(3):check(after.xyz[node*3+axis]==before.xyz[old*3+axis] and after.previous[node*3+axis]==before.previous[old*3+axis],"canonical midpoint transfer retains exact original mechanical position and velocity history")
	print("Material edge insertion: ",failures," failures");quit(1 if failures else 0)
