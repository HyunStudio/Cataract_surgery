extends SceneTree
var failures:=0
func check(ok:bool,message:String)->void:
	if not ok: failures+=1; push_error(message)
func _initialize()->void:
	var shape=load("res://scripts/anterior_segment.gd").new()
	var injury=load("res://scripts/tissue_injury.gd").new()
	var shell:Dictionary=shape.cornea(); shell["closed_shell"]=true
	injury.reset({"cornea":shell,"posterior":shape.posterior()})
	var kernel=load("res://scripts/surface_contact.gd").new()
	var data:Dictionary=injury.surfaces.cornea
	var hit:Dictionary=kernel.sweep(Vector3(0,2,0),Vector3(0,.5,0),.01,data.positions,data.triangles)
	injury.step(.02,[{"surface":"cornea","point":hit.surface_point,"triangle":hit.triangle,"revision":data.revision,"load":.02,"energy":0.,"cutting":true,"tool":"knife"}])
	check(injury.metrics().corneal_integrity<1.,"outer shell damage changes actual surface")
	check(not injury.metrics().corneal_breached and injury.metrics().corneal_conductance==0.,"superficial outer damage cannot create a through-wall leak")
	hit=kernel.sweep(Vector3(0,1.,0),Vector3(0,1.5,0),.01,data.positions,data.triangles)
	injury.step(.02,[{"surface":"cornea","point":hit.surface_point,"triangle":hit.triangle,"revision":data.revision,"load":.02,"energy":0.,"cutting":true,"tool":"knife"}])
	check(injury.metrics().corneal_breached and injury.metrics().corneal_conductance>0.,"aligned missing outer and inner shell creates through-wall conductance")
	hit=kernel.sweep(Vector3(0,2,0),Vector3(0,.5,0),.005,data.positions,data.triangles)
	check(not hit.hit,"reported full breach has actual open passage across both boundaries")
	print("Corneal shell injury: ",failures," failures"); quit(1 if failures else 0)
