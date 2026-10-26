extends Node3D
## Original, procedural teaching-scene assets. Rendering never changes procedure state.
var microscope: Camera3D
var room_camera: Camera3D
var tools: Dictionary = {}
var lens_regions: Array[MeshInstance3D] = []
var cortex_regions: Array[MeshInstance3D] = []
var iol: Node3D
var target: Node3D
var capsule_trace: Node3D
var entry_trace: Node3D
var _built := false
var _phase := ""
var _tool_root: Node3D
var _capsule: MeshInstance3D
var _iol_optic: MeshInstance3D
var _target_dots: Array[MeshInstance3D] = []
var _entry_marks: Array[MeshInstance3D] = []
var _capsule_marks: Array[MeshInstance3D] = []
var _metal: StandardMaterial3D
var _last_tool := ""
var _capsule_intact: StandardMaterial3D
var _capsule_damaged: StandardMaterial3D
var _membrane: MeshInstance3D
var _aspiration: Node3D
var _particles: Array[MeshInstance3D] = []
var _guide_normal: StandardMaterial3D
var _guide_contrast: StandardMaterial3D

func normalized_to_world(point: Vector3) -> Vector3:
	return Vector3((point.x-0.5)*4.0, 0.8+point.z, (point.y-0.5)*4.0)
func world_to_normalized(point: Vector3) -> Vector3:
	return Vector3(point.x/4.0+0.5, point.z/4.0+0.5, point.y-0.8)

func _material(color: Color, roughness: float = 0.5, metal: float = 0.0) -> StandardMaterial3D:
	var mat := StandardMaterial3D.new()
	mat.albedo_color = color
	mat.roughness = roughness
	mat.metallic = metal
	if color.a < 1.0:
		mat.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
		mat.cull_mode = BaseMaterial3D.CULL_DISABLED
	return mat
func _glow(color: Color) -> StandardMaterial3D:
	var mat := _material(color)
	mat.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	return mat
func _group(label: String, parent: Node3D = self) -> Node3D:
	var node := Node3D.new()
	node.name = label
	parent.add_child(node)
	return node
func _mesh(label: String, mesh: Mesh, mat: Material, pos: Vector3, parent: Node3D = self) -> MeshInstance3D:
	var node := MeshInstance3D.new()
	node.name = label
	node.mesh = mesh
	node.material_override = mat
	node.position = pos
	parent.add_child(node)
	return node
func _ball(label: String, radius: float, scale_factor: Vector3, mat: Material, pos: Vector3, parent: Node3D = self) -> MeshInstance3D:
	var sphere := SphereMesh.new()
	sphere.radius = radius
	sphere.height = radius*2
	sphere.radial_segments = 48
	sphere.rings = 24
	var node := _mesh(label, sphere, mat, pos, parent)
	node.scale = scale_factor
	return node
func _box(label: String, size: Vector3, mat: Material, pos: Vector3, parent: Node3D = self) -> MeshInstance3D:
	var box := BoxMesh.new()
	box.size = size
	return _mesh(label, box, mat, pos, parent)
func _rod(label: String, a: Vector3, b: Vector3, radius: float, mat: Material, parent: Node3D = self, end_radius: float = -1.0) -> MeshInstance3D:
	var cyl := CylinderMesh.new()
	cyl.top_radius = radius if end_radius < 0 else end_radius
	cyl.bottom_radius = radius
	cyl.height = a.distance_to(b)
	cyl.radial_segments = 16
	var node := _mesh(label,cyl,mat,(a+b)*0.5,parent)
	var axis := (b-a).normalized()
	var side := Vector3.FORWARD.cross(axis).normalized()
	if side.length_squared() < 0.01: side = Vector3.RIGHT
	node.basis = Basis(side,axis,side.cross(axis).normalized())
	return node
