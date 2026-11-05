extends SceneTree
func _initialize()->void:
 var saved:Dictionary=FileAccess.open("res://tests/fixtures/operative-motion179-state.bin",FileAccess.READ).get_var()
 var model=load("res://scripts/embedded_membrane.gd").new();model._state=saved.state.duplicate(true)
 var backend=ClassDB.instantiate("MembraneFEMKernel");var guard=ClassDB.instantiate("MembraneContactKernel")
 var motion:Dictionary=saved.motion.duplicate(true);motion.guard=guard
 var started:=Time.get_ticks_usec()
 var result:Dictionary=model.advance_contact(saved.dt,saved.force,backend,saved.mu,saved.lambda,motion,saved.damping,saved.budget,saved.targets)
 var elapsed:=Time.get_ticks_usec()-started
 DirAccess.make_dir_recursive_absolute("res://reports")
 FileAccess.open("res://reports/material-face-state.bin",FileAccess.WRITE).store_var({"result":result,"state":model.snapshot()})
 var summary:={"valid":result.valid,"elapsed_us":elapsed,"force_inf":result.get("force_inf",INF),"iterations":result.get("trajectory_iterations",-1),"state_sha256":FileAccess.get_sha256("res://reports/material-face-state.bin")}
 FileAccess.open("res://reports/material-face-time.json",FileAccess.WRITE).store_string(JSON.stringify(summary,"  ",true,true))
 print("Material face owned179: ",JSON.stringify(summary));quit(0 if result.valid else 1)
