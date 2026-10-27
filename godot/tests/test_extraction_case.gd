extends SceneTree
var failures:=0
func check(ok:bool,message:String)->void:
	if not ok: failures+=1; push_error(message)
func obs(extracted:float,retained:float)->Dictionary:
	return {"capsule_extraction_required":true,"capsule":{"finite":true,"extracted_flaps":int(extracted>0.),"extracted_area":extracted,"retained_detached_area":retained},"lens":{"finite":true,"remaining_mass":0.,"removed_mass":1.},"iol":{"finite":true,"delivered":1.,"deployed":true,"alignment":1.},"wound":true,"tool":"forceps","energy":0.,"movement":0.}
func _initialize()->void:
	var d=load("res://scripts/case_director.gd").new()
	for key in ["patient","side","equipment"]: d.prepare(key)
	d.observe(.02,obs(0.,.2))
	for key in ["residual","implant","wound"]: d.inspect(key)
	check(not d.finish(),"normal completion requires actual flap extraction in the default case")
	var omitted:=obs(0.,.2); omitted.erase("capsule_extraction_required")
	d.observe(.02,omitted)
	check(not d.finish(),"omitting extraction requirement later cannot bypass the gate")
	d.observe(.02,obs(.2,0.))
	check(d.finish(),"measured extraction with no retained flap satisfies normal ending")
	var event:=false
	for item in d.snapshot().timeline:
		if item.event=="capsule_flap_removed": event=true
	check(event,"actual removal gets a persistent case event")
	print("Extraction case: ",failures," failures"); quit(1 if failures else 0)
