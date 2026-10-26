extends SceneTree
const Solver = preload("res://scripts/capsule_solver.gd")
var failures := 0

func check(value: bool, label: String) -> void:
	if not value:
		failures += 1
		printerr("FAIL capsule: ", label)

func _initialize() -> void:
	var s = Solver.new()
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
	print("Capsule solver tests: ", "PASS" if failures == 0 else str(failures) + " failures")
	quit(0 if failures == 0 else 1)
