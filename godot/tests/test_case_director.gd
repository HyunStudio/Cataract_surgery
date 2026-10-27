extends SceneTree
var failures := 0
func check(ok: bool, message: String) -> void:
	if not ok: failures += 1; push_error(message)
func observation(remaining := .005, aligned := 1.) -> Dictionary:
	return {"capsule":{"finite":true,"broken_edges":6},"lens":{"finite":true,"remaining_mass":remaining,"removed_mass":1.-remaining},"iol":{"finite":true,"delivered":1.,"deployed":true,"alignment":aligned},"wound":true,"tool":"phaco","energy":.4,"movement":.2}
func _initialize() -> void:
	if not ResourceLoader.exists("res://scripts/case_director.gd"):
		check(false,"case director implementation missing"); quit(1); return
	var script = load("res://scripts/case_director.gd")
	var d = script.new()
	d.reset("standard",7)
	check(not d.ready() and not d.finish(),"briefing cannot finish or operate")
	d.prepare("patient"); d.prepare("side")
	check(not d.ready(),"equipment preparation mandatory")
	d.prepare("equipment")
	check(d.ready(),"all three preparation checks enable operation")
	d.observe(.02,observation(.5))
	check(not d.inspect("residual") and not d.finish(),"residual tissue blocks inspection and finish")
	d.observe(.02,observation(.005,.2))
	check(not d.inspect("implant"),"offcenter implant blocks final inspection")
	d.observe(.02,observation())
	var kinds: Array = []
	for event in d.snapshot().timeline: kinds.append(event.event)
	check("material_removed" in kinds and "implant_deployed" in kinds,"timeline captures measured physical milestones")
	check(not d.finish(),"physical state alone does not replace final inspections")
	for key in ["residual","implant","wound"]: check(d.inspect(key),"valid final check "+key)
	check(d.finish() and d.snapshot().ending=="completed","observed physics plus inspection completes encounter")
	var closed: Dictionary = d.snapshot()
	d.observe(.02,observation(.9)); d.abort("late")
	check(d.snapshot()==closed,"terminal outcome and evidence cannot be overwritten")
	d.reset("standard",8)
	d.abort("operator_stop")
	check(d.snapshot().ending=="safe_stop","safe stop distinct from completed operation")
	var a = script.new(); var b = script.new()
	for director in [a,b]:
		director.reset("motion",42)
		for key in ["patient","side","equipment"]: director.prepare(key)
	for i in range(1200):
		a.observe(.02,observation(.8)); b.observe(.02,observation(.8))
	check(a.snapshot().alert!="" and a.snapshot()==b.snapshot(),"seeded active-time motion alert deterministic")
	a.acknowledge()
	check(a.snapshot().alert=="","acknowledge records response and clears recoverable alert")
	var stable: Dictionary = a.snapshot()
	a.observe(NAN,observation()); a.observe(.02,{"lens":{"remaining_mass":NAN}})
	check(a.snapshot()==stable,"malformed observations rejected atomically")
	d.reset("dense",3)
	for key in ["patient","side","equipment"]: d.prepare(key)
	d.observe(.02,observation())
	for key in ["residual","implant","wound"]: d.inspect(key)
	d.observe(.02,observation(.5))
	check(not d.snapshot().inspection.residual and not d.finish(),"deteriorating physical evidence invalidates stale inspections")
	print("Case director: ",failures," failures"); quit(1 if failures else 0)
