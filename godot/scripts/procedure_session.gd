extends RefCounted
## Deterministic game rules. Coordinates and timing are game units, not clinical settings.
const BUILD := "cataract-godot-2.0"
const STEP := 1.0 / 60.0
const PHASES := ["PREOP", "PREP", "ENTRY", "CAPSULE", "HYDRO", "PHACO", "CORTEX", "IOL", "ALIGN", "CLOSE", "RECOVERY", "ABORTED"]
const TOOLS := ["knife", "forceps", "cannula", "phaco", "ia", "injector", "manipulator"]
const CASES := ["normal", "movement", "monitor", "capsule"]
const MAX_COMMANDS := 100000
const MAX_LOG_BYTES := 8000000
const MAX_REPLAY_COMMANDS := 1000000
var phase := "PREOP"
var tool := "knife"
var case_id := "normal"
var paused := false
var alert := ""
var ending := ""
var progress := 0.0
var eye: Dictionary
var events: Array = []
var simulation_tick := 0
var stage_times: Dictionary = {}
var errors := 0
var final_checks: Dictionary = {}
var seed_value := 1
var _held := false
var _release_required := false
var _previous := Vector3.ZERO
var _has_previous := false
var _clock := 0.0
var _action_clock := 0.0
var _arc := 0.0
var _commands: Array = []
var _record := true
var export_error := ""
var _journal_bytes := 0
var _journal_work := 0

func _init() -> void:
	reset("normal", 1)

func reset(id: String = "normal", seed_id: int = 1) -> void:
	case_id = id if id in CASES else "normal"
	seed_value = seed_id
	phase = "PREOP"; tool = "knife"; paused = false; alert = ""; ending = ""; progress = 0.0
	simulation_tick = 0; errors = 0; _clock = 0.0; _action_clock = 0.0; _arc = 0.0
	_held = false; _release_required = false; _has_previous = false
	events = []; _commands = []; stage_times = {}
	export_error = ""; _journal_bytes = 0; _journal_work = 0
	final_checks = {"alignment": false, "wound": false, "handoff": false}
	eye = {"opacity": 1.0, "cortex": 1.0, "capsule_integrity": 1.0, "iol_alignment": 0.0, "iol_deployment": 0.0, "entry_path": [], "capsule_path": [], "regions": []}
	for i in range(8):
		var a := TAU * i / 8.0
		eye.regions.append({"x": .5 + cos(a) * .16, "y": .5 + sin(a) * .16, "opacity": 1.0, "cortex": 1.0})

static func stage_depth(stage: String) -> float:
	return {"ENTRY": .12, "CAPSULE": .04, "HYDRO": -.02, "PHACO": -.08, "CORTEX": -.06, "IOL": .02, "ALIGN": .02}.get(stage, .0)

func target_depth() -> float:
	return stage_depth(phase)

func expected_tool() -> String:
	return {"ENTRY": "knife", "CAPSULE": "forceps", "HYDRO": "cannula", "PHACO": "phaco", "CORTEX": "ia", "IOL": "injector", "ALIGN": "manipulator"}.get(phase, "")

func _log(op: String, data: Dictionary = {}) -> void:
	if _record and export_error == "":
		_journal_work += 1
		if _journal_work > MAX_REPLAY_COMMANDS:
			export_error = "Replay journal simulation duration limit exceeded."
			return
		# Adjacent identical clock commands preserve each fixed-step call on replay.
		if op == "tick" and not _commands.is_empty():
			var last: Dictionary = _commands[-1]
			if last.op == "tick" and last.paused == paused and last.dt == data.dt and last.get("count", 1) < 1000000:
				last["count"] = last.get("count", 1) + 1
				return
		var command := data.duplicate(true)
		command["op"] = op
		command["tick"] = simulation_tick
		command["paused"] = paused
		var bytes := JSON.stringify(command).to_utf8_buffer().size() + 1
		if _commands.size() >= MAX_COMMANDS or _journal_bytes + bytes > MAX_LOG_BYTES - 2048:
			export_error = "Replay journal capacity exceeded; restart the case to record a new replay."
			return
		_journal_bytes += bytes
		_commands.append(command)

