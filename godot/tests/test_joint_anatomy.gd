extends SceneTree
var failures:=0
const Source=preload("res://scripts/capsule_solver.gd")
func check(ok:bool,message:String)->void:
	if not ok: failures+=1; push_error(message)
class Query extends RefCounted:
	var calls:=0
	var mode:="once"
	var reply:Variant=null
	func inspect(_backend:RefCounted,_old:PackedFloat64Array,_current:PackedFloat64Array,vertices:PackedInt32Array)->Variant:
		calls+=1
		if reply!=null: return reply
		if mode=="unknown" or (mode=="later" and calls==3): return {"status":2}
		if mode=="initial" or (calls>1 and (mode in ["always","repeated"] or (mode=="once" and calls==2))):
			return {"status":1,"vertex":vertices[0],"face":0,"triangle":PackedFloat64Array([-1,0,-1,1,0,-1,0,0,1]),"radius":.1,"witness_t":0. if mode=="initial" else (pow(.5,calls-1) if mode=="always" else .5),"gap":-.001}
		return {"status":0,"gap":INF}
class Backend extends RefCounted:
	var static_calls:=0
	var guards:=0
	var interleave:=false
	var fail_anatomy:=false
	var anatomy_requests:Array[Dictionary]=[]
	func solve_contact(request:Dictionary)->Dictionary:
		static_calls+=1
		return {"status":0,"xyz":request.initial.duplicate(),"stats":PackedFloat64Array([0,0,0,0,0,0,0,0,0,0,0,0])}
	func guard_motion(_request:Dictionary)->Dictionary:
		guards+=1
		if interleave and guards==2: return {"status":1,"witness_t":.25}
		return {"status":0,"stats":PackedFloat64Array([1,1,-1,-1,INF,0,0,0])}
	func solve_anatomy(request:Dictionary)->Dictionary:
		anatomy_requests.append(request.duplicate(true))
		if fail_anatomy: return {"status":1}
		var result:=solve_contact(request); static_calls-=1
		var count:int=request.triangles.size()/3*request.kinds.size()*request.times.size()+request.anatomy_vertices.size()
		var dual:=PackedFloat64Array(); dual.resize(count)
		if not request.anatomy_vertices.is_empty(): dual[-1]=1.
		result["dual"]=dual
		return result
class Boundary extends RefCounted:
	var query:RefCounted
	func anatomical_query()->RefCounted: return query
	func resolve(_old:Vector3,current:Vector3,outside:bool)->Dictionary:
		return {"valid":true,"position":current,"outside":outside,"contact":false}
class MissingAnatomy extends RefCounted:
	var calls:=0
	func solve_contact(_request:Dictionary)->Dictionary:
		calls+=1; return {"status":1}
func request()->Dictionary:
	return {"initial":PackedFloat64Array([0,.1,0,-1,.1,0,0,.1,-1]),"predicted":PackedFloat64Array([0,.1,0,-1,.1,0,0,.1,-1]),"inverse":PackedFloat64Array([1,0,0]),"a":PackedInt32Array(),"b":PackedInt32Array(),"rest":PackedFloat64Array(),"alpha":.1,"triangles":PackedInt32Array([0,1,2]),"capsules":PackedFloat64Array(),"budget":100,"force_tolerance":1e-8,"gap_tolerance":1e-9,"complementarity_tolerance":1e-11}
func small_model():
	var model=Source.new()
	model.triangles=PackedInt32Array([0,1,2]); model._inverse_mass=PackedFloat64Array([1,0,0])
	return model
func specimen():
	var shape=load("res://scripts/anterior_segment.gd").new()
	var model=Source.new(); model.geometry=shape; model.reset()
	var prior:=Vector3(.4,shape.bag_front(.4),0)
	for i in range(1,65):
		var next:=Vector3(.4*cos(TAU*i/64.),prior.y,.4*sin(TAU*i/64.))
		check(model.incise(prior,next,Vector3.UP,.05).valid,"actual refined incision"); prior=next
	var selected:PackedInt32Array=model._joint_anatomy_vertices()
	var expected:PackedInt32Array=model.detached_components()[0].vertices
	check(not selected.is_empty() and selected.size()==expected.size(),"every detached material vertex participates in anatomy queries")
	for v in selected: check(expected.has(v) and model._removed[v]==0 and model.anchored[v]==0,"query selection excludes removed and anchored material")
	return model
