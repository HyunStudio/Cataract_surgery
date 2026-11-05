extends SceneTree
const Normal=preload("res://scripts/material_normal_contact.gd")
var failures:=0
func check(ok:bool,message:String)->void:
	if not ok:failures+=1;push_error(message)
func _initialize()->void:
	var xyz:=PackedFloat64Array([-.6,.01,-.3,.6,.01,-.3,0.,.01,.6])
	var rows:Array=[{"nodes":PackedInt32Array([0,1,2]),"weights":PackedFloat64Array([.5,1./6.,1./3.])},{"nodes":PackedInt32Array([0,1,2]),"weights":PackedFloat64Array([1./6.,.5,1./3.])}]
	var state:={"xyz":xyz.duplicate(),"indices":PackedInt32Array([0,1,2]),"support":{"elements":PackedInt32Array([0,1,2]),"weights":PackedFloat64Array([1.,0.,0.,0.,1.,0.,0.,0.,1.])}}
	var context:={"bodies":1,"capsules":PackedFloat64Array([-.2,0.,0.,.2,0.,0.,.01])}
	for row in rows:row["face"]=0;row["barycentric"]=row.weights.duplicate()
	var bad:Array=rows.duplicate(true);bad[0].weights=PackedFloat64Array([0.,0.,1.])
	check(not Normal.force(state,xyz,PackedFloat64Array([0.,0.]),bad,context).valid,"normal row weights cannot replace their original face provenance")
	var dual:=PackedFloat64Array([.00075,.00075]);var before:=var_to_bytes([xyz,rows,context,dual])
	var answer:=Normal.force(state,xyz,dual,rows,context)
	check(answer.valid,"distributed normal reactions have independent finite point geometry")
	if answer.valid:
		for node in range(3):check(absf(answer.force[node*3+1]+.1)<1e-13,"two pressures distribute correct original force to all controls")
	check(var_to_bytes([xyz,rows,context,dual])==before,"independent normal validation never mutates accepted source arrays")
	check(not Normal.force(state,xyz,PackedFloat64Array([-.1,0.]),rows,context).valid,"negative normal force cannot pull tissue toward the tool")
	check(not Normal.force(state,xyz,PackedFloat64Array([NAN,0.]),rows,context).valid,"NaN reaction is rejected")
	check(not Normal.force(state,xyz,PackedFloat64Array([0.]),rows,context).valid,"unmatched point pressure array is rejected")
	var penetrated:=xyz.duplicate();penetrated[1]=.009;penetrated[4]=.009;penetrated[7]=.009
	check(not Normal.force(state,penetrated,dual,rows,context).valid,"point pressure cannot approve penetration")
	var separated:=xyz.duplicate();separated[1]=.02;separated[4]=.02;separated[7]=.02
	check(not Normal.force(state,separated,dual,rows,context).valid,"positive pressure cannot persist after separation")
	print("Material normal contact: ",failures," failures");quit(1 if failures else 0)