func toggle_pause() -> bool:
	_log("pause")
	paused = not paused
	_clock = 0.0; _action_clock = 0.0
	_held = false; _has_previous = false; _release_required = true
	return paused

func select_tool(id: String) -> bool:
	if id not in TOOLS:
		return false
	_log("tool", {"id": id})
	if id != tool:
		_release_required = _release_required or _held
		_held = false; _has_previous = false; _action_clock = 0.0
	tool = id
	return true

func begin_stroke() -> void:
	_log("begin")
	if not _held and not _release_required and not paused and alert == "" and ending == "":
		_held = true
		_has_previous = false
		_action_clock = 0.0

func end_stroke() -> void:
	if not _held and not _release_required and not _has_previous and _action_clock == 0.0 and not (phase == "CAPSULE" and progress > 0.0):
		return
	_log("end")
	_held = false; _release_required = false; _has_previous = false; _action_clock = 0.0
	if phase == "CAPSULE" and progress > 0.0:
		progress = 0.0; _arc = 0.0; eye.capsule_path = []
	elif phase == "ENTRY":
		# An incision belongs to one uninterrupted drag, including its initial point.
		progress = 0.0; eye.entry_path = []

func _transition(next: String) -> void:
	events.append({"tick": simulation_tick, "phase": next})
	phase = next; progress = 0.0; _has_previous = false; _action_clock = 0.0
	_release_required = true; _held = false
	if next == "PHACO" and case_id != "normal":
		alert = case_id
		events.append({"tick": simulation_tick, "alert": alert})
		if case_id == "capsule":
			eye.capsule_integrity = 0.0
	if next == "RECOVERY":
		ending = "completed"

func confirm() -> bool:
	_log("confirm")
	if paused or alert != "" or ending != "":
		return false
	match phase:
		"PREOP": _transition("PREP")
		"PREP": _transition("ENTRY")
		"CLOSE":
			if eye.opacity > .01 or eye.cortex > .01 or eye.iol_alignment < .99 or eye.capsule_integrity < 1.0:
				return false
			if false in final_checks.values():
				return false
			_transition("RECOVERY")
		_: return false
	return true

func verify(id: String) -> bool:
	if not final_checks.has(id):
		return false
	_log("verify", {"id": id})
	if phase != "CLOSE" or paused or alert != "":
		return false
	final_checks[id] = true
	return true

func _valid(point: Vector3) -> bool:
	if point.x < 0.0 or point.x > 1.0 or point.y < 0.0 or point.y > 1.0 or absf(point.z - target_depth()) > .035:
		return false
	var radius := Vector2(point.x - .5, point.y - .5).length()
	match phase:
		"ENTRY": return point.x >= .745 and point.x <= .925 and absf(point.y - .5) <= .035
		"CAPSULE": return absf(radius - .22) <= .035
		"HYDRO": return Vector2(point.x - .68, point.y - .5).length() <= .08
		"PHACO", "CORTEX": return radius <= .29
		"IOL", "ALIGN": return radius <= .09
	return false

