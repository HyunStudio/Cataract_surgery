extends SceneTree
var failures:=0
func check(ok:bool,message:String)->void:
 if not ok:failures+=1;push_error(message)
func components(state:Dictionary)->int:
 var neighbors:Dictionary={}
 for off in range(0,state.indices.size(),3):
  for j in range(3):
   var a:int=state.indices[off+j];var b:int=state.indices[off+(j+1)%3]
   if not neighbors.has(a):neighbors[a]=[]
   if not neighbors.has(b):neighbors[b]=[]
   neighbors[a].append(b);neighbors[b].append(a)
 var seen:Dictionary={};var count:=0
 for seed in neighbors:
  if seen.has(seed):continue
  count+=1;var stack:Array=[seed];seen[seed]=true
  while not stack.is_empty():
   var vertex:int=stack.pop_back()
   for next in neighbors[vertex]:
    if not seen.has(next):seen[next]=true;stack.append(next)
 return count
func area(state:Dictionary)->float:
 var total:=0.
 for value in state.areas:check(value>0.,"retained material areas are strictly positive");total+=value
 return total
func model(rows:Array,ids:PackedInt32Array)->Dictionary:
 var original:=PackedVector3Array([Vector3.ZERO,Vector3.RIGHT,Vector3.BACK])
 var solver=load("res://scripts/embedded_membrane.gd").new()
 solver.initialize(original,PackedInt32Array([0,1,2]),PackedByteArray([0,0,0]),1.)
 var s:Dictionary=solver.snapshot();s.rest=PackedVector3Array();var weights:=PackedFloat64Array();s.areas=PackedFloat64Array();s.ancestors=PackedInt32Array()
 for row in rows:s.rest.append(Vector3(row[1],0.,row[2]))
 for off in range(0,ids.size(),3):
  var tri:Array=[]
  for j in range(3):tri.append(PackedFloat64Array(rows[ids[off+j]]));weights.append_array(rows[ids[off+j]])
  var sum:float=(tri[1][1]-tri[0][1])*(tri[2][2]-tri[0][2])-(tri[1][2]-tri[0][2])*(tri[2][1]-tri[0][1])
  s.areas.append(sum*.5);s.ancestors.append(0)
 s.indices=ids;s.fallback=s.rest.duplicate()
 for key in ["anchored","removed","outside"]:s[key]=PackedByteArray();s[key].resize(rows.size())
 s.support=load("res://scripts/membrane_support.gd").build(original,s.original_indices,s.rest,ids,s.ancestors,s.areas,1.,weights)
 check(s.support.valid,"synthetic retained chart initializes")
 s.fixed=PackedByteArray();s.fixed.resize(s.support.controls.size());s.xyz=PackedFloat64Array()
 for control in s.support.controls:
  for axis in range(3):s.xyz.append(original[control][axis])
 s.previous=s.xyz.duplicate();return s
func small_cases(helper)->void:
 var rows:Array=[[1.,0.,0.],[0.,1.,0.],[0.,0.,1.],[.5,.5,0.]];var ids:=PackedInt32Array([0,3,2,3,1,2]);var s:=model(rows,ids)
 var result:Dictionary=helper.simplify(s)
 check(result.valid and result.changed and result.removed_vertices==1 and result.state.rest.size()==3,"one exact straight boundary midpoint reduces to the identical triangle")
 var bent:Array=rows.duplicate(true);bent[3]=[.5-pow(2.,-40.),.5,pow(2.,-40.)];s=model(bent,ids)
 result=helper.simplify(s)
 check(result.valid and not result.changed,"positive inward boundary bend below display/proximity resolution cannot disappear")
 for flag in ["anchored","removed","outside"]:
  s=model(rows,ids);s[flag][3]=1;result=helper.simplify(s)
  check(result.valid and not result.changed,"flagged material vertex cannot be removed: "+flag)
 s=model(rows,ids);s.grasps={0:{"vertex":3,"face":0,"target":PackedFloat64Array([.5,0.,0.]),"reaction":PackedFloat64Array([0.,0.,0.])}};result=helper.simplify(s)
 check(result.valid and not result.changed,"held face and vertex remain protected")
 var banks:Array=[[1.,0.,0.],[.5,.5,0.],[0.,0.,1.],[.25,.25,.5],[.5,.5,0.],[0.,1.,0.],[0.,0.,1.],[.25,.25,.5]]
 s=model(banks,PackedInt32Array([0,1,3,0,3,2,4,5,7,5,6,7]));result=helper.simplify(s)
 check(result.valid and result.changed and components(result.state)==2 and result.state.support.controls.size()==s.support.controls.size(),"coincident opposite banks simplify separately and never weld")
 check(not helper.simplify(s,0).valid and not helper.simplify(s,257).valid,"bounded reduction rejects invalid work budgets")
