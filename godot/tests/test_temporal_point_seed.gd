extends SceneTree
var failures:=0
func check(ok:bool,message:String)->void:
 if not ok:failures+=1;push_error(message)
func _initialize()->void:
 var query=load("res://scripts/material_normal_contact.gd").new()
 check(query.has_method("warm_start"),"point-only temporal seeds need explicit provenance and remapping")
 if failures:print("Temporal point seed: ",failures," failures");quit(1);return
 var xyz:=PackedFloat64Array([0.,0.,0.,1.,0.,0.,0.,0.,1.])
 var state:={"steps":7,"events":11,"xyz":xyz,"indices":PackedInt32Array([0,1,2]),"support":{"elements":PackedInt32Array([0,1,2]),"weights":PackedFloat64Array([1.,0.,0.,0.,1.,0.,0.,0.,1.])}}
 var center:={"face":0,"barycentric":PackedFloat64Array([1./3.,1./3.,1./3.]),"nodes":PackedInt32Array([0,1,2]),"weights":PackedFloat64Array([1./3.,1./3.,1./3.])}
 var corner:={"face":0,"barycentric":PackedFloat64Array([1.,0.,0.]),"nodes":PackedInt32Array([0,1,2]),"weights":PackedFloat64Array([1.,0.,0.])}
 var packet:=PackedFloat64Array([4.,4.,4.,4.,4.,4.,4.,4.,4.,4.,4.,4.,.1]);packet.resize(41)
 var context:={"previous":xyz,"times":PackedFloat64Array([.25,.5,1.]),"kinds":PackedInt32Array([0]),"packets":packet,"bodies":1}
 var seed:={"model":"material_points","source_steps":7,"source_events":11,"source_xyz":xyz.duplicate(),"kinds":context.kinds.duplicate(),"packets":packet.duplicate(),"rows":[center.duplicate(true)],"xyz":xyz.duplicate(),"times":PackedFloat64Array([.5,1.]),"dual":PackedFloat64Array([3.,0.]),"penalty":100.}
 var rows:Array=[center,corner];var before:=var_to_bytes([state,seed,rows,context])
 var answer:Dictionary=query.warm_start(state,seed,rows,context)
 check(answer.valid and answer.multiplier_seed==PackedFloat64Array([0.,0.,3.,0.,0.,0.]),"new rows and layers start at zero while matched material reactions retain exact values")
 check(answer.valid and answer.penalty_seed==seed.penalty,"temporal continuation retains conditioning and mapped reactions")
 var unchanged:Dictionary=context.duplicate(true);unchanged.times=seed.times.duplicate()
 var same:Dictionary=query.warm_start(state,seed,seed.rows,unchanged)
 check(same.valid and same.penalty_seed==seed.penalty,"identical constraint set keeps its converged numerical penalty")
 var time_only:Dictionary=query.warm_start(state,seed,seed.rows,context)
 check(time_only.valid and time_only.penalty_seed==seed.penalty,"new temporal layer keeps its model conditioning")
 var row_only:Dictionary=query.warm_start(state,seed,rows,unchanged)
 check(row_only.valid and row_only.penalty_seed==seed.penalty,"new material row keeps temporal model conditioning")
 var endpoint:Dictionary=seed.duplicate(true);endpoint.times=PackedFloat64Array([1.]);endpoint.dual=PackedFloat64Array([0.]);endpoint.penalty=1000000.
 var transition:Dictionary=query.warm_start(state,endpoint,rows,context)
 check(transition.valid and transition.penalty_seed==1.,"endpoint to temporal model initializes its numerical penalty while preserving owned seed")
 var reordered:Dictionary=query.warm_start(state,seed,[corner,center],context)
 check(reordered.valid and reordered.multiplier_seed==PackedFloat64Array([0.,0.,0.,3.,0.,0.]),"canonical material identity survives row reordering")
 if answer.valid:answer.initial[0]=9.;answer.multiplier_seed[0]=9.
 check(var_to_bytes([state,seed,rows,context])==before,"warm guesses cannot alias or mutate physical inputs")
 for patch in [{"model":"ordinary_faces"},{"source_steps":8},{"source_events":12},{"dual":PackedFloat64Array([3.])},{"dual":PackedFloat64Array([3.,-1.])},{"penalty":.1}]:
  var bad:Dictionary=seed.duplicate(true);bad.merge(patch,true)
  check(not query.warm_start(state,bad,rows,context).valid,"foreign stale or malformed point seed rejects")
 var bad:Dictionary=seed.duplicate(true);bad.source_xyz[0]=.001
 check(not query.warm_start(state,bad,rows,context).valid,"different physical source cannot inherit point multipliers")
 bad=seed.duplicate(true);bad.rows[0].weights=PackedFloat64Array([1.,0.,0.])
 check(not query.warm_start(state,bad,rows,context).valid,"seed rows must reconstruct from accepted source material")
 check(not query.warm_start(state,seed,[corner],context).valid,"seeded active material rows cannot disappear silently")
 check(not query.warm_start(state,seed,[center,center],context).valid,"duplicate destination rows cannot ambiguously receive a reaction")
 print("Temporal point seed: ",failures," failures");quit(1 if failures else 0)
