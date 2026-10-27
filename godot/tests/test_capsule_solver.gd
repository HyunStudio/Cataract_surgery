extends SceneTree
const Solver = preload("res://scripts/capsule_solver.gd")
var failures := 0

func check(value: bool, label: String) -> void:
	if not value:
		failures += 1
		printerr("FAIL capsule: ", label)

func _initialize() -> void:
	var s = Solver.new()
	var bench = Solver.new()
	bench.pressure_load = .15
	var started := Time.get_ticks_usec()
	for i in range(180): bench.step(1.0 / 60, Vector3(3, 3, 3), .06, false, false)
	print("Capsule benchmark: ", (Time.get_ticks_usec() - started) / 180000.0, " ms per 60Hz step;217 vertices,6 iterations,pressure .15")
	var rest: PackedVector3Array = s.positions.duplicate()
	check(rest.size() >= 180 and s.triangles.size() >= 900, "triangulated disk has spatial resolution")
	for i in range(120):
		s.step(1.0 / 60, Vector3(3, 3, 3), .06, false, false)
	var drift := 0.0
	for i in range(rest.size()): drift = maxf(drift, rest[i].distance_to(s.positions[i]))
	check(drift < .00001, "unloaded rest state stable and distant input isolated")
	check(s.metrics().broken_edges == 0, "no spontaneous tear")
	s.step(1.0 / 60, Vector3(0, .8, 0), .10, false, false)
	check(s.positions[0].distance_to(rest[0]) > .02, "local contact deforms membrane")
	for i in range(rest.size()):
		if s.anchored[i]: check(s.positions[i].distance_to(rest[i]) < .00001, "anchored rim fixed")
	s.reset()
	s.step(1.0 / 60, Vector3(0, .82, 0), .06, true, false)
	check(s.metrics().grasped >= 0, "local grip attaches vertex")
	var face_count: int = s.triangles.size()
	for i in range(40):
		s.step(1.0 / 60, Vector3(.012 * i, .82 + .018 * i, 0), .06, true, false)
	check(s.metrics().broken_edges > 0, "traction causes strain driven edge rupture")
	check(s.triangles.size() < face_count, "rupture changes rendered topology")
	check(s.metrics().finite, "traction remains finite")
	s.release()
	check(s.metrics().grasped == -1, "release detaches grasp")
	s.reset()
	s.step(1.0 / 60, Vector3(3, 3, 3), .06, true, true)
	check(s.metrics().grasped == -1 and s.metrics().broken_edges == 0, "distant grip and cut cannot affect tissue")
	s.step(1.0 / 60, Vector3(0, .82, 0), .09, false, true)
	check(s.metrics().broken_edges > 0, "cut breaks only contacted connections")
	s.reset()
	s.step(10000, Vector3(0, .81, 0), .08, false, false)
	s.step(NAN, Vector3(NAN, 0, 0), INF, true, true)
	s.step(1e-300, Vector3(0, .81, 0), .08, false, false)
	check(s.metrics().finite, "invalid dt and nonfinite inputs rejected")
	check(s.positions == s.rest_positions, "invalid inputs leave state unchanged")
	for dt in [.004, .016, .05]:
		for i in range(40): s.step(dt, Vector3(.1, .80, .1), .06, false, false)
	check(s.metrics().finite and is_finite(s.metrics().strain_energy), "bounded substeps finite for variable dt")
	s.reset()
	check(s.metrics().broken_edges == 0 and s.positions == rest, "reset restores mesh and constraints")
	s.pressure_load = .3
	for i in range(90): s.step(1.0 / 60, Vector3(3, 3, 3), .06, false, false)
	check(s.positions[0].y > rest[0].y + .0001, "positive pressure force bows membrane outward")
	for i in range(rest.size()):
		if s.anchored[i]: check(s.positions[i] == rest[i], "pressure retains anchored rim")
	check(s.metrics().finite, "pressure evolution finite")
	s.reset(); s.pressure_load = -.3
	for i in range(90): s.step(1.0 / 60, Vector3(3, 3, 3), .06, false, false)
	check(s.positions[0].y < rest[0].y - .0001, "negative pressure reverses load direction")
	s.reset(); s.pressure_load = NAN
	s.step(1.0 / 60, Vector3(3, 3, 3), .06, false, false)
	check(s.positions == s.rest_positions and s.metrics().finite, "invalid pressure rejected")
	s.pressure_load = 1e30
	s.step(1.0 / 60, Vector3(3, 3, 3), .06, false, false)
	check(s.positions == s.rest_positions, "unbounded pressure rejected")
	s.reset(); s.passive_tips = PackedVector3Array([Vector3(0, .8, 0)])
	s.step(1.0 / 60, Vector3(3, 3, 3), .1, false, false)
	check(s.positions[0].distance_to(s.rest_positions[0]) > .02, "retained instrument has passive sphere contact")
	s.reset(); s.passive_tips = PackedVector3Array([Vector3(NAN, 0, 0)])
	s.step(1.0 / 60, Vector3(0, .81, 0), .1, false, false)
	check(s.positions == s.rest_positions and s.metrics().finite, "invalid passive tips rejected before mutation")
	s.reset()
	var tools: Array[Dictionary] = [
		{"hand": 0, "tip": Vector3(0, .82, 0), "radius": .05, "grip": true, "cut": false},
		{"hand": 1, "tip": Vector3(.1466667, .819444, 0), "radius": .05, "grip": true, "cut": false}]
	s.step_tools(1.0 / 60, tools)
	var grasp_metrics: Dictionary = s.metrics()
	check(grasp_metrics.grasps.size() == 2 and grasp_metrics.grasps[0] != grasp_metrics.grasps[1], "two hands hold distinct local vertices")
	check(grasp_metrics.integration_steps == 1, "bimanual tools integrate once")
	var left_vertex: int = grasp_metrics.grasps[0]
	s.release_hand(1)
	check(s.metrics().grasps.has(0) and not s.metrics().grasps.has(1), "release one hand preserves other")
	tools[0].tip = Vector3(0, .85, 0)
	tools[1].grip = false
	tools[1].tip = Vector3(.3, .82, 0)
	for i in range(5): s.step_tools(1.0 / 60, tools)
	check(s.metrics().grasps[0] == left_vertex, "left grasp survives other hand operations")
	check(s.positions[left_vertex].distance_to(tools[0].tip) < .00001, "retained left grasp tracks its own target")
	var before: PackedVector3Array = s.positions.duplicate()
	tools[1].tip = Vector3(NAN, 0, 0)
	s.step_tools(1.0 / 60, tools)
	check(s.positions == before and s.metrics().grasps.has(0), "invalid tool batch rejects atomically")
	s.release()
	check(s.metrics().grasps.is_empty(), "release all hands")
	s.reset()
	tools = [{"hand": 1, "tip": Vector3(0, .82, 0), "radius": .09, "grip": false, "cut": true}]
	s.step_tools(1.0 / 60, tools)
	check(s.metrics().broken_edges > 0, "second hand cuts local topology")
	s.reset(); s.pressure_load = .3
	tools = [{"hand": 0, "tip": Vector3(3, 3, 3), "radius": .05, "grip": false, "cut": false}, {"hand": 1, "tip": Vector3(3, 3, 3), "radius": .05, "grip": false, "cut": false}]
	for i in range(30): s.step_tools(1.0 / 60, tools)
	check(s.positions[0].y > s.rest_positions[0].y and s.metrics().finite, "bimanual interface retains pressure force")
	var single = Solver.new()
	var batch = Solver.new()
	single.pressure_load = .2; batch.pressure_load = .2
	single.passive_tips = PackedVector3Array([Vector3(.3, .81, 0)])
	tools = [{"hand": 0, "tip": Vector3(0, .81, 0), "radius": .06, "grip": false, "cut": false}, {"hand": 1, "tip": Vector3(.3, .81, 0), "radius": .06, "grip": false, "cut": false}]
	for i in range(10):
		single.step(1.0 / 60, tools[0].tip, .06, false, false)
		batch.step_tools(1.0 / 60, tools)
	check(single.positions == batch.positions and batch.metrics().integration_steps == 10, "batch and legacy wrapper have identical single integration")
	print("Capsule solver tests: ", "PASS" if failures == 0 else str(failures) + " failures")
	quit(0 if failures == 0 else 1)