func _ring(label: String, inner: float, outer: float, y: float, mat: Material, parent: Node3D = self, bulge: float = 0.0) -> MeshInstance3D:
	var vertices := PackedVector3Array()
	var normals := PackedVector3Array()
	var uv := PackedVector2Array()
	var indices := PackedInt32Array()
	var segments := 160
	var rows := 6
	for j in range(rows+1):
		var f := float(j)/rows
		var radius := lerpf(inner,outer,f)
		for k in range(segments+1):
			var theta := float(k)/segments*TAU
			vertices.append(Vector3(cos(theta)*radius,y+sin(f*PI)*bulge,sin(theta)*radius))
			normals.append(Vector3.UP)
			uv.append(Vector2(cos(theta),sin(theta))*radius/outer*0.5+Vector2(0.5,0.5))
	for j in range(rows):
		for k in range(segments):
			var a := j*(segments+1)+k
			indices.append_array(PackedInt32Array([a,a+segments+1,a+1,a+1,a+segments+1,a+segments+2]))
	var arrays := []
	arrays.resize(Mesh.ARRAY_MAX)
	arrays[Mesh.ARRAY_VERTEX]=vertices
	arrays[Mesh.ARRAY_NORMAL]=normals
	arrays[Mesh.ARRAY_TEX_UV]=uv
	arrays[Mesh.ARRAY_INDEX]=indices
	var surface := ArrayMesh.new()
	surface.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES,arrays)
	return _mesh(label,surface,mat,Vector3.ZERO,parent)
func _arc(label: String, radius: float, start: float, end: float, height: float, thickness: float, mat: Material, parent: Node3D = self, center: Vector3 = Vector3.ZERO) -> Node3D:
	var group := _group(label,parent)
	var count := maxi(8,int(abs(end-start)*20.0))
	for i in range(count):
		var t0 := lerpf(start,end,float(i)/count)
		var t1 := lerpf(start,end,float(i+1)/count)
		_rod("segment",center+Vector3(cos(t0)*radius,height,sin(t0)*radius),center+Vector3(cos(t1)*radius,height,sin(t1)*radius),thickness,mat,group)
	return group

func build() -> void:
	if _built: return
	_built = true
	_metal = _material(Color("b9cbd0"),0.19,0.83)
	var environment := WorldEnvironment.new()
	var env := Environment.new()
	env.background_mode = Environment.BG_COLOR
	env.background_color = Color("071b24")
	env.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	env.ambient_light_color = Color("a6c7d0")
	env.ambient_light_energy = 0.45
	env.tonemap_mode = Environment.TONE_MAPPER_FILMIC
	environment.environment = env
	add_child(environment)
	var key := DirectionalLight3D.new()
	key.rotation_degrees = Vector3(-65,-25,0)
	key.light_color = Color("fff0d8")
	key.light_energy = 0.95
	add_child(key)
	var fill := OmniLight3D.new()
	fill.position = Vector3(-3,4,-2)
	fill.light_color = Color("9ce4f3")
	fill.light_energy = 0.9
	fill.omni_range = 12
	add_child(fill)
	microscope = Camera3D.new()
	microscope.name = "MicroscopeCamera"
	microscope.projection = Camera3D.PROJECTION_ORTHOGONAL
	microscope.size = 5.3
	microscope.position = Vector3(0,9,0)
	microscope.rotation_degrees = Vector3(-90,0,0)
	microscope.near = 0.05
	microscope.far = 60
	add_child(microscope)
	microscope.current = true
	room_camera = Camera3D.new()
	room_camera.name = "RoomCamera"
	room_camera.position = Vector3(6.4,4.8,7.0)
	room_camera.fov = 48
	room_camera.near = 0.1
	room_camera.far = 60.0
	add_child(room_camera)
	room_camera.look_at(Vector3(0,0.4,0.4))
	_build_room()
	_build_eye()
	_build_tools()
	_build_targets()
	update_state({"phase":"PREOP","eye":{}},Vector3(0.85,0.5,0),"knife",false)

func _lens_sector(index: int, parent: Node3D) -> MeshInstance3D:
	var vertices := PackedVector3Array()
	var normals := PackedVector3Array()
	var uv := PackedVector2Array()
	var indices := PackedInt32Array()
	var angle := index*TAU/8.0
	var center := Vector3(cos(angle)*0.64,0,sin(angle)*0.64)
	var steps := 16
	var rows := 12
	for j in range(rows+1):
		var radius := float(j)/rows*0.955
		for k in range(steps+1):
			var theta := angle+(float(k)/steps-0.5)*(TAU/8.0+0.008)
			var p := Vector3(cos(theta)*radius,0.065*(1.0-radius*radius),sin(theta)*radius)
			vertices.append(p-center)
			normals.append(Vector3(p.x*0.1,1,p.z*0.1).normalized())
			uv.append(Vector2(p.x,p.z)/2.0+Vector2(0.5,0.5))
	for j in range(rows):
		for k in range(steps):
			var a := j*(steps+1)+k
			indices.append_array(PackedInt32Array([a,a+steps+1,a+1,a+1,a+steps+1,a+steps+2]))
	var arrays := []
	arrays.resize(Mesh.ARRAY_MAX)
	arrays[Mesh.ARRAY_VERTEX]=vertices
	arrays[Mesh.ARRAY_NORMAL]=normals
	arrays[Mesh.ARRAY_TEX_UV]=uv
	arrays[Mesh.ARRAY_INDEX]=indices
	var surface := ArrayMesh.new()
	surface.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES,arrays)
	var material := ShaderMaterial.new()
	material.shader = load("res://assets/lens.gdshader")
	return _mesh("Nucleus_%d"%index,surface,material,Vector3(center.x,0.72,center.z),parent)

