extends SceneTree
var failures:=0
func check(ok:bool,message:String)->void:
	if not ok:failures+=1;push_error(message)
func _initialize()->void:
	check(ClassDB.class_exists("MembraneFEMKernel"),"actual FEM extension registers")
	if failures:quit(1);return
	var kernel=ClassDB.instantiate("MembraneFEMKernel")
	check(kernel.has_method("contact_fem"),"actual extension exposes retained fine contact query")
	if failures:quit(1);return
	var request:={"controls":PackedFloat64Array([0.,0.,0.,1.,0.,0.,0.,0.,1.]),"weights":PackedFloat64Array([.8,.1,.1,.3,.6,.1,.3,.1,.6]),"segment":PackedFloat64Array([.25,.3,.25,.25,.3,.25]),"radius":.1}
	var before:=request.duplicate(true);var result:Dictionary=kernel.contact_fem(request)
	check(result.status==0 and result.values.size()==22 and result.gradient.size()==9 and result.hessian.size()==81,"typed contact bridge returns exact smooth-branch arrays")
	check(request==before,"contact bridge preserves caller arrays")
	if result.status!=0:quit(1);return
	check(absf(result.values[0]-.09)<1e-14 and absf(result.values[1]-.2)<1e-14,"actual bridge uses fine retained face distance")
	var maximum_gradient:=0.;var maximum_hessian:=0.;var epsilon:=2e-6
	for coordinate in range(9):
		var plus:=request.duplicate(true);var minus:=request.duplicate(true)
		plus.controls[coordinate]+=epsilon;minus.controls[coordinate]-=epsilon
		var a:Dictionary=kernel.contact_fem(plus);var b:Dictionary=kernel.contact_fem(minus)
		check(a.status==0 and b.status==0,"difference probes remain on regular fine face branch")
		if a.status!=0 or b.status!=0:quit(1);return
		maximum_gradient=maxf(maximum_gradient,absf(result.gradient[coordinate]-(a.values[0]-b.values[0])/(2*epsilon)))
		for row in range(9):maximum_hessian=maxf(maximum_hessian,absf(result.hessian[row*9+coordinate]-(a.gradient[row]-b.gradient[row])/(2*epsilon)))
	check(maximum_gradient<2e-10 and maximum_hessian<2e-8,"actual packed bridge derivatives match independent engine finite differences")
	var absent:=request.merged({"segment":PackedFloat64Array([.82,.03,.08,.82,.03,.08])},true)
	check(kernel.contact_fem(absent).values[1]>.1,"retained fine collider excludes empty parent material")
	var malformed:Array=[{},request.merged({"controls":[]},true),request.merged({"controls":PackedFloat64Array([0.])},true),request.merged({"weights":PackedInt32Array([0,1,2])},true),request.merged({"weights":PackedFloat64Array([1.])},true),request.merged({"segment":PackedFloat64Array([0.,0.,0.])},true),request.merged({"radius":".1"},true),request.merged({"radius":NAN},true)]
	for bad in malformed:
		var rejected:Dictionary=kernel.contact_fem(bad)
		check(rejected.status==-1 and rejected.values.is_empty() and rejected.gradient.is_empty() and rejected.hessian.is_empty(),"malformed contact input returns no fabricated geometry")
	var crossing:Dictionary=kernel.contact_fem(request.merged({"segment":PackedFloat64Array([.25,1.,.25,.25,-1.,.25])},true))
	check(crossing.status!=0 and crossing.values.is_empty() and crossing.gradient.is_empty() and crossing.hessian.is_empty(),"nonregular contact does not publish candidate arrays")
	print("Native embedded contact Godot bridge: ",failures," failures");quit(1 if failures else 0)
