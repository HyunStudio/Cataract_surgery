extends SceneTree
var failures:=0
func check(ok:bool,message:String)->void:
	if not ok:failures+=1;push_error(message)
func _initialize()->void:
	var transfer=load("res://scripts/membrane_refinement.gd")
	var precise=load("res://scripts/membrane_precision.gd")
	for point in [Vector3(.31,.49,.79),Vector3(.528,.510009,.291948),Vector3(1.03,.98,.45)]:
		for weights in [Vector3(.1,.3,.6),Vector3(.37864077,.0918367,.5295225)]:
			var binding:={"ids":Vector3i(0,1,2),"weights":weights}
			var values:=PackedVector3Array([point,point,point])
			check(transfer.blend(values,binding)==point,"rounded barycentric weights preserve a constant material field exactly")
	var points:=PackedVector3Array([Vector3(.3,.5,.7),Vector3(.8,.2,.1),Vector3(-.4,.9,.3)])
	var bindings:Array=[]
	for weights in [Vector3(.1,.3,.6),Vector3(.37864077,.0918367,.5295225),Vector3(0.,.2,.8),Vector3(.7,.3,0.)]:bindings.append({"ids":Vector3i(0,1,2),"weights":weights})
	var expected:PackedVector3Array=precise.publish(precise.transfer(precise.pack(points),bindings))
	for i in range(bindings.size()):check(transfer.blend(points,bindings[i])==expected[i],"ordinary material transfer uses the same normalized scalar-double affine interpolation as the packed64 path")
	print("Material affine transfer: ",failures," failures");quit(1 if failures else 0)
