extends SceneTree
var failures:=0
func check(ok:bool,message:String)->void:
	if not ok: failures+=1; push_error(message)
func area(p:PackedVector3Array,ids:PackedInt32Array)->float:
	var total:=0.
	for i in range(0,ids.size(),3): total+=(p[ids[i+1]]-p[ids[i]]).cross(p[ids[i+2]]-p[ids[i]]).length()*.5
	return total
func components(ids:PackedInt32Array)->int:
	var parent:={}
	for v in ids: parent[v]=v
	for i in range(0,ids.size(),3):
		for j in [1,2]:
			var a:int=ids[i]; var b:int=ids[i+j]
			while parent[a]!=a: a=parent[a]
			while parent[b]!=b: b=parent[b]
			parent[b]=a
	var roots:={}
	for v in parent:
		while parent[v]!=v: v=parent[v]
		roots[v]=true
	return roots.size()
func verify(result:Dictionary,p:PackedVector3Array,ids:PackedInt32Array)->void:
	check(result.valid,"cut is valid: "+result.reason)
	if not result.valid: return
	check(absf(area(result.points,result.indices)-area(p,ids))<.00001,"cut preserves current tissue area")
	check(result.sources.size()*3==result.indices.size(),"all retained faces retain source provenance")
	check(result.bindings.size()==result.points.size(),"all points have interpolation provenance")
	var rest:=PackedVector3Array(); var transferred:=PackedVector3Array()
	for point in p: rest.append(Vector3(point.x,point.y+.13*sin(point.x+point.z),point.z))
	for i in range(result.points.size()):
		var binding:Dictionary=result.bindings[i]; var weights:Vector3=binding.weights; var source:Vector3i=binding.ids
		check(weights.x>=0. and weights.y>=0. and weights.z>=0. and absf(weights.x+weights.y+weights.z-1.)<.00001,"state transfer weights are convex")
		check(result.points[i].distance_to(p[source.x]*weights.x+p[source.y]*weights.y+p[source.z]*weights.z)<.00001,"point interpolates actual source coordinates")
		transferred.append(rest[source.x]*weights.x+rest[source.y]*weights.y+rest[source.z]*weights.z)
	check(absf(area(transferred,result.indices)-area(rest,ids))<.00001,"barycentric transfer also preserves an independent material rest surface area")
	for i in range(0,result.indices.size(),3):
		var source:int=result.sources[i/3]*3
		var original:=(p[ids[source+1]]-p[ids[source]]).cross(p[ids[source+2]]-p[ids[source]])
		var normal:Vector3=(result.points[result.indices[i+1]]-result.points[result.indices[i]]).cross(result.points[result.indices[i+2]]-result.points[result.indices[i]])
		check(normal.dot(original)>0.,"subdivision preserves face winding and nonzero area")