func _build_eye() -> void:
	var eye := _group("Eye")
	_ring("Sclera",1.43,1.92,0.71,_material(Color("e2d4ca"),0.3),eye,0.075)
	_ring("Limbus",1.38,1.47,0.79,_material(Color("9baaa8"),0.25),eye)
	var iris_mat := ShaderMaterial.new()
	iris_mat.shader = load("res://assets/iris.gdshader")
	_ring("Iris",0.98,1.40,0.765,iris_mat,eye,0.025)
	_ring("PupilRim",0.955,1.0,0.775,_material(Color("182422"),0.35),eye)
	_ring("Pupil",0.0,0.98,0.63,_material(Color("131918"),0.45),eye)
	_capsule_intact = _material(Color(0.75,0.91,0.9,0.2),0.15)
	_capsule_damaged = _material(Color(0.9,0.3,0.22,0.65),0.18)
	_capsule = _ring("Capsule",0.86,0.91,0.792,_capsule_intact,eye)
	_membrane = _ring("CapsuleMembrane",0.0,0.86,0.804,_material(Color(0.9,0.94,0.93,0.16),0.22),eye)
	var lens_root := _group("LensRegions",eye)
	var cortex_root := _group("CortexRegions",eye)
	for i in range(8):
		var angle := i*TAU/8.0
		var tissue := _lens_sector(i,lens_root)
		tissue.rotation.y = 0.0
		lens_regions.append(tissue)
		var cortical := _ball("Cortex_%d"%i,0.24,Vector3(0.7,0.11,1.35),_material(Color("e5dcca"),0.35),Vector3(cos(angle)*0.78,0.701,sin(angle)*0.78),cortex_root)
		cortical.rotation.y = -angle+PI/2
		cortex_regions.append(cortical)
	# Fine branching conjunctival vessels are confined to the visible scleral annulus.
	var vein_mat := _material(Color("bc8381"),0.5)
	for i in range(25):
		var theta := i*2.399963
		var start := Vector3(cos(theta)*1.91,0.728,sin(theta)*1.91)
		var mid := Vector3(cos(theta+0.024)*1.72,0.773,sin(theta+0.024)*1.72)
		var tip := Vector3(cos(theta-0.035)*1.52,0.765,sin(theta-0.035)*1.52)
		_rod("ConjunctivalVessel",start,mid,0.006,vein_mat,eye)
		_rod("VesselBranch",mid,tip,0.003,vein_mat,eye)
	# Transparent corneal envelope plus explicit microscope reflections.
	var cornea_mat := _material(Color(0.68,0.9,0.97,0.045),0.08)
	_ball("Cornea",1.42,Vector3(1,0.10,1),cornea_mat,Vector3(0,0.79,0),eye)
	var reflection := _glow(Color(0.94,1,1,0.48))
	_arc("CornealCatchlight",1.12,3.70,4.14,1.012,0.014,reflection,eye)
	_arc("SecondaryCatchlight",1.21,5.45,5.72,0.98,0.009,reflection,eye)
	_ball("SpecularHighlight",0.065,Vector3(1.7,0.08,0.6),_glow(Color(1,1,1,0.65)),Vector3(-0.78,1.04,-0.62),eye)
	iol = _group("IOL",eye)
	_iol_optic = _ball("Optic",0.66,Vector3(1,0.065,1),_material(Color(0.67,0.88,0.98,0.34),0.05),Vector3.ZERO,iol)
	_ring("OpticEdge",0.63,0.66,0.015,_material(Color(0.63,0.91,0.98,0.75),0.1),iol)
	_arc("HapticA",0.79,-0.25,2.1,0.0,0.019,_material(Color("9fd8eb"),0.15),iol,Vector3(0.13,0,0))
	_arc("HapticB",0.79,PI-0.25,PI+2.1,0.0,0.019,_material(Color("9fd8eb"),0.15),iol,Vector3(-0.13,0,0))
	capsule_trace = _group("CapsuleTrace",eye)
	entry_trace = _group("EntryTrace",eye)
	for i in range(80):
		var mark := _ball("CapsuleMark",0.021,Vector3(1,0.25,1),_glow(Color("ffe1a2")),Vector3.ZERO,capsule_trace)
		mark.visible = false
		_capsule_marks.append(mark)
	for i in range(40):
		var mark := _ball("IncisionMark",0.025,Vector3(1,0.2,0.55),_material(Color("67473f")),Vector3.ZERO,entry_trace)
		mark.visible = false
		_entry_marks.append(mark)

