extends SceneTree

const Session = preload("res://scripts/procedure_session.gd")
var failures := 0

func check(value: bool, label: String) -> void:
	if not value:
		failures += 1
		printerr("FAIL: ", label)

func arm(s, tool: String) -> void:
	s.end_stroke()
	s.select_tool(tool)
	s.begin_stroke()

func hold(s, p: Vector3, seconds: float = 1.5) -> void:
	for i in range(int(seconds * 60)):
		s.act(p, 1.0 / 60.0)
		s.tick(1.0 / 60.0)

func entry(s) -> void:
	arm(s, "knife")
	for i in range(31):
		s.act(Vector3(.76 + .15 * i / 30.0, .5, .12), 1.0 / 60.0)

func capsule(s) -> void:
	arm(s, "forceps")
	for i in range(97):
		var a := TAU * i / 96.0
		s.act(Vector3(.5 + cos(a) * .22, .5 + sin(a) * .22, .04), 1.0 / 60.0)

func through_hydro(s) -> void:
	s.confirm()
	s.confirm()
	entry(s)
	capsule(s)
	arm(s, "cannula")
	hold(s, Vector3(.68, .5, -.02))

func complete(s) -> void:
	through_hydro(s)
	if s.alert != "":
		s.assess()
	arm(s, "phaco")
	for r in s.eye.regions:
		s.end_stroke()
		s.begin_stroke()
		hold(s, Vector3(r.x, r.y, -.08), 2.0)
	arm(s, "ia")
	for r in s.eye.regions:
		s.end_stroke()
		s.begin_stroke()
		hold(s, Vector3(r.x, r.y, -.06), 1.2)
	arm(s, "injector")
	hold(s, Vector3(.5, .5, .02), 2.0)
	arm(s, "manipulator")
	hold(s, Vector3(.5, .5, .02), 2.0)
	check(not s.confirm(), "closure requires final checks")
	s.verify("alignment")
	s.verify("wound")
	s.verify("handoff")
	s.confirm()

