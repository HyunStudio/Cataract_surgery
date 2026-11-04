extends SceneTree
var failures:=0
func check(ok:bool,message:String)->void:
 if not ok:failures+=1;push_error(message)
func model():
 var tissue=load("res://scripts/embedded_membrane.gd").new()
 tissue.initialize(PackedVector3Array([Vector3.ZERO,Vector3.RIGHT,Vector3.BACK]),PackedInt32Array([0,1,2]),PackedByteArray([0,0,0]),1.)
 return tissue
func point(tissue,held:Dictionary)->PackedFloat64Array:
 var state:Dictionary=tissue.snapshot();var out:=PackedFloat64Array([0.,0.,0.])
 for j in range(3):
  for axis in range(3):out[axis]+=state.xyz[held.nodes[j]*3+axis]*held.weights[j]
 return out
func cut_cases()->void:
 var helper=load("res://scripts/material_attachment.gd")
 check(helper.has_method("remap_cut"),"material attachment needs child-face identity across an actual incision")
 if failures:return
 var patch:=PackedVector3Array([Vector3(.25,-.2,-1),Vector3(.25,.2,-1),Vector3(.25,0,2)])
 for bary in [PackedFloat64Array([.7,.1,.2]),PackedFloat64Array([.6875,.125,.1875])]:
  var tissue=model();check(tissue.grasp_material(0,0,bary).valid,"prepare interior material hold")
  var before:Dictionary=tissue.snapshot();var result:Dictionary=tissue._incise_one(patch)
  check(result.valid and result.changed and tissue.snapshot().grasps.has(0),"changed cut preserves the unique held material bank including ordinary child tessellation edges")
  if tissue.snapshot().grasps.has(0):
   var held:Dictionary=tissue.snapshot().grasps[0];var next:Dictionary=tissue._attachments({})
   check(next.valid and held.target==before.grasps[0].target,"cut preserves material target and native constraint")
   for axis in range(3):check(absf(point(tissue,held)[axis]-held.target[axis])<1e-9,"remapped controls evaluate the same physical held point")
  check(tissue.snapshot().steps==before.steps and tissue.snapshot().time==before.time,"material remap does not advance accepted physical time")
 var ambiguous=model();ambiguous.grasp_material(0,0,PackedFloat64Array([.5,.25,.25]));var result:Dictionary=ambiguous._incise_one(patch)
 check(result.valid and ambiguous.snapshot().grasps.is_empty(),"incision through a held point never selects one of distinct new crack banks arbitrarily")
 var slit=model();slit.grasp_material(0,0,PackedFloat64Array([.5,.25,.25]))
 result=slit._incise_one(PackedVector3Array([Vector3(.25,-.1,.1),Vector3(.25,.1,.1),Vector3(.25,0,.5)]))
 check(result.valid and slit.snapshot().support.controls.size()==3 and slit.snapshot().grasps.is_empty(),"partial slit banks remain distinct even when their current mechanical control rows coincide")
 var tiny=model();tiny.grasp_material(0,0,PackedFloat64Array([1.,1e-200,0.]));var saved:Dictionary=tiny.snapshot();result=tiny._incise_one(patch)
 check(not result.valid and tiny.snapshot()==saved,"uncertifiable positive material coordinates reject a changed cut atomically")
 var refined=model();refined._incise_one(patch);var state:Dictionary=refined.snapshot();var face:=0
 var bary:=PackedFloat64Array([.25,.25,.5]);var expected:=PackedFloat64Array([0.,0.,0.])
 for j in range(3):
  for k in range(3):expected[j]+=bary[k]*state.support.weights[face*9+k*3+j]
 check(refined.grasp_material(0,face,bary).valid and refined.snapshot().grasps[0].weights==expected,"fine-face interpolation composes with accepted B rather than treating local barycentric values as original control weights")
 var captured:Dictionary=FileAccess.open("res://tests/fixtures/operative-vertex-budget-state.bin",FileAccess.READ).get_var();var large=model();large._state=captured.state
 check(large.grasp_material(0,0,bary).valid,"material hold registers on the captured retained surface")
 var reduced:Dictionary=load("res://scripts/embedded_material_reduce.gd").simplify(large.snapshot(),128)
 check(reduced.valid and reduced.changed and reduced.state.grasps.has(0),"near-budget reduction supports a nonvertex attachment and protects its face")
 if reduced.valid:check(reduced.state.grasps[0].nodes==large.snapshot().grasps[0].nodes and reduced.state.grasps[0].weights==large.snapshot().grasps[0].weights,"reduction cannot refit the held coarse material row")
func _initialize()->void:
 var tissue=model()
 check(tissue.has_method("grasp_material"),"actual finite-jaw connection needs face-interior material attachment, not nearest display vertex")
 if failures:quit(1);return
 var bary:=PackedFloat64Array([.2,.3,.5]);var saved:=bary.duplicate();var before:Dictionary=tissue.snapshot()
 var result:Dictionary=tissue.grasp_material(0,0,bary)
 check(result.valid and result.changed and bary==saved,"registration owns and preserves input material weights")
 var after:Dictionary=tissue.snapshot();var held:Dictionary=after.grasps[0]
 check(held.kind=="material" and held.face==0 and held.nodes==PackedInt32Array([0,1,2]) and held.weights==bary,"original face interior has the expected coarse material row")
 check(held.target==PackedFloat64Array([.3,0.,.5]) and point(tissue,held)==held.target,"target is the accepted material point, never a neighboring display vertex")
 check(after.xyz==before.xyz and after.previous==before.previous and after.steps==before.steps and after.time==before.time,"grasp setup cannot move physical state or clock")
 result=tissue.grasp_material(0,0,bary)
 check(result.valid and not result.changed,"same material attachment is idempotent")
 check(not tissue.grasp_material(1,0,bary).valid,"two hands cannot silently occupy the identical material row")
 var request:Dictionary=tissue._attachments({})
 check(request.valid and request.nodes==held.nodes and request.weights==held.weights and request.targets==held.target,"native attachment request uses composed material row")
 after.grasps[0].weights[0]=9.;check(tissue.snapshot().grasps[0].weights==saved,"public snapshots cannot mutate live material rows")
 for bad in [PackedFloat64Array([0.,0.]),PackedFloat64Array([-1.,1.,1.]),PackedFloat64Array([NAN,0.,1.]),PackedFloat64Array([0.,0.,0.])]:
  var copy:Dictionary=tissue.snapshot();check(not tissue.grasp_material(1,0,bad).valid and tissue.snapshot()==copy,"invalid material registration is atomic")
 tissue.release_hand(0);check(tissue.snapshot().grasps.is_empty(),"material attachment releases through the existing hand API")
 check(tissue.grasp(0,1).valid and tissue._attachments({}).valid,"legacy vertex attachment still works")
 check(not tissue.grasp_material(1,0,PackedFloat64Array([0.,1.,0.])).valid,"material API cannot occupy a legacy-held vertex")
 tissue.release_hand(0);tissue.grasp_material(0,0,PackedFloat64Array([0.,1.,0.]))
 check(not tissue.grasp(1,1).valid,"legacy API cannot occupy the material-held vertex")
 cut_cases()
 print("Material point attachment: ",failures," failures");quit(1 if failures else 0)