func _build_tools() -> void:
	_tool_root = _group("Instruments")
	var blue := _material(Color("2485ac"),0.3,0.25)
	var gold := _material(Color("bca367"),0.25,0.5)
	for id in ["knife","forceps","cannula","phaco","ia","injector","manipulator"]:
		var tool := _group(id,_tool_root)
		tools[id] = tool
		# All shafts extend toward the right edge and rise above anatomy, away from origin tip.
		var neck := Vector3(0.65,0.24,0.08)
		var grip := Vector3(1.55,0.52,0.20)
		if id == "knife":
			var blade := PrismMesh.new()
			blade.size = Vector3(0.25,0.015,0.13)
			var blade_node := _mesh("DiamondBlade",blade,_metal,Vector3(0.12,0.018,0),tool)
			blade_node.rotation.z = -0.04
			_rod("Shank",Vector3(0.23,0.03,0),neck,0.025,_metal,tool)
			_rod("Handle",neck,grip,0.075,blue,tool)
		elif id == "forceps":
			for side in [-1.0,1.0]:
				_rod("Jaw",Vector3(0,0,side*0.012),Vector3(0.25,0.08,side*0.10),0.014,_metal,tool)
				_rod("SpringArm",Vector3(0.25,0.08,side*0.10),grip+Vector3(0,0,side*0.07),0.028,_metal,tool)
			_box("Grip",Vector3(0.6,0.09,0.26),blue,grip,tool)
		elif id == "cannula":
			_rod("BentTip",Vector3.ZERO,Vector3(0.16,0.03,-0.08),0.014,_metal,tool)
			_rod("Needle",Vector3(0.16,0.03,-0.08),neck,0.021,_metal,tool)
			_rod("Hub",neck,neck+Vector3(0.24,0.08,0.03),0.07,gold,tool)
			_rod("Syringe",neck+Vector3(0.24,0.08,0.03),grip,0.095,_material(Color(0.70,0.87,0.91,0.7),0.12),tool)
		elif id == "phaco" or id == "ia":
			_rod("HollowTip",Vector3.ZERO,Vector3(0.22,0.055,0.025),0.026,_metal,tool)
			_ball("Lumen",0.018,Vector3(0.4,1,1),_material(Color("25313b")),Vector3(0,0.004,0),tool)
			_rod("SiliconeSleeve",Vector3(0.19,0.05,0.022),neck,0.046,_material(Color("b6d5df")),tool)
			_rod("Handpiece",neck,grip,0.105,blue if id=="phaco" else _material(Color("eee8db"),0.3),tool)
			for k in range(5):
				var p := neck.lerp(grip,0.3+k*0.12)
				_rod("GripBand",p,p+Vector3(0.035,0.011,0.004),0.111,_metal,tool)
			_rod("Tubing",grip,grip+Vector3(1.5,0.3,0.7),0.045,_material(Color("79b0b7")),tool)
		elif id == "injector":
			_rod("TaperedNozzle",Vector3.ZERO,neck,0.017,_material(Color(0.79,0.93,0.94,0.8),0.15),tool,0.08)
			_rod("Cartridge",neck,grip,0.11,_material(Color("e7eee7"),0.25),tool)
			_box("BluePlunger",Vector3(0.40,0.14,0.17),blue,grip+Vector3(0.3,0.08,0),tool)
		else:
			_rod("Hook",Vector3.ZERO,Vector3(0.015,0.018,0.065),0.012,_metal,tool)
			_rod("Shaft",Vector3(0.015,0.018,0.065),neck,0.017,_metal,tool)
			_rod("TitaniumGrip",neck,grip,0.055,gold,tool)

