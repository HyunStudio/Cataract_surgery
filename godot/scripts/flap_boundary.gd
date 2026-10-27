extends RefCounted
## Cached actual triangle heights; bounded thin-membrane vertex contact, not face FEM.
const EntryWindow=preload("res://scripts/incision_window.gd")
var portals:Array=[]
const Kernel=preload("res://scripts/surface_contact.gd")
const CELL:=.16
const HEIGHT_CACHE_LIMIT:=512
var wounds:Array=[]
var radius:=.004
var wound_radius:=.085
var _cornea:Dictionary={}
var _iris:Dictionary={}
var _rim_radius:=0.
var _rim_inner:=0.
func configure(cornea:Dictionary,iris:Dictionary)->bool:
	var first:=_make_field(cornea); var second:=_make_field(iris)
	if first.is_empty() or second.is_empty(): return false
	var rim_radius:=0.; var rim_inner:=INF
	for p in first.positions: rim_radius=maxf(rim_radius,Vector2(p.x,p.z).length())
	for p in first.positions:
		if Vector2(p.x,p.z).length()>rim_radius-.0001: rim_inner=minf(rim_inner,p.y)
	if rim_radius<=radius or not is_finite(rim_inner): return false
	_cornea=first; _iris=second; _rim_radius=rim_radius; _rim_inner=rim_inner; return true
func _make_field(data:Dictionary)->Dictionary:
	if not data.get("positions") is PackedVector3Array or not data.get("triangles") is PackedInt32Array: return {}
	if data.positions.is_empty() or data.positions.size()>8192 or data.triangles.size()>24576: return {}
	if not Kernel.new().sweep(Vector3.ZERO,Vector3.ZERO,.01,data.positions,data.triangles).valid: return {}
	var field:={"positions":data.positions.duplicate(),"triangles":data.triangles.duplicate(),"bins":{},"height_cache":{}}
	var min_y:=INF; var max_y:=-INF
	for p in field.positions: min_y=minf(min_y,p.y); max_y=maxf(max_y,p.y)
	# Include the barycentric edge tolerance and float-vector rounding.
	var padding:float=(max_y-min_y)*.000004+maxf(1.,maxf(absf(min_y),absf(max_y)))*.000001
	field["min_y"]=min_y-padding; field["max_y"]=max_y+padding
	var coefficients:=PackedFloat64Array(); coefficients.resize(field.triangles.size()/3*10)
	for offset in range(0,field.triangles.size(),3):
		var a:Vector3=field.positions[field.triangles[offset]]; var b:Vector3=field.positions[field.triangles[offset+1]]; var c:Vector3=field.positions[field.triangles[offset+2]]
		var denominator:float=(b.z-c.z)*(a.x-c.x)+(c.x-b.x)*(a.z-c.z)
		if absf(denominator)<1e-12: continue
		var row:int=offset/3*10
		coefficients[row]=b.z-c.z; coefficients[row+1]=c.x-b.x
		coefficients[row+2]=c.z-a.z; coefficients[row+3]=a.x-c.x
		coefficients[row+4]=c.x; coefficients[row+5]=c.z; coefficients[row+6]=denominator
		coefficients[row+7]=a.y; coefficients[row+8]=b.y; coefficients[row+9]=c.y
		var lo:=a.min(b).min(c); var hi:=a.max(b).max(c)
		var from:=Vector2i(floori(lo.x/CELL),floori(lo.z/CELL)); var to:=Vector2i(floori(hi.x/CELL),floori(hi.z/CELL))
		if (to.x-from.x+1)*(to.y-from.y+1)>4096: return {}
		for x in range(from.x,to.x+1):
			for z in range(from.y,to.y+1):
				var key:=Vector2i(x,z)
				if not field.bins.has(key): field.bins[key]=PackedInt32Array()
				field.bins[key].append(offset)
	field["coefficients"]=coefficients
	return field
