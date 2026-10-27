extends RefCounted
## Observes simulation evidence. Never edits tissue or assigns a clinical grade.
const CASES := ["standard","dense","small_pupil","motion"]
const CHECKS := ["patient","side","equipment"]
const INSPECTIONS := ["residual","implant","wound"]
var _case := "standard"
var _seed := 1
var _stage := "briefing"
var _preparation: Dictionary = {}
var _inspection: Dictionary = {}
var _latest: Dictionary = {}
var _timeline: Array = []
var _elapsed := 0.
var _active_time := 0.
var _alert := ""
var _ending := ""
var _motion_issued := false
var _milestones: Dictionary = {}
var _last_tool := ""

func _init() -> void:
	reset("standard",1)

func reset(case_id: String = "standard", seed_id: int = 1) -> void:
	_case=case_id if case_id in CASES else "standard"; _seed=seed_id
	_stage="briefing"; _elapsed=0.; _active_time=0.; _alert=""; _ending=""; _motion_issued=false
	_preparation={"patient":false,"side":false,"equipment":false}
	_inspection={"residual":false,"implant":false,"wound":false}
	_latest={}; _timeline=[]
	_milestones={}; _last_tool=""
	_event("case_started",{"case_id":_case,"seed":_seed})

func _event(kind: String, details: Dictionary = {}) -> void:
	if _timeline.size()<4000: _timeline.append({"time":_elapsed,"event":kind,"details":details.duplicate(true)})

func prepare(check_id: String) -> bool:
	if _stage!="briefing" or check_id not in CHECKS: return false
	if not _preparation[check_id]:
		_preparation[check_id]=true; _event("preparation",{"check":check_id})
	if false not in _preparation.values():
		_stage="operating"; _event("operation_started")
	return true

func ready() -> bool:
	return _stage=="operating" and _ending==""

func observe(dt: float, observation: Dictionary) -> void:
	if not ready() or not is_finite(dt) or dt<=0. or dt>.1 or not _valid_observation(observation): return
	_elapsed+=dt
	_latest=observation.duplicate(true)
	var observed_tool: String = str(observation.get("tool",""))
	if observed_tool!=_last_tool:
		_last_tool=observed_tool; _event("instrument_selected",{"tool":observed_tool})
	for milestone in ["material_removed","implant_delivery","implant_deployed","implant_aligned","entry_observed"]:
		var reached := false
		match milestone:
			"material_removed": reached=_satisfied("residual")
			"implant_delivery": reached=observation.iol.delivered>0.
			"implant_deployed": reached=observation.iol.deployed
			"implant_aligned": reached=_satisfied("implant")
			"entry_observed": reached=observation.wound
		if reached and not _milestones.has(milestone):
			_milestones[milestone]=true
			_event(milestone,{"remaining_mass":observation.lens.remaining_mass,"alignment":observation.iol.alignment})
	if _alert=="" and (float(observation.get("energy",0.))>0. or float(observation.get("movement",0.))>0.): _active_time+=dt
	if _case=="motion" and not _motion_issued and _active_time>=8.+posmod(_seed,5):
		_motion_issued=true; _alert="motion"; _event("patient_motion",{"active_time":_active_time})
	for check_id in INSPECTIONS:
		if _inspection[check_id] and not _satisfied(check_id):
			_inspection[check_id]=false; _event("inspection_invalidated",{"check":check_id})

func _valid_observation(o: Dictionary) -> bool:
	for key in ["capsule","lens","iol"]:
		if not o.get(key) is Dictionary or o[key].get("finite")!=true: return false
	for pair in [["lens","remaining_mass"],["lens","removed_mass"],["iol","delivered"],["iol","alignment"]]:
		var value = o[pair[0]].get(pair[1])
		if not (value is float or value is int) or not is_finite(value) or value<0. or value>1.000001: return false
	if not o.iol.get("deployed") is bool or not o.get("wound") is bool: return false
	for key in ["energy","movement"]:
		var value = o.get(key,0.)
		if not (value is float or value is int) or not is_finite(value) or value<0.: return false
	return true

func _satisfied(check_id: String) -> bool:
	if _latest.is_empty(): return false
	match check_id:
		"residual": return _latest.lens.remaining_mass<=.02 and _latest.lens.removed_mass>=.98
		"implant": return _latest.iol.delivered>=.999999 and _latest.iol.deployed and _latest.iol.alignment>=.9
		"wound": return _latest.wound
	return false

func inspect(check_id: String) -> bool:
	if not ready() or _alert!="" or check_id not in INSPECTIONS or not _satisfied(check_id): return false
	if not _inspection[check_id]:
		_inspection[check_id]=true; _event("inspection",{"check":check_id})
	return true

func finish() -> bool:
	if not ready() or _alert!="" or false in _inspection.values(): return false
	for check_id in INSPECTIONS:
		if not _satisfied(check_id): return false
	_stage="debrief"; _ending="completed"; _event("completed")
	return true

func abort(reason: String) -> void:
	if _ending!="": return
	_stage="aborted"; _ending="safe_stop"; _alert=""
	_event("safe_stop",{"reason":reason.left(500)})

func acknowledge() -> bool:
	if _alert=="" or _ending!="": return false
	_event("alert_acknowledged",{"alert":_alert}); _alert=""
	return true

func report() -> bool:
	return acknowledge()

func snapshot() -> Dictionary:
	var objective := "준비 확인: 환자 · 수술 부위 · 장비"
	if ready():
		objective="상태 평가 후 조작 재개" if _alert!="" else ("수정체 잔여물 제거" if not _satisfied("residual") else ("IOL 전달·전개·중심 정렬" if not _satisfied("implant") else ("진입 상처 확인" if not _satisfied("wound") else "잔여물·렌즈·상처 최종 검사")))
	elif _ending!="": objective="사례 기록 검토"
	return {"case_id":_case,"seed":_seed,"stage":_stage,"ready":ready(),"preparation":_preparation.duplicate(),"inspection":_inspection.duplicate(),"objective":objective,"alert":_alert,"ending":_ending,"elapsed":_elapsed,"timeline":_timeline.duplicate(true),"latest":_latest.duplicate(true),"metrics":{"active_time":_active_time,"clinical_grade":false}}