func _build_targets() -> void:
	target = _group("TutorialTargets")
	_guide_normal = _glow(Color(0.35,0.94,0.88,0.66))
	_guide_contrast = _glow(Color(1.0,0.94,0.05,1.0))
	_aspiration = _group("AspirationFragments")
	for i in range(12):
		var fragment := _ball("Fragment",0.025,Vector3.ONE,_material(Color("d8c78f")),Vector3.ZERO,_aspiration)
		_particles.append(fragment)
	for i in range(48):
		var dot := _ball("GuideDot",0.023,Vector3(1,0.3,1),_guide_normal,Vector3.ZERO,target)
		_target_dots.append(dot)

func _drape_mesh(parent: Node3D, mat: Material) -> void:
	var vertices := PackedVector3Array()
	var normals := PackedVector3Array()
	var indices := PackedInt32Array()
	var width := 34
	var length := 64
	for j in range(length+1):
		var z := -0.64+float(j)/length*5.5
		for i in range(width+1):
			var x := (float(i)/width-0.5)*3.1
			var shoulder := 0.53*exp(-pow((z-0.22)/0.8,2.0))
			var chest := 0.45*exp(-pow((z-1.25)/1.15,2.0))
			var legs := 0.26*exp(-pow((z-3.5)/1.7,2.0))
			var silhouette := (shoulder+chest+legs)*exp(-pow(x/0.65,4.0))
			var folds := 0.035*sin(x*17+z*2)*sin(z*5+x)*clampf(absf(x)*0.7+0.15,0,1)
			var falloff := pow(clampf((absf(x)-0.85)/0.7,0,1),1.2)*0.6
			vertices.append(Vector3(x,0.17+silhouette+folds-falloff,z))
			normals.append(Vector3.UP)
	# Geometric cloth normals expose the soft body contours and shallow folds.
	for j in range(length+1):
		for i in range(width+1):
			var left := vertices[j*(width+1)+maxi(0,i-1)]
			var right := vertices[j*(width+1)+mini(width,i+1)]
			var back := vertices[maxi(0,j-1)*(width+1)+i]
			var front := vertices[mini(length,j+1)*(width+1)+i]
			var dx := (right.y-left.y)/maxf(.01,right.x-left.x)
			var dz := (front.y-back.y)/maxf(.01,front.z-back.z)
			normals[j*(width+1)+i]=Vector3(-dx,1,-dz).normalized()
	for j in range(length):
		for i in range(width):
			var a := j*(width+1)+i
			indices.append_array(PackedInt32Array([a,a+1,a+width+1,a+1,a+width+2,a+width+1]))
	var arrays := []
	arrays.resize(Mesh.ARRAY_MAX)
	arrays[Mesh.ARRAY_VERTEX]=vertices
	arrays[Mesh.ARRAY_NORMAL]=normals
	arrays[Mesh.ARRAY_INDEX]=indices
	var surface := ArrayMesh.new()
	surface.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES,arrays)
	var cloth := _mesh("PatientBodyDrape",surface,mat,Vector3.ZERO,parent)
	cloth.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_DOUBLE_SIDED