func audit_state(s:Dictionary)->Dictionary:
 return {"indices":Array(s.indices),"ancestors":Array(s.ancestors),"elements":Array(s.support.elements),"weights_le":Marshalls.raw_to_base64(s.support.weights.to_byte_array()),"areas_le":Marshalls.raw_to_base64(s.areas.to_byte_array()),"anchored":Array(s.anchored),"removed":Array(s.removed),"outside":Array(s.outside)}
func _initialize()->void:
 check(FileAccess.file_exists("res://scripts/embedded_material_reduce.gd"),"owned vertex exhaustion needs conservative material reduction without raised limits")
 if failures:quit(1);return
 var helper=load("res://scripts/embedded_material_reduce.gd")
 small_cases(helper)
 var captured:Dictionary=FileAccess.open("res://tests/fixtures/operative-vertex-budget-state.bin",FileAccess.READ).get_var();var before:Dictionary=captured.state.duplicate(true);var saved:=before.duplicate(true)
 var result:Dictionary=helper.simplify(before,128)
 check(result.valid and result.changed and result.removed_vertices>=32,"owned exact collinear material boundary vertices provide useful headroom")
 check(before==saved,"reduction cannot mutate its caller")
 if result.valid and result.changed:
  var after:Dictionary=result.state
  check(after.rest.size()==before.rest.size()-result.removed_vertices and after.indices.size()<before.indices.size(),"only proven redundant fine geometry is removed")
  for key in ["original","original_indices","original_anchors","xyz","previous","time","steps","events","fixed"]:check(after[key]==before[key],"coarse/accepted state retained bitwise: "+key)
  for key in ["controls","mass","minimum_mass","cells"]:check(after.support[key]==before.support[key],"authoritative mechanics retained bitwise: "+key)
  check(components(after)==components(before),"no cut bank welds or disappears")
  check(absf(area(after)-area(before))<1e-10,"whole retained material area conserved")
  var model=load("res://scripts/embedded_membrane.gd").new();model._state=before;var physical:PackedFloat64Array=model.physical_positions();model._state=after;var reduced:PackedFloat64Array=model.physical_positions()
  for point in range(result.point_sources.size()):
   for axis in range(3):check(reduced[point*3+axis]==physical[result.point_sources[point]*3+axis],"surviving physical material coordinates are bitwise unchanged")
  for hand in before.grasps:check(after.grasps.has(hand) and after.grasps[hand].target==before.grasps[hand].target,"held target is preserved")
  var cut:Dictionary=model._incise_one(captured.patch)
  check(cut.valid,"exact177-step physical patch fits original4096/8192limits after conservative reduction: "+cut.reason)
  if cut.valid:check(model.snapshot().rest.size()<=4096 and model.snapshot().indices.size()/3<=8192,"actual incision retains original geometry budgets")
  DirAccess.make_dir_recursive_absolute("res://reports")
  var proofs:Array=[]
  for proof in result.certificates:
   var item:Dictionary=proof.duplicate(true);var values:=PackedFloat64Array()
   for row in proof.rows:values.append_array(row)
   item.rows_le=Marshalls.raw_to_base64(values.to_byte_array());item.erase("rows");proofs.append(item)
  var f:=FileAccess.open("res://reports/material-reduction.json",FileAccess.WRITE);f.store_string(JSON.stringify({"removed":result.removed_vertices,"before_vertices":before.rest.size(),"after_vertices":after.rest.size(),"components":components(after),"area_error":area(after)-area(before),"cut":cut.reason,"before":audit_state(before),"after":audit_state(after),"point_sources":Array(result.point_sources),"certificates":proofs},"  ",true,true))
 var integrated=load("res://scripts/embedded_membrane.gd").new();integrated._state=saved.duplicate(true)
 var incision:Dictionary=integrated._incise_one(captured.patch)
 check(incision.valid and incision.changed,"normal incision path accepts owned exhaustion state under the original budgets: "+incision.reason)
 if incision.valid:
  var after:Dictionary=integrated.snapshot()
  check(after.steps==saved.steps and after.time==saved.time and after.events==saved.events+1,"reduction and incision publish one geometry event and never advance physical time")
  check(after.rest.size()<=4096 and absf(area(after)-area(saved))<1e-10,"integrated cut preserves limits and material")
 for patch in [PackedVector3Array([Vector3.ZERO,Vector3.ZERO,Vector3.ZERO]),PackedVector3Array([Vector3(2,2,2),Vector3(2.1,2,2),Vector3(2,2.1,2)])]:
  integrated._state=saved.duplicate(true);incision=integrated._incise_one(patch)
  check(not incision.changed and integrated.snapshot()==saved,"failed or no-op incision cannot publish preparatory reduction")
 print("Conservative material reduction: ",failures," failures");quit(1 if failures else 0)