func _initialize() -> void:
	var s = Session.new()
	check(s.snapshot().score == 0, "initial score is unearned")
	s.abort()
	check(s.snapshot().score < 100, "premature safe stop is not full completion score")
	s.reset("normal", 1)
	s.toggle_pause()
	var pause_replay = s.replay_log(s.export_log())
	check(pause_replay.get("ok", false) and pause_replay.get("snapshot", {}) == s.snapshot(), "pause is replayable without later commands")
	s.toggle_pause()
	s.confirm(); s.confirm(); arm(s, "knife")
	s.toggle_pause(); s.toggle_pause(); s.begin_stroke()
	s.act(Vector3(.76, .5, .12), .02)
	s.act(Vector3(.91, .5, .12), .02)
	check(s.phase == "ENTRY", "toggle pause requires release on resume")
	s.reset("normal", 1)
	complete(s)
	check(s.snapshot().score >= 95, "completed normal route earns high score")
	check(s.phase == "RECOVERY", "complete normal route: " + s.phase)
	check(s.eye.opacity < .02 and s.eye.cortex < .02, "all regions removed")
	check(s.eye.iol_alignment >= .99, "IOL centered")
	var replay = s.replay_log(s.export_log())
	check(replay.get("ok", false), "semantic replay valid")
	check(replay.get("snapshot", {}) == s.snapshot(), "replay final snapshot equal")
	check(not s.replay_log("{bad").get("ok", true), "reject malformed replay")
	var raw: String = s.export_log()
	check(not s.replay_log(raw.replace('"version":2', '"version":1')).get("ok", true), "reject old replay")
	s.reset("normal", 42)
	check(s.phase == "PREOP" and s.eye.opacity == 1.0, "restart restores tissues")
	s.confirm(); s.confirm()
	arm(s, "forceps")
	hold(s, Vector3(.8, .5, .12))
	check(s.progress == 0.0, "wrong tool blocked")
	arm(s, "knife")
	hold(s, Vector3(.8, .5, -.2))
	check(s.progress == 0.0, "wrong depth blocked")
	entry(s)
	check(s.phase == "CAPSULE", "entry path completion")
	s.select_tool("forceps")
	s.begin_stroke()
	hold(s, Vector3(.72, .5, .04))
	check(s.progress == 0.0, "held transition requires release")
	arm(s, "forceps")
	s.act(Vector3(.72, .5, .04), .0167)
	s.act(Vector3(.28, .5, .04), .0167)
	check(s.progress == 0.0, "swept invalid capsule crossing blocked")
	capsule(s)
	check(s.phase == "HYDRO", "continuous capsule completion")
	for hazard in ["movement", "monitor", "capsule"]:
		s.reset(hazard, 7)
		through_hydro(s)
		check(s.alert != "", "hazard triggered " + hazard)
		var old: float = s.eye.opacity
		arm(s, "phaco"); hold(s, Vector3(.66, .5, -.08))
		check(s.eye.opacity == old, "alert blocks tissue input")
		s.assess()
		if hazard == "capsule":
			check(s.ending == "safe_abort", "capsule hazard requires safe stop")
		else:
			check(s.alert == "", "recoverable hazard assessed")
	s.reset("normal", 1)
	s.confirm(); s.confirm(); arm(s, "knife")
	check(not s.act(Vector3(NAN, .5, .12), .1), "nonfinite input rejected")
	check(not s.act(Vector3(.8, .5, .12), 1000), "unbounded dt rejected")
	s.select_tool("unknown")
	check(s.replay_log(s.export_log()).get("ok", false), "rejected API arguments preserve valid log")
	s.paused = true
	s.act(Vector3(.76, .5, .12), .1)
	s.paused = false
	s.begin_stroke()
	for i in range(31):
		s.act(Vector3(.76 + .15 * i / 30.0, .5, .12), STEP_FOR_TEST())
	check(s.phase == "ENTRY", "paused interaction requires release after resume")
	s.paused = true
	entry(s)
	check(s.phase == "ENTRY", "pause blocks input")
	s.reset("normal", 1)
	s.confirm(); s.confirm(); arm(s, "knife")
	s.act(Vector3(.76, .5, .12), .000001)
	s.act(Vector3(.91, .5, .12), .000001)
	check(s.phase == "ENTRY" and s.progress == 0.0, "subtick contacts cannot complete paths")
	s.reset("normal", 1)
	s.confirm(); s.confirm(); arm(s, "knife")
	s.act(Vector3(.76, .5, .12), STEP_FOR_TEST())
	s.end_stroke(); s.begin_stroke()
	s.act(Vector3(.91, .5, .12), STEP_FOR_TEST())
	check(s.phase == "ENTRY" and s.progress == 0.0, "disconnected entry clicks cannot complete incision")
	entry(s)
	arm(s, "forceps")
	for i in range(1600):
		var angle := .009 if i % 2 else .0
		s.act(Vector3(.5 + cos(angle) * .22, .5 + sin(angle) * .22, .04), STEP_FOR_TEST())
	check(s.phase == "CAPSULE" and s.progress < .01, "capsule jitter cannot accumulate duplicate winding")
	s.reset("normal", 1)
	for i in range(110000):
		s.tick(STEP_FOR_TEST())
	var long_log: String = s.export_log()
	check(not long_log.is_empty() and s.replay_log(long_log).get("ok", false), "30 minute idle journal compressed and replayable")
	s.reset("normal", 1)
	for i in range(100010):
		s.select_tool("knife" if i % 2 == 0 else "forceps")
	check(s.export_log().is_empty() and s.export_error != "", "journal overflow fails export explicitly")
	print("Session tests: ", "PASS" if failures == 0 else str(failures) + " failures")
	quit(0 if failures == 0 else 1)

func STEP_FOR_TEST() -> float:
	return 1.0 / 60.0