func _build_room() -> void:
	var room := _group("Room")
	var wall := _material(Color("233d47"),0.85)
	var cloth := _material(Color("38666b"),0.98)
	cloth.cull_mode = BaseMaterial3D.CULL_DISABLED
	var pale := _material(Color("b3c4c4"),0.5)
	var charcoal := _material(Color("253640"),0.6)
	var skin := _material(Color("bb9581"),0.72)
	var floor_mat := ShaderMaterial.new()
	floor_mat.shader=load("res://assets/floor.gdshader")
	_box("Floor",Vector3(22,.12,22),floor_mat,Vector3(0,-2,0),room)
	_box("BackWall",Vector3(22,8,0.15),wall,Vector3(0,2,-7),room)
	_box("SideWall",Vector3(0.15,8,16),wall,Vector3(-8,2,0),room)
	_box("WallRail",Vector3(16,0.09,0.06),_metal,Vector3(0,0.1,-6.9),room)
	_box("OperatingTableFrame",Vector3(2.5,0.25,7.3),_metal,Vector3(0,-0.3,1.35),room)
	_box("OperatingTableMattress",Vector3(2.4,0.28,7.25),charcoal,Vector3(0,-0.05,1.35),room)
	_box("TablePedestal",Vector3(0.8,1.3,1.2),pale,Vector3(0,-1.1,1.3),room)
	for side in [-1,1]:
		_box("TableFoot",Vector3(2.7,0.16,0.32),charcoal,Vector3(0,-1.8,1.3+side*0.9),room)
		for x in [-1.1,1.1]:
			_ball("LockingCastor",0.12,Vector3(1,1,0.5),charcoal,Vector3(x,-1.85,1.3+side*0.9),room)
	_ball("Headrest",0.72,Vector3(1.05,0.18,1.2),charcoal,Vector3(0,0.16,-1.43),room)
	_ball("PatientHead",0.55,Vector3(1,0.78,1.3),skin,Vector3(0,0.32,-1.34),room)
	_ball("Nose",0.13,Vector3(0.55,0.76,1.15),skin,Vector3(0,0.755,-1.27),room)
	_arc("ClosedOtherEye",0.10,0.12,PI-0.12,0.73,0.009,_material(Color("755950")),room,Vector3(-0.23,0,-1.57))
	_rod("Mouth",Vector3(-0.09,0.681,-0.98),Vector3(0.09,0.681,-0.98),0.009,_material(Color("976e63")),room)
	for side in [-1,1]:
		_ball("Ear",0.12,Vector3(0.48,0.75,1.25),skin,Vector3(side*0.54,0.35,-1.30),room)
		_ball("Shoulder",0.30,Vector3(1,0.45,1.2),cloth,Vector3(side*0.42,0.18,0.25),room)
	_drape_mesh(room,cloth)
	var proxy := _group("RoomEyeProxy",room)
	proxy.position = Vector3(0.23,0.715,-1.58)
	_ball("RoomSclera",0.125,Vector3(1,0.20,0.75),_material(Color("dedbd1"),0.3),Vector3.ZERO,proxy)
	_ball("RoomIris",0.057,Vector3(1,0.12,1),_material(Color("42625d"),0.35),Vector3(0,0.026,0),proxy)
	_ball("RoomPupil",0.029,Vector3(1,0.10,1),_material(Color("222e2b")),Vector3(0,0.034,0),proxy)
	_arc("RoomSpeculum",0.14,0,TAU,0.01,0.008,_metal,proxy)
	# Articulated microscope, scaled to the patient's operative eye.
	_rod("MicroscopeStand",Vector3(-2.5,-1.8,-2.0),Vector3(-2.5,3.4,-2.0),0.10,pale,room)
	_box("MicroscopeBase",Vector3(1.5,0.15,1.2),charcoal,Vector3(-2.5,-1.8,-2),room)
	_rod("MicroscopeArmA",Vector3(-2.5,3.4,-2),Vector3(-1.3,3.4,-2.4),0.09,pale,room)
	_ball("ArmJointA",0.15,Vector3.ONE,_metal,Vector3(-1.3,3.4,-2.4),room)
	_rod("MicroscopeArmB",Vector3(-1.3,3.4,-2.4),Vector3(.23,2.8,-1.58),0.085,pale,room)
	_ball("ArmJointB",0.13,Vector3.ONE,_metal,Vector3(.23,2.8,-1.58),room)
	_box("MicroscopeHousing",Vector3(.65,.4,.55),pale,Vector3(.23,2.45,-1.58),room)
	_rod("Objective",Vector3(.23,2.4,-1.58),Vector3(.23,2.1,-1.58),.16,_metal,room)
	for side in [-1,1]:
		_rod("BinocularTube",Vector3(.23+side*.16,2.55,-1.55),Vector3(.23+side*.16,2.83,-1.12),.075,pale,room)
		_rod("Eyepiece",Vector3(.23+side*.16,2.83,-1.12),Vector3(.23+side*.16,2.9,-1.00),.085,charcoal,room)
		_rod("FocusKnob",Vector3(.23+side*.28,2.45,-1.58),Vector3(.23+side*.38,2.45,-1.58),.065,charcoal,room)
	var scope_light := SpotLight3D.new()
	scope_light.position=Vector3(.23,2.05,-1.58)
	scope_light.rotation_degrees=Vector3(-90,0,0)
	scope_light.light_color=Color("fff2d7")
	scope_light.light_energy=0.65
	scope_light.spot_range=3.0
	scope_light.spot_angle=22
	room.add_child(scope_light)
	_box("InstrumentTray",Vector3(1.7,0.09,1.3),_metal,Vector3(2.7,0.8,0.2),room)
	_box("TrayLiner",Vector3(1.58,0.018,1.18),_material(Color("8bacac"),.9),Vector3(2.7,.858,.2),room)
	_rod("TrayStand",Vector3(2.7,-1.8,.2),Vector3(2.7,.8,.2),.06,_metal,room)
	for i in range(5):
		_rod("SterileInstrument",Vector3(2.1+i*.25,.89,-.2),Vector3(2.15+i*.25,.89,.65),.018,_metal,room)
	_box("MonitorHousing",Vector3(2.0,1.4,.20),charcoal,Vector3(-3.7,1.3,-2.8),room)
	_box("MonitorScreen",Vector3(1.80,1.18,.025),_glow(Color("09252b")),Vector3(-3.7,1.3,-2.68),room)
	var screen := _group("MonitorTrace",room)
	for i in range(28):
		var x0 := -4.5+i*.058
		var h0: float = 1.4+sin(i*.8)*.025+(.23 if i%10==4 else 0)
		var h1: float = 1.4+sin((i+1)*.8)*.025+(.23 if (i+1)%10==4 else 0)
		_rod("ECG",Vector3(x0,h0,-2.65),Vector3(x0+.058,h1,-2.65),.008,_glow(Color("65e7ab")),screen)
	_rod("MonitorPole",Vector3(-3.7,-1.7,-2.8),Vector3(-3.7,.6,-2.8),.06,_metal,room)
	for x in [-3.0,3.0]:
		_box("CeilingLight",Vector3(1.8,.12,.7),_glow(Color("d9f6f1")),Vector3(x,5.8,-3),room)
	# Microscope backdrop and enlarged speculum share the operative model's scale.
	var surround := _group("OperativeSurround")
	_ring("SterileDrapeBackdrop",1.94,7.0,.45,_material(Color("294d53"),.95),surround)
	_ring("ExposedLidMargin",1.87,2.0,.59,skin,surround)
	for side in [-1.0,1.0]:
		_arc("SpeculumBlade",1.98,.6 if side>0 else PI+.6,2.5 if side>0 else PI+2.5,.85,.035,_metal,surround)
		_rod("SpeculumArm",Vector3(-1.4,.8,side*1.4),Vector3(-2.15,.8,side*1.7),.032,_metal,surround)
	_rod("SpeculumBridge",Vector3(-2.15,.8,-1.7),Vector3(-2.15,.8,1.7),.035,_metal,surround)

