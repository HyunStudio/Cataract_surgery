extends RefCounted
## Numerical guesses only; this module cannot change physical histories or dt.
static func invalid()->Dictionary:return {"valid":false,"changed":false,"reason":"trajectory_seed"}
static func transition(candidate:Dictionary,witness:float)->Dictionary:
	for key in ["xyz","dual","times"]:
		if not candidate.get(key) is PackedFloat64Array:return invalid()
	if not candidate.get("pairs") is int or candidate.pairs<1 or candidate.pairs>65536:return invalid()
	var times:PackedFloat64Array=candidate.times;var dual:PackedFloat64Array=candidate.dual;var pairs:int=candidate.pairs
	if times.is_empty() or times.size()>16 or times.size()*pairs>65536 or dual.size()!=times.size()*pairs or candidate.xyz.is_empty() or candidate.xyz.size()%3!=0:return invalid()
	var previous:=0.
	for t in times:
		if not is_finite(t) or t<=previous or t>1.:return invalid()
		previous=t
	if previous!=1. or not is_finite(witness) or witness<=0. or witness>=1. or witness in times:return invalid()
	var penalty=candidate.get("penalty")
	if not (penalty is float or penalty is int) or not is_finite(penalty) or penalty<1. or penalty>1e12:return invalid()
	for value in candidate.xyz:
		if not is_finite(value) or absf(value)>16.:return invalid()
	for value in dual:
		if not is_finite(value) or value<0.:return invalid()
	var next_times:=times.duplicate();next_times.append(witness);next_times.sort()
	if next_times.size()*pairs>65536 or next_times.size()>16:
		next_times=PackedFloat64Array([1.,witness])
		for layer in range(times.size()):
			if times[layer]==1.:continue
			for pair in range(pairs):
				if dual[layer*pairs+pair]>0.:next_times.append(times[layer]);break
		next_times.sort()
	if next_times.size()*pairs>65536 or next_times.size()>16:return invalid()
	var multipliers:=PackedFloat64Array();multipliers.resize(next_times.size()*pairs)
	for layer in range(next_times.size()):
		var source:=times.find(next_times[layer])
		if source<0:continue
		for pair in range(pairs):multipliers[layer*pairs+pair]=dual[source*pairs+pair]
	return {"valid":true,"reason":"","times":next_times,"initial":candidate.xyz.duplicate(),"multiplier_seed":multipliers,"penalty_seed":float(penalty),"retired":times.size()+1-next_times.size()}
