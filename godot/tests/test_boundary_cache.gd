extends SceneTree
var failures:=0
func check(ok:bool,message:String)->void:
	if not ok: failures+=1; push_error(message)
func reference(data:Dictionary,p:Vector3)->Vector2:
	var lo:=INF; var hi:=-INF
	for i in range(0,data.triangles.size(),3):
		var a:Vector3=data.positions[data.triangles[i]]; var b:Vector3=data.positions[data.triangles[i+1]]; var c:Vector3=data.positions[data.triangles[i+2]]
		var d:float=(b.z-c.z)*(a.x-c.x)+(c.x-b.x)*(a.z-c.z)
		if absf(d)<1e-12: continue
		var u:float=((b.z-c.z)*(p.x-c.x)+(c.x-b.x)*(p.z-c.z))/d
		var v:float=((c.z-a.z)*(p.x-c.x)+(a.x-c.x)*(p.z-c.z))/d
		if u>=-1e-6 and v>=-1e-6 and u+v<=1.+1e-6:
			var y:float=u*a.y+v*b.y+(1.-u-v)*c.y
			lo=minf(lo,y); hi=maxf(hi,y)
	return Vector2(lo,hi)
func _initialize()->void:
	var shape=load("res://scripts/anterior_segment.gd").new()
	var boundary=load("res://scripts/flap_boundary.gd").new()
	var cornea:Dictionary=shape.cornea(); var iris:Dictionary=shape.iris(.96)
	check(boundary.configure(cornea,iris),"configure immutable triangle fields")
	var rng:=RandomNumberGenerator.new(); rng.seed=79
	for i in range(700):
		var p:=Vector3(rng.randf_range(-1.6,1.6),rng.randf_range(-.8,1.8),rng.randf_range(-1.6,1.6))
		for pair in [[cornea,boundary._cornea],[iris,boundary._iris]]:
			var expected:=reference(pair[0],p); var actual:Vector4=boundary._heights(pair[1],p)
			check(Vector2(actual.x,actual.y)==expected,"cached field matches independent actual-triangle interpolation")
			var repeat:Vector4=boundary._heights(pair[1],Vector3(p.x,p.y+.25,p.z))
			check(repeat==actual,"height answer is independent of query Y and repeated identically")
	var center:Vector4=boundary._heights(boundary._cornea,Vector3.ZERO)
	check(boundary._cornea.height_cache.size()<=512 and boundary._iris.height_cache.size()<=512,"query memory remains bounded after more than 512 distinct coordinates")
	for i in range(cornea.positions.size()): cornea.positions[i].y+=.2
	check(boundary._heights(boundary._cornea,Vector3.ZERO)==center,"caller source edits cannot corrupt configured query state")
	check(boundary.configure(cornea,iris),"updated actual geometry replaces field")
	var changed:Vector4=boundary._heights(boundary._cornea,Vector3.ZERO)
	check(absf(changed.x-center.x-.2)<1e-6,"reconfiguration cannot reuse stale height answer")
	check(not boundary.configure({},iris),"invalid replacement rejects atomically")
	check(boundary._heights(boundary._cornea,Vector3.ZERO)==changed,"rejected replacement retains current valid answer")
	var slope:={"positions":PackedVector3Array([Vector3.ZERO,Vector3(1,1,0),Vector3(0,1,1)]),"triangles":PackedInt32Array([0,1,2])}
	var below:={"positions":PackedVector3Array([Vector3(0,-2,0),Vector3(1,-2,0),Vector3(0,-2,1)]),"triangles":PackedInt32Array([0,1,2])}
	check(boundary.configure(slope,below),"sloped reference surface configures")
	var near_edge:=Vector3(.5,0,.5000005)
	var edge_height:=reference(slope,near_edge)
	near_edge.y=edge_height.y+boundary.radius-.0000001
	check(boundary._blocked(near_edge),"Y broadphase retains contact inside barycentric edge tolerance")
	var first:Vector4=boundary._heights(boundary._cornea,Vector3(.25,0,.25))
	var adjacent:Vector4=boundary._heights(boundary._cornea,Vector3(.2500002,0,.25))
	check(adjacent.y>first.y,"cache preserves distinct nearby coordinates without spatial quantization")
	print("Boundary query equivalence: ",failures," failures"); quit(1 if failures else 0)
