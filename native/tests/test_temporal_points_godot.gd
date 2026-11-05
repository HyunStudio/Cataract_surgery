extends SceneTree
var failures:=0
func check(ok:bool,message:String)->void:
 if not ok:failures+=1;push_error(message)
func _initialize()->void:
 var kernel=ClassDB.instantiate("MembraneFEMKernel")
 check(kernel!=null and kernel.has_method("solve_trajectory_material_points_fem"),"actual kernel requires separate temporal material-point API")
 check(kernel!=null and kernel.has_method("solve_seeded_trajectory_material_points_fem"),"material point seeds require a separate actual typed API")
 if failures:print("Native temporal material points: ",failures," failures");quit(1);return
 var p:Dictionary=JSON.parse_string(FileAccess.get_file_as_string("res://temporal_material_point.json"))
 for key in ["xyz","inverse","gradients","areas","grip_weights","targets","face_weights","capsules","previous","packets","times"]:p[key]=PackedFloat64Array(p[key])
 for key in ["nodes","grip_nodes","face_nodes","kinds"]:p[key]=PackedInt32Array(p[key])
 p.budget=int(p.budget)
 var before:=var_to_bytes(p);var result:Dictionary=kernel.solve_trajectory_material_points_fem(p)
 check(result.status==0 and result.dual.size()==2,"typed time-point candidate converges")
 if result.status==0:
  for node in range(3):check(absf(result.xyz[node*3]-1.15)<2e-9,"typed rotating-body middle contact reaches analytic final plane")
  check(absf(result.dual[0]-3.)<2e-8 and result.dual[1]==0.,"typed temporal reaction preserves t-scaled physical balance")
  check(result.stats[1]<=1e-8 and result.stats[12]<=1e-9 and result.stats[13]<=1e-11,"original physical gates remain")
  var warm:Dictionary=p.duplicate(true);warm.times=PackedFloat64Array([.25,.5,1.]);warm.initial=result.xyz.duplicate()
  warm.multiplier_seed=PackedFloat64Array([0.,result.dual[0],result.dual[1]]);warm.penalty_seed=float(result.stats[15])
  var warm_before:=var_to_bytes(warm);var seeded:Dictionary=kernel.solve_seeded_trajectory_material_points_fem(warm)
  check(seeded.status==0 and seeded.xyz==result.xyz and seeded.stats[2]<result.stats[2],"typed point-only seed reduces work without changing physical solution")
  check(var_to_bytes(warm)==warm_before,"typed point seed owns all predictor and multiplier arrays")
  result.xyz[0]=9.;result.dual[0]=9.
 check(var_to_bytes(p)==before,"typed temporal outputs cannot mutate caller inputs")
 var bad:Dictionary=p.duplicate(true);bad.face_weights[3]=1.;bad.face_weights[4]=0.;bad.face_weights[5]=0.
 check(kernel.solve_trajectory_material_points_fem(bad).status==-1,"ordinary face rows cannot masquerade as fixed material points")
 bad=p.duplicate(true);bad.times=PackedFloat64Array([.5])
 check(kernel.solve_trajectory_material_points_fem(bad).status==-1,"time sequence requires physical endpoint")
 bad=p.duplicate(true);bad.budget=0
 var stopped:Dictionary=kernel.solve_trajectory_material_points_fem(bad)
 check(stopped.status!=0 and stopped.xyz==p.xyz,"exhausted temporal candidate preserves original predictor")
 print("Native temporal material points: ",failures," failures");quit(1 if failures else 0)
