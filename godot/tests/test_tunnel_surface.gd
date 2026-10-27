extends SceneTree
var failures:=0
func check(ok:bool,message:String)->void:
	if not ok: failures+=1; push_error(message)
func _initialize()->void:
	var source=load("res://scripts/tunnel_surface.gd")
	if source==null: push_error("tunnel surface builder missing"); quit(1); return
	var builder=source.new()
	var p:=PackedVector3Array([Vector3(-2,-.2,-2),Vector3(2,-.2,-2),Vector3(2,-.2,2),Vector3(-2,-.2,2),Vector3(-2,.2,-2),Vector3(2,.2,-2),Vector3(2,.2,2),Vector3(-2,.2,2)])
	var ids:=PackedInt32Array([0,2,1,0,3,2,4,5,6,4,6,7,0,1,5,0,5,4,1,2,6,1,6,5,2,3,7,2,7,6,3,0,4,3,4,7])
	var r:Dictionary=builder.build(p,ids,[],.15)
	check(r.valid and r.points==p and r.indices==ids,"no wound preserves exact source mesh")
	var path:=[PackedVector3Array([Vector3(-.5,0,0),Vector3(.5,0,0)])]
	r=builder.build(p,ids,path,.15)
	check(r.valid,"bounded incision produces valid closed tunnel: "+r.reason)
	if r.valid:
		check(r.sources.has(-1),"tunnel walls have generated source marker")
		var window=load("res://scripts/incision_window.gd")
		for triangle in range(r.sources.size()):
			if r.sources[triangle]!=-1: continue
			for corner in range(3): check(window.contains(r.points[r.indices[triangle*3+corner]],path,.000001,.15,[]),"generated wall stays inside incision footprint")
		check(builder.is_closed(r.points,r.indices),"result tunnel shell has no boundary edges")
		var kernel=load("res://scripts/capsule_surface.gd").new()
		var q:Dictionary=kernel.query(Vector3(0,-1,0),Vector3(0,1,0),.05,r.points,r.indices)
		check(not q.hit,"through-hole capsule clears skins and tunnel walls")
		q=kernel.query(Vector3(0,-1,.3),Vector3(0,1,.3),.05,r.points,r.indices)
		check(q.hit,"intact shell outside footprint still blocks capsule")
	var curve:=[PackedVector3Array([Vector3(-.7,0,0),Vector3(-.7,0,.7),Vector3(.7,0,.7)])]
	r=builder.build(p,ids,curve,.1)
	check(r.valid,"curved union builds a closed shell: "+r.reason)
	if r.valid:
		var kernel=load("res://scripts/capsule_surface.gd").new()
		check(kernel.query(Vector3(0,-1,.2),Vector3(0,1,.2),.02,r.points,r.indices).hit,"untraced concavity remains intact")
	r=builder.build(p,ids,[PackedVector3Array([Vector3(4,0,0),Vector3(5,0,0)])],.1)
	check(not r.valid,"non intersecting outside incision rejected")
	r=builder.build(p,ids,path,.15,[],8)
	check(not r.valid and r.points.is_empty(),"budget failure returns no partial mesh")
	var bad:=p.duplicate(); bad[0]=Vector3(NAN,0,0)
	r=builder.build(bad,ids,path,.1)
	check(not r.valid,"nonfinite source rejected")
	check(not builder.is_closed(bad,ids),"closed-shell checker rejects nonfinite points")
	r=builder.build(p,ids,[PackedVector3Array([Vector3.ZERO,Vector3(INF,0,0)])],.1)
	check(not r.valid,"nonfinite stroke rejected")
	var collinear:=[PackedVector3Array([Vector3(-.5,0,0),Vector3(-.25,0,0),Vector3.ZERO,Vector3(.25,0,0),Vector3(.5,0,0)])]
	var short:Dictionary=builder.build(p,ids,path,.15)
	r=builder.build(p,ids,collinear,.15)
	check(r.valid and r.points==short.points and r.indices==short.indices,"forward collinear samples compress to identical geometry")
	r=builder.build(p,ids,path,.15,[Vector3(0,0,.7)])
	check(r.valid,"portal offset builds bounded entry tunnel")
	if r.valid:
		var kernel=load("res://scripts/capsule_surface.gd").new()
		check(not kernel.query(Vector3(0,-1,.6),Vector3(0,1,.6),.03,r.points,r.indices).hit,"portal offset opens swept quad interior")
		check(r.sources.size()*3==r.indices.size(),"every output triangle has a source mapping")
		for source_id in r.sources: check(source_id>=-1 and source_id<ids.size()/3,"source mapping references original triangle or generated wall")
	r=builder.build(p,ids,[],.15,[],8)
	check(not r.valid and r.indices.is_empty(),"unchanged source also respects triangle budget")
	var reversed:=ids.duplicate(); reversed[0]=0; reversed[1]=1; reversed[2]=2
	r=builder.build(p,reversed,path,.15)
	check(not r.valid,"inconsistent source winding is rejected atomically")
	var segment=load("res://scripts/anterior_segment.gd").new()
	var cornea:Dictionary=segment.cornea()
	var trace:=PackedVector3Array()
	for i in range(101): trace.append(Vector3(1.32,.80,-.25+.005*i))
	var started:=Time.get_ticks_msec()
	r=builder.build(cornea.positions,cornea.triangles,[trace],.085,[segment.portals[0]])
	var elapsed:=Time.get_ticks_msec()-started
	check(r.valid,"default 101-point cornea tunnel builds within bounded work: "+r.reason)
	if r.valid:
		check(builder.is_closed(r.points,r.indices),"default cornea tunnel remains closed")
		check(r.sources.size()*3==r.indices.size() and r.sources.has(-1),"default cornea tunnel sources include walls")
		check(r.indices.size()/3<10000,"straight default rebuild remains bounded in geometry size")
		var kernel=load("res://scripts/capsule_surface.gd").new()
		check(not kernel.query(Vector3(1.36,.3,0),Vector3(1.36,1.2,0),.025,r.points,r.indices).hit,"default cornea hole admits a full sleeve capsule")
		print("Default cornea tunnel output vertices/triangles: ",r.points.size(),"/",r.indices.size()/3)
	var open_ids:PackedInt32Array=cornea.triangles.slice(3)
	r=builder.build(cornea.positions,open_ids,[trace],.085,[segment.portals[0]])
	check(not r.valid and r.reason=="source_not_closed","raw injured open shell rejects explicitly")
	r=builder.build(p,ids,path,8.0)
	check(not r.valid and r.points.is_empty(),"complete subtraction returns atomic invalid mesh")
	print("Default cornea tunnel build ms: ",elapsed)
	var conform_input:Array[Dictionary]=[
		{"p":PackedVector3Array([Vector3.ZERO,Vector3(2,0,0),Vector3(0,0,2)]),"source":0},
		{"p":PackedVector3Array([Vector3(1,0,0),Vector3(1,-1,0),Vector3(1,0,-1)]),"source":1}]
	builder._work=0; builder._failed=false
	var conformed:Array[Dictionary]=builder._conform(conform_input,4)
	check(builder._failed and conformed.is_empty(),"unchanged triangle after split cannot bypass conform cap")
	builder._work=0; builder._failed=false
	conformed=builder._conform(conform_input,5)
	check(not builder._failed and conformed.size()==5,"conform cap permits exact five-triangle boundary")
	var wall_edges:Array=[
		[Vector3(0,0,0),Vector3(1,0,0)],
		[Vector3(0,1,0),Vector3(1,1,0)]]
	builder._work=builder.MAX_WORK-1; builder._failed=false
	var active:Array=builder._wall_active_edges(wall_edges,Vector2.RIGHT,.5)
	check(builder._failed and active.is_empty(),"wall interval edge search exhausts remaining budget atomically")
	builder._work=builder.MAX_WORK-2; builder._failed=false
	active=builder._wall_active_edges(wall_edges,Vector2.RIGHT,.5)
	check(not builder._failed and active.size()==2 and builder._work==builder.MAX_WORK,"wall search accounts exactly one work unit per examined edge")
	print("Tunnel surface: ",failures," failures"); quit(1 if failures else 0)
