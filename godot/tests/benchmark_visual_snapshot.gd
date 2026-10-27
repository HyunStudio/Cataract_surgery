extends SceneTree
func _initialize()->void:
	var lens=load("res://scripts/lens_fluid_solver.gd").new()
	var capsule=load("res://scripts/capsule_solver.gd").new()
	var started:=Time.get_ticks_usec(); var count:=500
	var rich:Dictionary={}
	for i in range(count): rich={"particles":lens.particles.duplicate(true),"bonds":lens.bonds.duplicate(true)}
	var rich_ms:=(Time.get_ticks_usec()-started)/1000./count
	started=Time.get_ticks_usec()
	var packed:Dictionary={}
	for i in range(count): packed=lens.visual_state()
	var packed_ms:=(Time.get_ticks_usec()-started)/1000./count
	var adapter=load("res://scripts/visual_snapshot.gd")
	var equal:bool=adapter.expand_lens(packed)==rich
	started=Time.get_ticks_usec()
	var cap_rich:Array=[]
	for i in range(count): cap_rich=capsule.edges.duplicate(true)
	var cap_rich_ms:=(Time.get_ticks_usec()-started)/1000./count
	started=Time.get_ticks_usec()
	var cap:Dictionary={}
	for i in range(count): cap=capsule.visual_state()
	var cap_ms:=(Time.get_ticks_usec()-started)/1000./count
	equal=equal and adapter.expand_capsule(cap).edges==cap_rich
	var report:={"capsule_rich_copy_ms":cap_rich_ms,"capsule_packed_copy_ms":cap_ms,"samples":count,"rich_copy_ms":rich_ms,"packed_copy_ms":packed_ms,"same_rich_values":equal}
	DirAccess.make_dir_recursive_absolute(ProjectSettings.globalize_path("res://reports"))
	var file:=FileAccess.open("res://reports/benchmark-visual-snapshot.json",FileAccess.WRITE)
	file.store_string(JSON.stringify(report,"  ")); print(JSON.stringify(report)); quit(0 if equal else 1)
