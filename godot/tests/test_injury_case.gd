extends SceneTree
var failures:=0
func check(ok:bool,message:String)->void:
	if not ok: failures+=1; push_error(message)
func _initialize()->void:
	var director=load("res://scripts/case_director.gd").new()
	for key in ["patient","side","equipment"]: director.prepare(key)
	var healthy:={"capsule":{"finite":true},"lens":{"finite":true,"remaining_mass":0.,"removed_mass":1.},"iol":{"finite":true,"delivered":1.,"deployed":true,"alignment":1.},"wound":true}
	director.observe(.02,healthy)
	for key in ["residual","implant","wound"]: director.inspect(key)
	var injury:=healthy.duplicate(true)
	injury["injury"]={"finite":true,"posterior_breached":true,"corneal_breached":false,"posterior_open_area":.005,"corneal_open_area":0.}
	director.observe(.02,injury)
	check(director.snapshot().alert=="tissue_injury","new measured structural injury causes modal assessment alert")
	check(not director.snapshot().inspection.wound and not director.snapshot().inspection.implant,"posterior damage invalidates closed-wound and supported implant checks")
	director.acknowledge()
	check(not director.finish(),"acknowledgment cannot erase structural injury")
	var second:=injury.duplicate(true); second.injury.corneal_breached=true; second.injury.corneal_open_area=.004
	director.observe(.02,second)
	check(director.snapshot().alert=="tissue_injury","a later injury on another surface triggers a new assessment")
	director.acknowledge()
	director.observe(.02,healthy)
	for key in ["residual","implant","wound"]: director.inspect(key)
	check(not director.finish(),"omitting later injury fields cannot erase earlier evidence")
	var stable:Dictionary=director.snapshot(); injury.injury.posterior_open_area=NAN
	director.observe(.02,injury)
	check(director.snapshot()==stable,"invalid injury evidence rejected atomically")
	injury.injury.posterior_open_area=.005; injury.injury.posterior_breached=false
	director.observe(.02,injury)
	check(director.snapshot()==stable,"positive missing area with false breach flag is rejected")
	director.abort("structural_injury_stop")
	check(director.snapshot().ending=="safe_stop","injured case preserves deliberate safe-stop outcome")
	print("Injury case: ",failures," failures"); quit(1 if failures else 0)
