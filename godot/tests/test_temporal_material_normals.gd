extends SceneTree
var failures:=0
func check(ok:bool,message:String)->void:
 if not ok:failures+=1;push_error(message)
func _initialize()->void:
 var query=load("res://scripts/material_normal_contact.gd").new()
 check(query.has_method("force_trajectory"),"temporal material reactions need independent time-scaled force validation")
 if failures:print("Temporal material normal force: ",failures," failures");quit(1);return
 var old:=PackedFloat64Array([1.05,-1.,-1.,1.05,1.,-1.,1.05,0.,2.]);var end:=old.duplicate()
 for i in range(3):end[i*3]=1.15
 var state:={"xyz":old,"indices":PackedInt32Array([0,1,2]),"support":{"elements":PackedInt32Array([0,1,2]),"weights":PackedFloat64Array([1.,0.,0.,0.,1.,0.,0.,0.,1.])}}
 var h:=sqrt(.5);var packet:=PackedFloat64Array([0.,-1.,0.,0.,-1.,0.,0.,1.,0.,0.,1.,0.,.1,0.,0.,0.,0.,0.,0.,0.,0.,-h,h,0.,0.,h,h,1.,0.,0.,1.,0.,0.,1.,0.,0.,1.,0.,0.,0.,1.])
 var context:={"times":PackedFloat64Array([.5,1.]),"previous":old,"kinds":PackedInt32Array([1]),"packets":packet,"bodies":1}
 var rows:Array=[{"face":0,"barycentric":PackedFloat64Array([1./3.,1./3.,1./3.]),"nodes":PackedInt32Array([0,1,2]),"weights":PackedFloat64Array([1./3.,1./3.,1./3.])}]
 var dual:=PackedFloat64Array([3.,0.]);var before:=var_to_bytes([state,end,rows,dual,context])
 var result:Dictionary=query.force_trajectory(state,end,dual,rows,context)
 check(result.valid,"middle-path material reaction independently validates")
 if result.valid:
  for i in range(3):check(absf(result.force[i*3]+10.)<1e-10 and absf(result.force[i*3+1])<1e-10,"half-time reaction distributes original force with t factor")
 check(var_to_bytes([state,end,rows,dual,context])==before,"time reaction validation never changes accepted histories or query ownership")
 check(not query.force_trajectory(state,end,PackedFloat64Array([3.,-1.]),rows,context).valid,"negative later-layer pressure rejects")
 check(not query.force_trajectory(state,end,PackedFloat64Array([3.]),rows,context).valid,"missing temporal dual entries reject")
 for times in [PackedFloat64Array([0.,1.]),PackedFloat64Array([.5,.5,1.]),PackedFloat64Array([.5])]:
  var bad:Dictionary=context.duplicate(true);bad.times=times
  check(not query.force_trajectory(state,end,dual,rows,bad).valid,"unsupported sampling cannot publish a force")
 var bad:Dictionary=context.duplicate(true);bad.previous[-1]=NAN
 check(not query.force_trajectory(state,end,dual,rows,bad).valid,"invalid previous coordinates reject before force arithmetic")
 var corrupt:Array=rows.duplicate(true);corrupt[0].weights=PackedFloat64Array([1.,0.,0.])
 check(not query.force_trajectory(state,end,dual,corrupt,context).valid,"time layers cannot replace original material provenance")
 var pose:Dictionary=load("res://scripts/recorded_body_pose.gd").sample(context.kinds,context.packets,1.)
 var single:Dictionary=context.duplicate(true);single.times=PackedFloat64Array([1.]);single.capsules=pose.capsules
 var static_force:Dictionary=query.force(state,end,PackedFloat64Array([0.]),rows,single)
 var time_force:Dictionary=query.force_trajectory(state,end,PackedFloat64Array([0.]),rows,single)
 check(var_to_bytes(static_force)==var_to_bytes(time_force),"endpoint-only independent force retains scalar bits")
 print("Temporal material normal force: ",failures," failures");quit(1 if failures else 0)