func _initialize()->void:
	var source=load("res://scripts/membrane_cut.gd")
	if source==null: push_error("area-preserving membrane cutter missing"); quit(1); return
	var cutter=source.new()
	var p:=PackedVector3Array([Vector3(-1,0,-1),Vector3(1,0,-1),Vector3(0,0,1)])
	var ids:=PackedInt32Array([0,2,1])
	var r:Dictionary=cutter.slice(p,ids,Vector3(-2,0,0),Vector3(2,0,0),Vector3.UP,.1)
	verify(r,p,ids)
	if r.valid: check(r.changed and components(r.indices)==2,"boundary-to-boundary slit separates two area-bearing banks")
	r=cutter.slice(p,ids,Vector3(-.2,0,0),Vector3(.2,0,0),Vector3.UP,.1)
	verify(r,p,ids)
	if r.valid:
		check(r.changed and components(r.indices)==1,"interior crack tips retain surrounding tissue connection")
		var midpoint_count:=0
		for point in r.points:
			if point.distance_to(Vector3.ZERO)<.00001: midpoint_count+=1
		check(midpoint_count==2,"interior slit has separate midpoint nodes for the two banks")
	var square:=PackedVector3Array([Vector3(-1,0,-1),Vector3(1,0,-1),Vector3(1,0,1),Vector3(-1,0,1)])
	var faces:=PackedInt32Array([0,2,1,0,3,2])
	r=cutter.slice(square,faces,Vector3(-2,0,0),Vector3(2,0,0),Vector3.UP,.1)
	verify(r,square,faces)
	if r.valid:
		check(components(r.indices)==2,"shared diagonal splits without disconnected extra fragments")
		var again:Dictionary=cutter.slice(r.points,r.indices,Vector3(-2,0,0),Vector3(2,0,0),Vector3.UP,.1)
		verify(again,r.points,r.indices)
		if again.valid:
			check(components(again.indices)==2,"repeated stroke cannot weld existing separated banks")
			check(not again.changed and again.points==r.points and again.indices==r.indices,"repeated stroke over an open seam is exactly idempotent")
		var cross_cut:Dictionary=cutter.slice(r.points,r.indices,Vector3(0,0,-2),Vector3(0,0,2),Vector3.UP,.1)
		verify(cross_cut,r.points,r.indices)
		if cross_cut.valid: check(components(cross_cut.indices)==4,"crossing an existing cut retains four separate patches")
	var disjoint:=square.duplicate(); disjoint.append_array(square)
	var disconnected:=faces.duplicate()
	for v in faces: disconnected.append(v+4)
	r=cutter.slice(disjoint,disconnected,Vector3(-2,0,0),Vector3(2,0,0),Vector3.UP,.1)
	verify(r,disjoint,disconnected)
	if r.valid: check(components(r.indices)==4,"coincident disconnected material never welds")
	for stroke in [[Vector3(3,0,0),Vector3(4,0,0)],[Vector3(-2,.5,0),Vector3(2,.5,0)]]:
		r=cutter.slice(p,ids,stroke[0],stroke[1],Vector3.UP,.1)
		check(r.valid and not r.changed and r.points==p and r.indices==ids,"finite stroke/depth leaves untouched material identical")
	r=cutter.slice(p,ids,Vector3(-2,0,0),Vector3(2,0,0),Vector3.UP,.1,3,1)
	check(not r.valid and r.points.is_empty() and r.indices.is_empty(),"budget rejects atomically without partial cut")
	var bad:=p.duplicate(); bad[0]=Vector3(NAN,0,0)
	r=cutter.slice(bad,ids,Vector3(-2,0,0),Vector3(2,0,0),Vector3.UP,.1)
	check(not r.valid,"nonfinite source rejected")
	r=cutter.slice(p,ids,Vector3(-2,0,0),Vector3(2,0,0),Vector3.RIGHT,.1)
	check(not r.valid,"degenerate curtain axis rejected")
	var bow:=PackedVector3Array([Vector3.ZERO,Vector3.RIGHT,Vector3(0,0,1),Vector3.LEFT,Vector3(0,0,-1)])
	r=cutter.slice(bow,PackedInt32Array([0,2,1,0,4,3]),Vector3(2,0,0),Vector3(3,0,0),Vector3.UP,.1)
	check(not r.valid and r.reason=="nonmanifold_vertex","bow-tie vertex source rejected before any incision")
	var near:=PackedVector3Array([Vector3.ZERO,Vector3.RIGHT,Vector3(0,0,1),Vector3(-.9,0,-.2),Vector3(-.1,0,-.2),Vector3(-.5,0,.2)])
	var near_faces:=PackedInt32Array([0,2,1,3,5,4])
	r=cutter.slice(near,near_faces,Vector3(-1,0,.0000005),Vector3(2,0,.0000005),Vector3.UP,.1)
	verify(r,near,near_faces)
	if r.valid: check(components(r.indices)==4,"a successful second face cannot hide a missing near-boundary seam")
	var tilted:=PackedVector3Array([Vector3(-1,-.5,-1),Vector3(1,.5,-1),Vector3(0,0,1)])
	r=cutter.slice(tilted,ids,Vector3(-2,0,0),Vector3(2,0,0),Vector3.UP,.2)
	verify(r,tilted,ids)
	if r.valid: check(components(r.indices)==1,"finite blade depth makes an interior slit on an oblique sheet, not an infinite plane cut")
	var triple:=PackedInt32Array([0,2,1,0,1,2,0,2,1])
	r=cutter.slice(p,triple,Vector3(-2,0,0),Vector3(2,0,0),Vector3.UP,.1)
	check(not r.valid,"nonmanifold edge rejected atomically")
	r=cutter.slice(p,ids,Vector3(-2,0,0),Vector3(2,0,0),Vector3(0,0,1),.1)
	check(not r.valid and r.reason=="coplanar_curtain","ambiguous coplanar sheet/curtain intersection rejects explicitly")
	var shared_tip:Dictionary=cutter.slice(square,faces,Vector3.ZERO,Vector3(.7,0,0),Vector3.UP,.1)
	verify(shared_tip,square,faces)
	if shared_tip.valid: check(components(shared_tip.indices)==1,"crack ending on a shared source edge remains connected without a T junction")
	var skinny:=PackedVector3Array([Vector3(-1,0,-.00001),Vector3(1,0,-.00001),Vector3(0,0,.00001)])
	r=cutter.slice(skinny,ids,Vector3(-2,0,0),Vector3(2,0,0),Vector3.UP,.1)
	verify(r,skinny,ids)
	if r.valid: check(components(r.indices)==2,"thin nonzero triangles retain two area-bearing cut banks")
	var geometry=load("res://scripts/anterior_segment.gd").new()
	var capsule=load("res://scripts/capsule_solver.gd").new(); capsule.geometry=geometry; capsule.reset()
	var curved:PackedVector3Array=capsule.positions.duplicate(); var curved_ids:PackedInt32Array=capsule.triangles.duplicate()
	var initial_area:=area(curved,curved_ids); var radius:=.4; var y:float=geometry.bag_front(radius)
	var prior:=Vector3(radius,y,0.)
	var started:=Time.get_ticks_msec()
	for i in range(1,65):
		var next:=Vector3(radius*cos(TAU*i/64.),y,radius*sin(TAU*i/64.))
		r=cutter.slice(curved,curved_ids,prior,next,Vector3.UP,.05)
		check(r.valid,"actual curved capsule circular stroke %d: %s"%[i,r.reason])
		if not r.valid: break
		curved=r.points; curved_ids=r.indices; prior=next
	check(absf(area(curved,curved_ids)-initial_area)<.00005,"closed actual capsule incision preserves tissue area")
	check(components(curved_ids)==2,"closed circular incision separates a retained central flap from anchored rim")
	print("Curved cut vertices/triangles/components/ms: ",curved.size(),"/",curved_ids.size()/3,"/",components(curved_ids),"/",Time.get_ticks_msec()-started)
	check(p==PackedVector3Array([Vector3(-1,0,-1),Vector3(1,0,-1),Vector3(0,0,1)]) and ids==PackedInt32Array([0,2,1]),"all calls leave source arrays immutable")
	print("Membrane cut: ",failures," failures"); quit(1 if failures else 0)
