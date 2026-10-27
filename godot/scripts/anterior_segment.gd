extends RefCounted
## Representative dimensioned geometry. Shape does not calibrate material/flow/device physics.
const units_per_mm:=.24
const lens_radius:=4.6*units_per_mm
const lens_half_thickness:=2.1*units_per_mm
const bag_radius:=4.7*units_per_mm
const bag_half_thickness:=2.2*units_per_mm
const corneal_radius:=5.9*units_per_mm
const corneal_thickness:=.55*units_per_mm
const iol_plane:=0.
const iol_scale:=1.44
const wound_radius:=.085
const entry_length:=.40
const closure_length:=.65
const tool_radii:={"knife":.018,"forceps":.018,"cannula":.025,"phaco":.055,"ia":.040,"injector":.070,"manipulator":.018}
func tip_radius(id:String)->float: return tool_radii.get(id,.025)
const portals:=[Vector3(1.44,.82,0),Vector3(-1.44,.82,.25)]
const planes:={"knife":.80,"forceps":.53,"cannula":.32,"phaco":.18,"ia":.18,"injector":0.,"manipulator":0.}
func pupil_radius(small:bool)->float: return .60 if small else .96
func bag_front(r:float)->float: return bag_half_thickness*sqrt(maxf(0.,1.-r*r/(bag_radius*bag_radius)))
func bag_back(r:float)->float: return -bag_front(r)
func lens_height(r:float)->float: return lens_half_thickness*sqrt(maxf(0.,1.-r*r/(lens_radius*lens_radius)))
func cornea_outer(r:float)->float:
	return bag_half_thickness+3.*units_per_mm+corneal_thickness-.60*pow(r/corneal_radius,2.)
func cornea_inner(r:float)->float:
	return cornea_outer(r)-corneal_thickness-.04*pow(r/corneal_radius,2.)
func _disk(radius:float,rings:int,sectors:int,kind:String)->Dictionary:
	var points:=PackedVector3Array([Vector3(0,_height(0.,kind),0)])
	var ids:=PackedInt32Array()
	for ring in range(1,rings+1):
		var r:=radius*sin(PI*.5*ring/rings) if kind=="posterior" else radius*ring/rings
		for i in range(sectors):
			var angle:=TAU*i/sectors
			points.append(Vector3(cos(angle)*r,_height(r,kind),sin(angle)*r))
	for i in range(sectors): ids.append_array(PackedInt32Array([0,1+(i+1)%sectors,1+i]))
	for ring in range(rings-1):
		for i in range(sectors):
			var a:=1+ring*sectors+i; var b:=1+ring*sectors+(i+1)%sectors
			var c:=a+sectors; var d:=b+sectors
			ids.append_array(PackedInt32Array([a,b,c,b,d,c]))
	return {"positions":points,"triangles":ids,"revision":0}
func _height(r:float,kind:String)->float:
	if kind=="outer": return cornea_outer(r)
	if kind=="inner": return cornea_inner(r)
	return bag_back(r)
func posterior()->Dictionary: return _disk(bag_radius,6,36,"posterior")
func cornea()->Dictionary:
	var outside:=_disk(corneal_radius,10,64,"outer")
	var inside:=_disk(corneal_radius,10,64,"inner")
	var points:PackedVector3Array=outside.positions
	var ids:PackedInt32Array=outside.triangles
	var offset:=points.size(); points.append_array(inside.positions)
	for i in range(0,inside.triangles.size(),3):
		ids.append_array(PackedInt32Array([offset+inside.triangles[i],offset+inside.triangles[i+2],offset+inside.triangles[i+1]]))
	var rim:=1+9*64
	for i in range(64):
		var a:=rim+i; var b:=rim+(i+1)%64
		ids.append_array(PackedInt32Array([a,b,offset+a,b,offset+b,offset+a]))
	return {"positions":points,"triangles":ids,"revision":0,"closed_shell":true}
func iris(inner:float)->Dictionary:
	inner=clampf(inner,.45,1.1)
	var points:=PackedVector3Array(); var ids:=PackedInt32Array()
	const N:=64
	const M:=4
	for side in range(2):
		for ring in range(M+1):
			var r:=lerpf(inner,1.4,float(ring)/M)
			var y:=maxf(.17,bag_front(r)+.12)-side*.06
			for i in range(N):
				var angle:=TAU*i/N
				points.append(Vector3(cos(angle)*r,y,sin(angle)*r))
	var offset:=(M+1)*N
	for ring in range(M):
		for i in range(N):
			var a:int=ring*N+i; var b:int=ring*N+(i+1)%N; var c:=a+N; var d:=b+N
			ids.append_array(PackedInt32Array([a,b,c,b,d,c,offset+a,offset+c,offset+b,offset+b,offset+c,offset+d]))
	for ring in [0,M]:
		for i in range(N):
			var a:int=ring*N+i; var b:int=ring*N+(i+1)%N
			ids.append_array(PackedInt32Array([a,offset+a,b,b,offset+a,offset+b]))
	return {"positions":points,"triangles":ids,"revision":0}
