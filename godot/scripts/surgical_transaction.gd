extends RefCounted
## Explicit ownership graph for the fallible portion of one simulator tick.
const State=preload("res://scripts/model_checkpoint.gd")
const MODELS:=["capsule","lens","incision","injury","anatomy"]
const APP_FIELDS:=["metrics","previous_tips","_body_poses","_resolved_grips","_contact_records","last_contacts","_last_injury","_last_lens","_last_capsule","_last_iol","_flap_revision"]

static func capture(app:Object)->Dictionary:
	var state:Dictionary={"models":{},"rigs":[],"app":{}}
	for key in MODELS: state.models[key]=app.get(key).capture_state()
	for rig in app.rigs: state.rigs.append(rig.capture_state())
	for key in APP_FIELDS: state.app[key]=State.clone_value(app.get(key))
	if app._flap_boundary: state["boundary"]=app._flap_boundary.capture_state()
	return state

static func restore(app:Object,state:Dictionary)->void:
	for key in MODELS: app.get(key).restore_state(state.models[key])
	for i in range(state.rigs.size()): app.rigs[i].restore_state(state.rigs[i])
	for key in APP_FIELDS: app.set(key,State.clone_value(state.app[key]))
	# Injury owns the surface graph. Consumers must share the restored objects.
	app.anatomy.cornea=app.injury.surfaces.cornea
	app.anatomy.posterior=app.injury.surfaces.posterior
	if state.has("boundary"): app._flap_boundary.restore_state(state.boundary)
	app._rigid_body.invalidate_cache()
	app.capsule.invalidate_solver_cache()