func act(point: Vector3, dt: float) -> bool:
	if not point.is_finite() or maxf(absf(point.x), maxf(absf(point.y), absf(point.z))) > 2.0 or not is_finite(dt) or dt <= 0.0 or dt > .25:
		return false
	_log("act", {"p": [point.x, point.y, point.z], "dt": dt})
	if paused or alert != "" or ending != "":
		_held = false; _release_required = true; _has_previous = false; _action_clock = 0.0
		return false
	if not _held or _release_required or paused or alert != "" or ending != "":
		return false
	if tool != expected_tool():
		errors += 1
		return false
	var valid := _valid(point)
	if _has_previous:
		for i in range(1, 17):
			valid = valid and _valid(_previous.lerp(point, i / 16.0))
	if not valid:
		errors += 1; _has_previous = false; _action_clock = 0.0
		if phase == "CAPSULE":
			progress = 0.0; _arc = 0.0; eye.capsule_path = []
		elif phase == "ENTRY":
			progress = 0.0; eye.entry_path = []
		return false
	_action_clock += dt
	var ticks := int((_action_clock + .000000001) / STEP)
	_action_clock -= ticks * STEP
	if ticks == 0:
		return false
	var elapsed := ticks * STEP
	match phase:
		"ENTRY":
			if eye.entry_path.is_empty() and point.x > .79:
				return false
			if _has_previous and point.x < _previous.x - .003:
				return false
			if eye.entry_path.size() < 256:
				eye.entry_path.append([point.x, point.y, point.z])
			progress = clampf((point.x - .76) / .15, 0.0, 1.0)
		"CAPSULE":
			if not _has_previous:
				if Vector2(point.x - .72, point.y - .5).length() > .04:
					return false
			else:
				var a := atan2(_previous.y - .5, _previous.x - .5)
				var b := atan2(point.y - .5, point.x - .5)
				var delta := wrapf(b - a, -PI, PI)
				if delta < -.01 or delta > .3:
					progress = 0.0; _arc = 0.0; eye.capsule_path = []; _has_previous = false
					return false
				# Small reversals undo winding; repeated jitter never earns new coverage.
				_arc = maxf(0.0, _arc + delta)
			if eye.capsule_path.size() < 512:
				eye.capsule_path.append([point.x, point.y, point.z])
			progress = clampf(_arc / TAU, 0.0, 1.0)
			if _arc >= TAU - .03:
				progress = 1.0
		"HYDRO": progress = minf(1.0, progress + elapsed / 1.2)
		"PHACO", "CORTEX":
			var field := "opacity" if phase == "PHACO" else "cortex"
			for region in eye.regions:
				if Vector2(point.x - region.x, point.y - region.y).length() < .085:
					region[field] = maxf(0.0, region[field] - elapsed / (1.4 if phase == "PHACO" else .8))
			var total := 0.0
			for region in eye.regions:
				total += region[field]
			eye[field] = total / 8.0
			progress = 1.0 - eye[field]
		"IOL":
			eye.iol_deployment = minf(1.0, eye.iol_deployment + elapsed / 1.5)
			progress = eye.iol_deployment
		"ALIGN":
			eye.iol_alignment = minf(1.0, eye.iol_alignment + elapsed / 1.4)
			progress = eye.iol_alignment
	_previous = point; _has_previous = true
	if progress >= .999999:
		_transition(PHASES[PHASES.find(phase) + 1])
	return true

func tick(dt: float) -> void:
	if not is_finite(dt) or dt <= 0.0 or dt > .25:
		return
	_log("tick", {"dt": dt})
	if paused or alert != "" or ending != "":
		_clock = 0.0
		_held = false; _release_required = true; _has_previous = false
		return
	_clock += dt
	var ticks := int((_clock + .000000001) / STEP)
	_clock -= ticks * STEP
	simulation_tick += ticks
	stage_times[phase] = stage_times.get(phase, 0) + ticks

func assess() -> void:
	_log("assess")
	if alert == "capsule":
		abort()
	elif alert != "":
		events.append({"tick": simulation_tick, "assessed": alert})
		alert = ""; _clock = 0.0; _action_clock = 0.0; _release_required = true; _held = false

func abort() -> void:
	_log("abort")
	if ending == "":
		_transition("ABORTED")
		ending = "safe_abort"

func score_breakdown() -> Dictionary:
	var completed := 0
	for event in events:
		if event.has("phase") and event.phase != "ABORTED":
			completed += 1
	var checks := 0
	for checked in final_checks.values():
		if checked: checks += 1
	return {"completion": completed * 5.0, "tissue": (1.0 - eye.opacity) * 15.0 + (1.0 - eye.cortex) * 10.0, "iol": eye.iol_deployment * 10.0 + eye.iol_alignment * 10.0, "final_checks": checks * 5.0 / 3.0, "error_penalty": mini(errors, 25), "safe_stop": ending == "safe_abort"}

func snapshot() -> Dictionary:
	var breakdown := score_breakdown()
	var score := clampi(roundi(breakdown.completion + breakdown.tissue + breakdown.iol + breakdown.final_checks - breakdown.error_penalty), 0, 100)
	return {"phase": phase, "tool": tool, "case_id": case_id, "paused": paused, "alert": alert, "ending": ending, "progress": progress, "tick": simulation_tick, "eye": eye.duplicate(true), "score": score, "score_breakdown": breakdown, "errors": errors, "stage_times": stage_times.duplicate(true), "events": events.duplicate(true), "final_checks": final_checks.duplicate(true)}

