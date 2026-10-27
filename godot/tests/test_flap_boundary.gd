extends SceneTree
var failures:=0
func check(ok:bool,message:String)->void:
	if not ok: failures+=1; push_error(message)
func _initialize()->void:
	check(FileAccess.file_exists("res://scripts/flap_boundary.gd"),"thin membrane boundary adapter exists")
	if failures: quit(1); return
	var shape=load("res://scripts/anterior_segment.gd").new()
	var boundary=load("res://scripts/flap_boundary.gd").new()
	check(boundary.configure(shape.cornea(),shape.iris(.96)),"actual cornea and iris can be indexed")
	var result:Dictionary=boundary.resolve(Vector3(0,.8,0),Vector3(0,1.6,0),false)
	check(result.valid and result.position.y<shape.cornea_inner(0.) and not result.outside,"intact corneal body blocks outward membrane passage")
	result=boundary.resolve(Vector3(.4,1.18,0),Vector3(.7,1.12,0),false)
	check(result.position.x>.62 and not result.outside,"membrane slides along corneal underside rather than sticking at first contact")
	boundary.wounds=[[Vector3(1.32,.8,-.25),Vector3(1.32,.8,.25)]]
	result=boundary.resolve(Vector3(1.32,.5,0),Vector3(1.32,1.,0),false)
	check(result.position.y>.99 and result.outside,"only actual opened channel permits exterior passage")
	result=boundary.resolve(Vector3(1.32,1.,0),Vector3(1.32,.5,0),true)
	check(not result.outside,"re-entry clears exterior state")
	result=boundary.resolve(Vector3(1.1,.7,0),Vector3(1.1,.1,0),false)
	check(result.contact and not boundary._blocked(result.position) and result.position.distance_to(Vector3(1.1,.1,0))>.02,"actual iris body blocks a membrane vertex")
	check(not boundary.configure({"positions":PackedVector3Array([Vector3(NAN,0,0)]),"triangles":PackedInt32Array([0,0,0])},shape.iris(.96)),"invalid boundary geometry rejects atomically")
	result=boundary.resolve(Vector3(0,.8,0),Vector3(0,1.6,0),false)
	check(result.position.y<1.3,"invalid replacement preserves existing valid boundary")
	check(boundary.get("portals")!=null,"entry model includes the external mouth of the corneal tunnel")
	if boundary.get("portals")!=null:
		boundary.portals=shape.portals.duplicate()
		result=boundary.resolve(Vector3(1.32,.75,0),Vector3(1.60,.80,0),false)
		check(result.position.x>1.59 and result.outside,"membrane can exit the radial tunnel mouth without crossing intact cornea")
	result=boundary.resolve(Vector3(1.38,.55,0),Vector3(1.50,.55,0),false)
	check(result.contact and result.position.x<1.416,"unpassed flap cannot escape below the limbal tunnel mouth")
	print("Flap boundary: ",failures," failures"); quit(1 if failures else 0)
