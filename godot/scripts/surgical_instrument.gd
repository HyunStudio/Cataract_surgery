extends RefCounted
## Dimensioned generic instruments. Local +X goes from working tip toward the handle.
## These are not a manufacturer-specific device library or complete contact shapes.
static func build(id:String,radius:float)->Node3D:
	var root:=Node3D.new(); root.set_meta("shaft_axis",Vector3.RIGHT)
	root.set_meta("tip_radius",radius)
	var metal:=_material(Color(.64,.72,.74),.18,.85)
	var blue:=_material(Color(.055,.25,.34),.28,.4)
	var white:=_material(Color(.72,.80,.78),.23,.15)
	var dark:=_material(Color(.015,.026,.028),.5,0.)
	var gold:=_material(Color(.63,.49,.25),.25,.7)
	if id=="knife":
		var mesh:=PrismMesh.new(); mesh.size=Vector3(.18,.015,.12)
		var blade:=MeshInstance3D.new(); blade.name="Blade"; blade.mesh=mesh; blade.material_override=metal
		blade.position=Vector3(.09,0,0); root.add_child(blade)
	elif id=="forceps":
		for side in [-1.,1.]:
			_rod(root,"Jaw",Vector3(0,0,side*.025),Vector3(.22,0,side*.045),.010,metal)
	elif id=="cannula":
		_rod(root,"BentTip",Vector3.ZERO,Vector3(.18,.025,0),radius,metal)
	elif id=="manipulator":
		_rod(root,"Hook",Vector3.ZERO,Vector3(.025,0,.06),.012,metal)
	else:
		_rod(root,"WorkingTip",Vector3.ZERO,Vector3(.22,0,0),radius,metal)
		_rod(root,"Lumen",Vector3(-.001,0,0),Vector3(.003,0,0),radius*.65,dark)
	var shaft_radius:=radius if id in ["phaco","ia","injector"] else .020
	_rod(root,"Shaft",Vector3(.20,0,0),Vector3(3.05,0,0),shaft_radius,metal)
	if id in ["phaco","ia"]:
		_rod(root,"Sleeve",Vector3(.22,0,0),Vector3(.75,0,0),radius*1.35,white)
		_rod(root,"Handpiece",Vector3(3.05,0,0),Vector3(5.1,0,0),.32,blue if id=="phaco" else white)
		for i in range(5): _rod(root,"GripBand",Vector3(3.3+i*.22,0,0),Vector3(3.34+i*.22,0,0),.335,metal)
		_rod(root,"Tubing",Vector3(5.1,0,0),Vector3(7.,.12,0),.09,blue)
	elif id=="injector":
		_rod(root,"Cartridge",Vector3(3.05,0,0),Vector3(4.5,0,0),.20,white)
		_rod(root,"Plunger",Vector3(4.5,0,0),Vector3(5.5,0,0),.12,blue)
	elif id=="cannula":
		_rod(root,"Hub",Vector3(3.05,0,0),Vector3(3.5,0,0),.14,gold)
		_rod(root,"Syringe",Vector3(3.5,0,0),Vector3(5.5,0,0),.25,white)
	else: _rod(root,"Handle",Vector3(3.05,0,0),Vector3(5.3,0,0),.15,blue if id=="knife" else gold)
	return root
static func _material(color:Color,roughness:float,metallic:float)->StandardMaterial3D:
	var mat:=StandardMaterial3D.new(); mat.albedo_color=color; mat.roughness=roughness; mat.metallic=metallic
	return mat
static func _rod(parent:Node3D,label:String,a:Vector3,b:Vector3,radius:float,material:Material)->void:
	var mesh:=CylinderMesh.new(); mesh.height=a.distance_to(b); mesh.top_radius=radius; mesh.bottom_radius=radius; mesh.radial_segments=16
	var node:=MeshInstance3D.new(); node.name=label; node.mesh=mesh; node.material_override=material; node.position=(a+b)*.5
	var axis:=(b-a).normalized(); var side:=Vector3.FORWARD.cross(axis).normalized()
	if side.length_squared()<.01: side=Vector3.RIGHT
	node.basis=Basis(side,axis,side.cross(axis).normalized()); parent.add_child(node)