func _digest() -> String:
	return JSON.stringify(snapshot()).sha256_text()

func export_log() -> String:
	if export_error != "":
		return ""
	var lines := [JSON.stringify({"version": 2, "engine_build": BUILD, "case": case_id, "seed": seed_value})]
	for command in _commands:
		lines.append(JSON.stringify(command))
	lines.append(JSON.stringify({"digest": _digest(), "command_count": _commands.size()}))
	var raw := "\n".join(lines)
	if raw.to_utf8_buffer().size() > MAX_LOG_BYTES:
		export_error = "Replay journal exceeds export byte limit."
		return ""
	return raw

func replay_log(raw: String) -> Dictionary:
	if raw.to_utf8_buffer().size() > MAX_LOG_BYTES:
		return {"ok": false, "error": "log exceeds bound"}
	var lines := raw.split("\n", false)
	if lines.size() < 2 or lines.size() > 100002:
		return {"ok": false, "error": "invalid line count"}
	var header = JSON.parse_string(lines[0])
	var footer = JSON.parse_string(lines[-1])
	if not header is Dictionary or not footer is Dictionary:
		return {"ok": false, "error": "invalid envelope"}
	if header.get("version") != 2 or header.get("engine_build") != BUILD or header.get("case") not in CASES or not _number(header.get("seed")) or absf(header.seed) > 2147483647:
		return {"ok": false, "error": "unsupported header"}
	if footer.get("command_count") != lines.size() - 2 or not footer.get("digest") is String:
		return {"ok": false, "error": "invalid footer"}
	var copy = get_script().new()
	copy.reset(header.case, int(header.seed))
	copy._record = false
	var expanded_commands := 0
	for line in lines.slice(1, lines.size() - 1):
		var c = JSON.parse_string(line)
		if not c is Dictionary or not c.get("op") is String or not c.get("paused") is bool or c.get("tick") != copy.simulation_tick:
			return {"ok": false, "error": "invalid command"}
		var repeats = c.get("count", 1)
		if not _number(repeats) or repeats != floor(repeats) or repeats < 1 or repeats > MAX_REPLAY_COMMANDS or (c.op != "tick" and repeats != 1):
			return {"ok": false, "error": "invalid repeat count"}
		expanded_commands += int(repeats)
		if expanded_commands > MAX_REPLAY_COMMANDS:
			return {"ok": false, "error": "replay work exceeds bound"}
		copy.paused = c.paused
		match c.op:
			"tool":
				if c.get("id") not in TOOLS: return {"ok": false, "error": "invalid tool"}
				copy.select_tool(c.id)
			"begin": copy.begin_stroke()
			"end": copy.end_stroke()
			"confirm": copy.confirm()
			"assess": copy.assess()
			"abort": copy.abort()
			"pause": copy.toggle_pause()
			"verify":
				if c.get("id") not in ["alignment", "wound", "handoff"]: return {"ok": false, "error": "invalid check"}
				copy.verify(c.id)
			"tick", "act":
				if not _number(c.get("dt")) or c.dt <= 0 or c.dt > .25:
					return {"ok": false, "error": "invalid dt"}
				if c.op == "tick":
					var count = c.get("count", 1)
					if not _number(count) or count != floor(count) or count < 1 or count > 1000000:
						return {"ok": false, "error": "invalid repeat count"}
					for i in range(int(count)): copy.tick(c.dt)
				else:
					if not c.get("p") is Array or c.p.size() != 3:
						return {"ok": false, "error": "invalid point"}
					for n in c.p:
						if not _number(n) or absf(n) > 2.0: return {"ok": false, "error": "unbounded point"}
					copy.act(Vector3(c.p[0], c.p[1], c.p[2]), c.dt)
			_: return {"ok": false, "error": "unknown command"}
	if copy._digest() != footer.digest:
		return {"ok": false, "error": "digest mismatch"}
	return {"ok": true, "snapshot": copy.snapshot()}

static func _number(value: Variant) -> bool:
	return (value is int or value is float) and is_finite(float(value))