func _initialize()->void:
	var initial=Source.new()
	check(initial.has_method("_joint_anatomy_vertices"),"actual capsule exposes detached physical anatomy selection")
	var boundary_source=load("res://scripts/flap_boundary.gd").new()
	check(boundary_source.has_method("anatomical_query"),"configured boundary exposes finite iris query geometry")
	if failures: quit(1); return
	var tiny=Source.new(); tiny.surface_density=100.
	var tiny_components:Array[Dictionary]=[{"anchored":false,"area":5e-13,"vertices":PackedInt32Array([0,1,2])},{"anchored":false,"area":0.,"vertices":PackedInt32Array([3])}]
	tiny._components=tiny_components; tiny._component_dirty=false; tiny._removed=PackedByteArray([0,0,0,0])
	check(1./(tiny.surface_density*(5e-13/3.))<1e12,"tiny positive material can stay within native inverse mass bounds")
	check(tiny._joint_anatomy_vertices()==PackedInt32Array([0,1,2]),"positive material area has no arbitrary anatomy selection cutoff; zero support is excluded")
	tiny._removed[2]=1
	check(tiny._joint_anatomy_vertices()==PackedInt32Array([0,1]),"removed tissue is excluded without hiding other tiny material")
	var req:=request(); var saved:=req.duplicate(true)
	for interleave in [false,true]:
		var model=small_model(); var backend:=Backend.new(); backend.interleave=interleave; model.contact_backend=backend
		var query:=Query.new()
		var body:Array=[{"a":Vector3(3,3,3),"b":Vector3(3.1,3,3),"previous_a":Vector3(3,3,3),"previous_b":Vector3(3.1,3,3),"radius":.018}] if interleave else []
		var solved:Dictionary=model._joint_contact_candidate(req,body,req.initial,query,PackedInt32Array([0]))
		check(not solved.is_empty() and model.native_failure.is_empty(),"finite anatomy witness is solved and checked again, including with no tool bodies")
		check(backend.anatomy_requests.size()==(2 if interleave else 1),"tool and anatomy refinements share the same solver loop")
		for recorded in backend.anatomy_requests:
			check(recorded.predicted==saved.predicted and recorded.previous==saved.initial and recorded.alpha==saved.alpha,"anatomy refinement retains original predictor history and material")
			check(recorded.anatomy_vertices==PackedInt32Array([0]) and recorded.anatomy==PackedFloat64Array([-1,0,-1,1,0,-1,0,0,1,.1,.5]),"finite face radius and witness time enter the physical request")
		check(req==saved and model.body_contact_count==0,"query generation is immutable and anatomical reactions are not counted as tool reactions")
	for mode in ["initial","unknown","always","repeated","failed"]:
		var model=small_model(); var backend:=Backend.new(); backend.fail_anatomy=mode=="failed"; model.contact_backend=backend
		var query:=Query.new(); query.mode=mode if mode!="failed" else "once"
		var solved:Dictionary=model._joint_contact_candidate(req,[],req.initial,query,PackedInt32Array([0]))
		check(solved.is_empty() and not model.native_failure.is_empty(),"anatomy "+mode+" rejects without an accepted candidate")
		if mode in ["initial","unknown"]: check(backend.static_calls==0,"invalid initial anatomy rejects before solving")
		if mode=="always": check(backend.anatomy_requests.size()==7,"tool and anatomical constraints retain the original eight-solve budget")
	var unsupported=small_model(); var missing:=MissingAnatomy.new(); unsupported.contact_backend=missing
	check(unsupported._joint_contact_candidate(req,[],req.initial,Query.new(),PackedInt32Array([0])).is_empty() and missing.calls==0 and unsupported.native_failure.get("reason","")=="native_joint_anatomy_unavailable","missing anatomy capability rejects before a static solve")
	for reply in [{},{"status":"0","gap":INF},{"status":0,"gap":-.001},{"status":0,"gap":NAN},{"status":1,"gap":-.001,"witness_t":.5,"vertex":0,"face":0,"radius":.1,"triangle":PackedFloat64Array([0])}]:
		var model=small_model(); var backend:=Backend.new(); model.contact_backend=backend
		var query:=Query.new(); query.reply=reply
		check(model._joint_contact_candidate(req,[],req.initial,query,PackedInt32Array([0])).is_empty() and backend.static_calls==0,"malformed anatomy cannot certify initial clearance or publish a candidate")
	for mode in ["initial","later"]:
		var model=specimen(); var query:=Query.new(); query.mode=mode
		var boundary:=Boundary.new(); boundary.query=query; model.tissue_boundary=boundary
		model.set_contact_backend(Backend.new()); var state:Dictionary=model._checkpoint()
		model.step(1./60.,Vector3(3,3,3),.018,false,false)
		check(not model.native_failure.is_empty() and model._physical_xyz==state._physical_xyz and model._physical_previous==state._physical_previous and model._outside==state._outside and model.metrics().integration_steps==state._integration_steps,"anatomy "+mode+" restores whole outer timestep, including an accepted first substep")
		if mode=="later": check(query.calls==3,"later failure follows one fully checked accepted substep")
	print("Joint anatomy: ",failures," failures"); quit(1 if failures else 0)
