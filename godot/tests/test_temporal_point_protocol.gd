extends SceneTree
var failures:=0
func check(ok:bool,message:String)->void:
 if not ok:failures+=1;push_error(message)
class Backend extends RefCounted:
 var fault:=""
 var exchange:=false
 var calls:=0
 var budgets:Array=[]
 var row_counts:Array=[]
 var seeded_calls:=0
 func material_witness_fem(v:Dictionary)->Dictionary:
  var y:float=v.controls[1];var distance:float=.1-y
  return {"status":0,"values":PackedFloat64Array([distance*distance,absf(distance)-v.radius,.25,.1,.25,.25,y,.25,.5,.25,.25,0.,0.])}
 func solve_trajectory_material_points_fem(v:Dictionary)->Dictionary:
  calls+=1;budgets.append(v.budget);row_counts.append(v.face_nodes.size()/3)
  var stats:=PackedFloat64Array();stats.resize(16);stats[2]=3. if calls==1 else 4.
  stats[15]=1. if v.face_nodes.size()>0 else 0.
  if fault=="negative":stats[2]=-1.
  if fault=="over":stats[2]=v.budget+1.
  if fault=="fraction":stats[2]=.5
  var xyz:PackedFloat64Array=v.xyz.duplicate();var dual:=PackedFloat64Array();dual.resize(v.face_nodes.size()/3*v.kinds.size()*v.times.size())
  if exchange and calls==1:
   for i in range(xyz.size()/3):xyz[i*3+1]=.095
  if fault=="dual":dual=PackedFloat64Array([0.])
  if fault=="xyz":xyz[-1]=NAN
  var out:={"status":0,"xyz":xyz,"dual":dual,"stats":stats}
  if fault=="model":out.normal_rows=[]
  return out
 func solve_seeded_trajectory_material_points_fem(v:Dictionary)->Dictionary:
  seeded_calls+=1
  return solve_trajectory_material_points_fem(v)
func _initialize()->void:
 var query=load("res://scripts/material_normal_contact.gd").new()
 var xyz:=PackedFloat64Array([0.,0.,0.,1.,0.,0.,0.,0.,1.])
 var state:={"steps":0,"events":0,"xyz":xyz,"indices":PackedInt32Array([0,1,2]),"support":{"elements":PackedInt32Array([0,1,2]),"weights":PackedFloat64Array([1.,0.,0.,0.,1.,0.,0.,0.,1.])}}
 var packet:=PackedFloat64Array([.25,.1,.25,.25,.1,.25,.25,.1,.25,.25,.1,.25,.01]);packet.resize(41)
 var context:={"previous":xyz,"times":PackedFloat64Array([.5,1.]),"kinds":PackedInt32Array([0]),"packets":packet,"bodies":1}
 var request:={"xyz":xyz,"budget":10,"previous":xyz,"times":context.times,"kinds":context.kinds,"packets":packet}
 var before:=var_to_bytes([state,context,request])
 for fault in ["negative","over","fraction","model","dual","xyz"]:
  var backend:=Backend.new();backend.fault=fault
  check(not query.solve_trajectory(state,request,context,backend).valid,"malformed temporal backend cannot approve candidate: "+fault)
 var backend:=Backend.new();backend.exchange=true
 var result:Dictionary=query.solve_trajectory(state,request,context,backend)
 check(result.valid and result.work_iterations==7 and backend.budgets==[10,7],"successive material exchanges share original work budget")
 check(result.valid and backend.row_counts==[0,1] and backend.seeded_calls==0,"empty contact result has no algorithm penalty to reuse; newly acquired row starts cold")
 check(var_to_bytes([state,context,request])==before,"all protocol paths preserve accepted state and predictor ownership")
 var near_context:Dictionary=context.duplicate(true);near_context.packets[12]=.09
 var near_request:Dictionary=request.duplicate(true);near_request.packets=near_context.packets.duplicate()
 var near_before:=var_to_bytes([state,near_context,near_request])
 var near:=Backend.new();near.exchange=true
 var acquired:Dictionary=query.solve_trajectory(state,near_request,near_context,near)
 check(acquired.valid and near.row_counts==[0,1],"near feasible faces are inspected but acquire rows only when a full candidate actually violates them")
 check(var_to_bytes([state,near_context,near_request])==near_before,"violation acquisition preserves physical source and request")
 print("Temporal point protocol: ",failures," failures");quit(1 if failures else 0)