func set_room_view(enabled: bool) -> void:
	if not _built: build()
	room_camera.current = enabled
	microscope.current = not enabled
	set_room_hardware_visibility()
func update_state(snapshot: Dictionary, tip: Vector3, tool_id: String, active: bool) -> void:
	if not _built: build()
	var eye: Dictionary = snapshot.get("eye",{})
	var phase: String = snapshot.get("phase","PREOP")
	var regions: Array = eye.get("regions",[])
	for i in range(8):
		var region: Dictionary = regions[i] if i<regions.size() and regions[i] is Dictionary else {}
		var opacity := clampf(float(region.get("opacity",eye.get("opacity",1.0))),0,1)
		var cortex := clampf(float(region.get("cortex",eye.get("cortex",1.0))),0,1)
		lens_regions[i].visible = opacity>0.02
		lens_regions[i].scale = Vector3.ONE*maxf(0.1,sqrt(opacity))
		cortex_regions[i].visible = cortex>0.02
		cortex_regions[i].scale = Vector3(0.7,0.11,1.35)*maxf(0.1,sqrt(cortex))
	var deployment := clampf(float(eye.get("iol_deployment",0.0)),0,1)
	var alignment := clampf(float(eye.get("iol_alignment",0.0)),0,1)
	iol.visible = deployment>0 or phase in ["ALIGN","CLOSE","RECOVERY"]
	iol.scale = Vector3(lerpf(0.18,1.0,deployment),1,lerpf(0.6,1,deployment))
	iol.position = Vector3(0.24*(1-alignment),0.835,0.14*(1-alignment))
	iol.rotation.y = (1-alignment)*0.48
	_capsule.material_override = _capsule_intact if float(eye.get("capsule_integrity",1.0))>0 else _capsule_damaged
	var capsule_done := phase in ["HYDRO","PHACO","CORTEX","IOL","ALIGN","CLOSE","RECOVERY"]
	_membrane.visible = not capsule_done
	var opening := clampf(float(snapshot.get("progress",0.0)),0,1) if phase=="CAPSULE" else 0.0
	_membrane.scale = Vector3(1.0-opening,1.0,1.0-opening)
	var blocked := bool(snapshot.get("paused",false)) or str(snapshot.get("alert",""))!=""
	target.visible = bool(snapshot.get("tutorial",true)) and not blocked
	for dot in _target_dots: dot.material_override = _guide_contrast if bool(snapshot.get("high_contrast",false)) else _guide_normal
	var remaining := float(eye.get("opacity",1.0)) if phase=="PHACO" else float(eye.get("cortex",1.0))
	_aspiration.visible = active and not blocked and phase in ["PHACO","CORTEX"] and tool_id in ["phaco","ia"] and remaining>0.01 and not bool(snapshot.get("reduced_motion",false))
	for i in range(_particles.size()):
		var cycle := fmod(float(snapshot.get("tick",0))*0.037+float(i)/12.0,1.0)
		var theta := float(i)*2.399963
		var radial := (1-cycle)*0.22
		_particles[i].position = normalized_to_world(tip)+Vector3(cos(theta)*radial,0.14+cycle*0.04,sin(theta)*radial)
		_particles[i].scale = Vector3.ONE*(1-cycle)*0.8
	_update_path(_entry_marks,eye.get("entry_path",[]),0.85)
	_update_path(_capsule_marks,eye.get("capsule_path",[]),0.845)
	for id in tools:
		tools[id].visible = id==tool_id and not blocked and phase not in ["PREOP","RECOVERY","ABORTED"]
	if tools.has(tool_id):
		tools[tool_id].position = normalized_to_world(tip)
		tools[tool_id].rotation.y = -0.20 if active else -0.12
		if tool_id=="forceps": tools[tool_id].scale.z = 0.65 if active else 1.0
	if _phase!=phase:
		_phase=phase
		_update_targets(phase,regions)
	set_room_hardware_visibility()

