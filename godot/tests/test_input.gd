extends SceneTree

var failures := 0
func check(ok: bool, message: String) -> void:
	if not ok:
		failures += 1
		push_error(message)

func _initialize() -> void:
	var script = load("res://scripts/operative_input.gd")
	if script == null:
		push_error("operative input adapter missing")
		quit(1)
		return
	var adapter = script.new()
	check(not adapter.allowed, "must not activate before fresh press")
	adapter.press(true)
	check(adapter.allowed, "fresh press in viewport arms input")
	adapter.block()
	adapter.press(true)
	check(not adapter.allowed, "blocked held button cannot rearm")
	adapter.release()
	adapter.press(false)
	check(not adapter.allowed, "UI press cannot activate input")
	adapter.release()
	adapter.press(true)
	check(adapter.allowed, "release then valid press rearms")
	var samples = adapter.sweep(Vector3(.3,.5,.04), Vector3(.7,.5,.04))
	check(samples.size() >= 20, "sweep must sample fast motion")
	check(samples[-1].is_equal_approx(Vector3(.7,.5,.04)), "sweep ends at real tip")
	check(adapter.sweep(Vector3(NAN,0,0), Vector3.ZERO).is_empty(), "nonfinite motion ignored")
	print("Input tests: ", failures, " failures")
	quit(1 if failures else 0)
