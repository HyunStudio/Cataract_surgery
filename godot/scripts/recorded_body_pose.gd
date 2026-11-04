extends RefCounted
## Independent binary64 sampling of Packet41; no Vector3/Quaternion conversion.
static func invalid()->Dictionary:return {"valid":false,"reason":"recorded_body_pose","capsules":PackedFloat64Array()}
static func unit(q:PackedFloat64Array)->PackedFloat64Array:
	var squared:=0.
	for value in q:squared+=value*value
	var length:=sqrt(squared)
	for k in range(4):q[k]/=length
	return q
static func ideal(p:PackedFloat64Array,endpoint:int,t:float)->PackedFloat64Array:
	var first:=unit(p.slice(19,23));var last:=unit(p.slice(23,27));var product:=0.
	for k in range(4):product+=first[k]*last[k]
	if product<0.:
		product=-product
		for k in range(4):last[k]=-last[k]
	var angle:=acos(clampf(product,0.,1.));var q:=PackedFloat64Array();q.resize(4)
	for k in range(4):q[k]=first[k]+t*(last[k]-first[k]) if angle<1e-9 else (sin((1.-t)*angle)*first[k]+sin(t*angle)*last[k])/sin(angle)
	q=unit(q)
	var local:=PackedFloat64Array();local.resize(3)
	for k in range(3):local[k]=p[27+endpoint*3+k]+t*(p[33+endpoint*3+k]-p[27+endpoint*3+k])
	var x:float=q[0];var y:float=q[1];var z:float=q[2];var w:float=q[3]
	var twice:=PackedFloat64Array([2.*(y*local[2]-z*local[1]),2.*(z*local[0]-x*local[2]),2.*(x*local[1]-y*local[0])])
	var point:=PackedFloat64Array([local[0]+w*twice[0]+y*twice[2]-z*twice[1],local[1]+w*twice[1]+z*twice[0]-x*twice[2],local[2]+w*twice[2]+x*twice[1]-y*twice[0]])
	for k in range(3):point[k]+=p[13+k]+t*(p[16+k]-p[13+k])
	return point
static func sample(kinds:PackedInt32Array,packets:PackedFloat64Array,t:float)->Dictionary:
	if not is_finite(t) or t<0. or t>1. or kinds.size()>64 or packets.size()!=kinds.size()*41:return invalid()
	var capsules:=PackedFloat64Array()
	for body in range(kinds.size()):
		var p:=packets.slice(body*41,(body+1)*41);var kind:int=kinds[body]
		if kind not in [0,1]:return invalid()
		for value in p:
			if not is_finite(value):return invalid()
		for k in range(12):
			if absf(p[k])>16.:return invalid()
		if p[12]<=1e-9 or p[12]>.3:return invalid()
		if kind==1:
			for k in range(13,39):
				if absf(p[k])>16.:return invalid()
			for off in [19,23]:
				var norm:=0.
				for k in range(4):norm+=p[off+k]*p[off+k]
				if absf(norm-1.)>.001:return invalid()
			if p[39]<0. or p[40]>1. or p[39]>=p[40]:return invalid()
		for endpoint in range(2):
			var point:=PackedFloat64Array();point.resize(3)
			if t==0. or t==1.:
				point=p.slice(endpoint*3+(6 if t==1. else 0),endpoint*3+(6 if t==1. else 0)+3)
			elif kind==0:
				for k in range(3):point[k]=p[endpoint*3+k]+t*(p[6+endpoint*3+k]-p[endpoint*3+k])
			else:
				var start:=ideal(p,endpoint,p[39]);var finish:=ideal(p,endpoint,p[40])
				point=ideal(p,endpoint,p[39]+t*(p[40]-p[39]))
				for k in range(3):point[k]+=(1.-t)*(p[endpoint*3+k]-start[k])+t*(p[6+endpoint*3+k]-finish[k])
			for value in point:
				if not is_finite(value) or absf(value)>16.:return invalid()
			capsules.append_array(point)
		capsules.append(p[12])
	return {"valid":true,"reason":"","capsules":capsules}