func _heights(field:Dictionary,p:Vector3)->Vector4:
	# Geometry is copied at configuration; reuse only identical XZ coordinates.
	var key:=Vector2(p.x,p.z)
	var cache:Dictionary=field.height_cache
	if cache.has(key): return cache[key]
	var coefficients:PackedFloat64Array=field.coefficients
	var low:=INF; var high:=-INF; var low_face:=-1; var high_face:=-1
	for offset in field.bins.get(Vector2i(floori(p.x/CELL),floori(p.z/CELL)),PackedInt32Array()):
		var row:int=offset/3*10
		var x:float=p.x-coefficients[row+4]; var z:float=p.z-coefficients[row+5]
		var u:float=(coefficients[row]*x+coefficients[row+1]*z)/coefficients[row+6]
		var v:float=(coefficients[row+2]*x+coefficients[row+3]*z)/coefficients[row+6]
		if u>=-1e-6 and v>=-1e-6 and u+v<=1.+1e-6:
			var y:float=u*coefficients[row+7]+v*coefficients[row+8]+(1.-u-v)*coefficients[row+9]
			if y<low: low=y; low_face=offset
			if y>high: high=y; high_face=offset
	var result:=Vector4(low,high,low_face,high_face)
	if cache.size()>=HEIGHT_CACHE_LIMIT: cache.clear()
	cache[key]=result
	return result
func _wound(p:Vector3)->bool:
	return EntryWindow.contains(p,wounds,radius,wound_radius,portals)

func _limbal_guard(p:Vector3)->bool:
	# Reduced lateral containment derived from the actual closed corneal rim.
	# Full scleral wall mechanics are not represented by this guard.
	return Vector2(p.x,p.z).length()>_rim_radius-radius and p.y<_rim_inner+radius
func _blocked(p:Vector3,exterior:=false)->bool:
	if not exterior and _limbal_guard(p): return true
	for index in range(2):
		var field:Dictionary=_cornea if index==0 else _iris
		if p.y<field.min_y-radius or p.y>field.max_y+radius: continue
		if index==0 and _wound(p): continue
		var heights:=_heights(field,p)
		if p.y>=heights.x-radius and p.y<=heights.y+radius: return true
	return false
func _outside(p:Vector3,prior:bool,previous:Vector3)->bool:
	var heights:=_heights(_cornea,p)
	if not is_finite(heights.y):
		var entry:=_heights(_cornea,previous)
		return prior or (is_finite(entry.x) and previous.y>=entry.x-radius and _wound(previous))
	if p.y>heights.y+radius: return prior or _wound(p)
	if p.y<heights.y-radius: return false
	return prior
func _contact_normal(p:Vector3,previous:Vector3)->Vector3:
	if _limbal_guard(p): return -Vector3(p.x,0,p.z).normalized()
	for index in range(2):
		if index==0 and _wound(p): continue
		var field:Dictionary=_cornea if index==0 else _iris
		var h:=_heights(field,p)
		if p.y<h.x-radius or p.y>h.y+radius: continue
		var prior:=_heights(field,previous)
		var upper:=is_finite(prior.y) and previous.y>(prior.x+prior.y)*.5
		if not is_finite(prior.y):
			var side:=Vector3(previous.x-p.x,0,previous.z-p.z).normalized()
			if side.length_squared()>.5: return side
		var offset:=int(h.w if upper else h.z)
		var a:Vector3=field.positions[field.triangles[offset]]; var b:Vector3=field.positions[field.triangles[offset+1]]; var c:Vector3=field.positions[field.triangles[offset+2]]
		var n:=(b-a).cross(c-a).normalized()
		if (n.y>0.)!=upper: n=-n
		return n
	return Vector3.DOWN
func resolve(start:Vector3,finish:Vector3,prior_outside:bool)->Dictionary:
	var result:={"valid":true,"position":finish,"outside":prior_outside,"contact":false}
	if _cornea.is_empty() or _iris.is_empty() or not start.is_finite() or not finish.is_finite() or start.length_squared()>256. or finish.length_squared()>256. or start.distance_to(finish)>2.56:
		result.valid=false; result.position=start; return result
	var current:=start; var desired:=finish
	for attempt in range(4):
		var count:=maxi(1,ceili(current.distance_to(desired)/.005)); var previous:=current; var collided:=false
		for i in range(1,count+1):
			var sample:=current.lerp(desired,float(i)/count)
			if _blocked(sample,result.outside):
				var normal:=_contact_normal(sample,previous)
				var low:=previous; var high:=sample
				for iteration in range(9):
					var middle:=(low+high)*.5
					if _blocked(middle,result.outside): high=middle
					else: low=middle
				var remaining:=desired-low
				var into:=remaining.dot(normal)
				if into<0.: remaining-=normal*into
				current=low+normal*.00001; desired=current+remaining
				result.contact=true; result.outside=_outside(current,result.outside,low); collided=true; break
			result.outside=_outside(sample,result.outside,previous); previous=sample
		if not collided: result.position=desired; return result
	result.position=current
	return result