func set_room_hardware_visibility() -> void:
	var room_mode := room_camera.current
	find_child("Room",true,false).visible = room_mode
	find_child("Eye",true,false).visible = not room_mode
	find_child("OperativeSurround",true,false).visible = not room_mode
	_tool_root.visible = not room_mode
	if room_mode:
		target.visible = false
		_aspiration.visible = false
func _update_path(marks: Array[MeshInstance3D], path: Array, height: float) -> void:
	for i in range(marks.size()):
		marks[i].visible = i<path.size()
		if i>=path.size(): continue
		var sampled := mini(path.size()-1,roundi(float(i)*float(path.size()-1)/float(maxi(1,mini(path.size(),marks.size())-1))))
		var p = path[sampled]
		if p is Array and p.size()>=2:
			marks[i].position=Vector3((float(p[0])-0.5)*4,height,(float(p[1])-0.5)*4)
func _update_targets(phase: String, regions: Array) -> void:
	for dot in _target_dots: dot.visible=false
	if phase=="CAPSULE":
		for i in range(48):
			var angle:=i*TAU/48.0
			_target_dots[i].position=Vector3(cos(angle)*0.88,0.94,sin(angle)*0.88)
			_target_dots[i].visible = i%2==0
	elif phase=="ENTRY" or phase=="CLOSE":
		for i in range(10):
			_target_dots[i].position=Vector3(1.04+i*0.06,0.95,0)
			_target_dots[i].visible=true
	elif phase=="HYDRO":
		_target_dots[0].position=Vector3(.72,.95,0)
		_target_dots[0].visible=true
	elif phase in ["PHACO","CORTEX"]:
		for i in range(8):
			var region:Dictionary=regions[i] if i<regions.size() else {}
			var angle:=i*TAU/8.0
			_target_dots[i].position=Vector3((float(region.get("x",0.5+cos(angle)*0.16))-0.5)*4,0.95,(float(region.get("y",0.5+sin(angle)*0.16))-0.5)*4)
			_target_dots[i].visible=true
	elif phase in ["IOL","ALIGN"]:
		for i in range(4):
			_target_dots[i].position=Vector3((i-1.5)*0.05,0.95,0)
			_target_dots[i].visible=true
