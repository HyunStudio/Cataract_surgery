extends SceneTree
var failures:=0
func check(ok:bool,message:String)->void:
	if not ok: failures+=1; push_error(message)
func area(data:Dictionary)->float:
	var sum:=0.
	for i in range(0,data.triangles.size(),3):
		var a:Vector3=data.positions[data.triangles[i]]; var b:Vector3=data.positions[data.triangles[i+1]]; var c:Vector3=data.positions[data.triangles[i+2]]
		sum+=(b-a).cross(c-a).length()*.5
	return sum
func _initialize()->void:
	var source=load("res://scripts/tissue_injury.gd")
	if source==null: push_error("structural injury component missing"); quit(1); return
	var model=source.new()
	var contact=load("res://scripts/surface_contact.gd").new()
	var data:Dictionary=model.surfaces.posterior
	var hit:Dictionary=contact.sweep(Vector3(0,.7,0),Vector3(0,.4,0),.01,data.positions,data.triangles)
	check(hit.hit,"initial posterior surface is closed")
	var record:={"surface":"posterior","point":hit.surface_point,"triangle":hit.triangle,"revision":0,"load":.03,"energy":0.,"cutting":false,"tool":"phaco"}
	var initial_area:=area(data)
	var initial:Dictionary=model.metrics()
	var idle:=record.duplicate(); idle.load=0.
	model.step(.02,[idle])
	check(model.metrics()==initial,"unpowered contact with no attempted loading cannot damage tissue")
	record.cutting=true; record.tool="knife"
	model.step(.02,[record])
	var metrics:Dictionary=model.metrics()
	check(metrics.posterior_breached and metrics.posterior_open_area>0.,"local blade puncture produces measured missing surface")
	check(metrics.posterior_open_area<.05,"local puncture cannot globally erase posterior capsule")
	data=model.surfaces.posterior
	check(absf(initial_area-area(data)-metrics.posterior_open_area)<.000001,"reported open area equals actual missing mesh area")
	hit=contact.sweep(Vector3(0,.7,0),Vector3(0,.4,0),.01,data.positions,data.triangles)
	check(not hit.hit,"actual puncture lets small sphere through its local opening")
	hit=contact.sweep(Vector3(.5,.7,0),Vector3(.5,.4,0),.01,data.positions,data.triangles)
	check(hit.hit,"distant posterior surface stays closed")
	check(data.positions.size()<=8192 and data.triangles.size()/3<=8192,"adaptive topology stays bounded")
	var snapshot:Dictionary=model.metrics()
	model.step(.02,[record])
	check(model.metrics()==snapshot,"stale topology revision cannot damage a different face")
	model.reset(); initial=model.metrics()
	var bad:=record.duplicate(); bad.point=Vector3(NAN,0,0)
	model.step(.02,[record,bad])
	check(model.metrics()==initial,"malformed second record rejects whole batch before first mutation")
	check(not model.metrics().posterior_breached,"reset restores original closed geometry")
	var inconsistent:=record.duplicate(); inconsistent.tool="forceps"; inconsistent.cutting=false; inconsistent.energy=1.; inconsistent.load=0.
	for i in range(30): model.step(.02,[inconsistent])
	check(not model.metrics().posterior_breached,"a non-energy tool cannot submit ultrasonic exposure")
	print("Tissue injury: ",failures," failures"); quit(1 if failures else 0)
