extends RefCounted
## Reduced elastic entry-gap model in simulator coordinates; not corneal FEM.
var portals := [Vector3(1.44,.86,0),Vector3(-1.44,.86,.25)]
var opened := [false,false]
var paths: Array = [[],[]]
var gaps := [0.,0.]
var lengths := [0.,0.]
var _last: Array = [null,null]

func reset() -> void:
	opened=[false,false]; paths=[[],[]]; gaps=[0.,0.]; lengths=[0.,0.]; _last=[null,null]

func cut(hand: int, tip: Vector3, active: bool) -> void:
	if hand not in [0,1] or not tip.is_finite(): return
	var valid := active and tip.distance_to(portals[hand])<.34 and tip.y>.74 and tip.y<1.02
	if not valid:
		_last[hand]=null
		if not opened[hand]: paths[hand]=[]; lengths[hand]=0.
		return
	if _last[hand]!=null:
		var distance: float = tip.distance_to(_last[hand])
		if distance>.10:
			if not opened[hand]: lengths[hand]=0.; paths[hand]=[]
		elif distance>.001:
			lengths[hand]=minf(.6,lengths[hand]+distance)
			if paths[hand].size()<128: paths[hand].append(tip)
	_last[hand]=tip
	if paths[hand].is_empty(): paths[hand].append(tip)
	if lengths[hand]>=.15:
		opened[hand]=true
		gaps[hand]=maxf(gaps[hand],.025)

func update(dt: float, insertions: Array) -> void:
	if not is_finite(dt) or dt<=0 or dt>.1 or insertions.size()!=2: return
	for hand in range(2):
		if not opened[hand]: continue
		var target := .035 if float(insertions[hand])>.22 else .001+maxf(0.,lengths[hand]-.35)*.08
		gaps[hand]=lerpf(gaps[hand],target,1.-exp(-4.*dt))

func metrics() -> Dictionary:
	var count := int(opened[0])+int(opened[1])
	return {"entry_count":count,"sealed":count>0 and maxf(gaps[0],gaps[1])<.006,"leak":clampf((gaps[0]+gaps[1])*2.,0.,1.),"total_length":lengths[0]+lengths[1]}
