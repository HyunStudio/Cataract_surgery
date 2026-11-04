extends RefCounted
## Objective compressible Neo-Hookean membrane energy over real cut-cell area.
## Scalar double arithmetic avoids deriving force differences from float32
## display vertices. An experimental energy evaluator, not a time integrator,
## contact solve, bending model or clinically calibrated tissue law.
var _cells:Array[Dictionary]=[]
var _count:=0
static func invalid(reason:String)->Dictionary:
	return {"valid":false,"reason":reason}
func configure(original:PackedVector3Array,indices:PackedInt32Array,support:Dictionary)->bool:
	if not support.get("valid",false) or not support.has("cells") or not support.has("controls"):return false
	if indices.is_empty() or indices.size()%3!=0 or indices.size()>24576 or original.size()>4096:return false
	var count:int=support.controls.size()
	if count<3 or count>24576 or support.cells.is_empty() or support.cells.size()>8192:return false
	for id in support.controls:
		if id<0 or id>=original.size():return false
	var cells:Array[Dictionary]=[]
	for cell in support.cells:
		if not cell is Dictionary or not cell.has_all(["parent","nodes","area"]) or not cell.parent is int or not cell.nodes is Vector3i:return false
		if cell.parent<0 or cell.parent*3+2>=indices.size() or not (cell.area is float or cell.area is int) or not is_finite(cell.area) or cell.area<=0.:return false
		for node in [cell.nodes.x,cell.nodes.y,cell.nodes.z]:
			if node<0 or node>=count:return false
		if cell.nodes.x==cell.nodes.y or cell.nodes.y==cell.nodes.z or cell.nodes.z==cell.nodes.x:return false
		var triangle:=PackedVector3Array()
		for j in range(3):
			var index:int=indices[cell.parent*3+j]
			if index<0 or index>=original.size() or not original[index].is_finite() or original[index].length_squared()>256.:return false
			if support.controls[cell.nodes[j]]!=index:return false
			triangle.append(original[index])
		var first:=PackedFloat64Array();var last:=PackedFloat64Array()
		for j in range(3):
			first.append(float(triangle[1][j])-triangle[0][j]);last.append(float(triangle[2][j])-triangle[0][j])
		var length_sq:=0.;var other_sq:=0.;var product:=0.
		for j in range(3):length_sq+=first[j]*first[j];other_sq+=last[j]*last[j];product+=first[j]*last[j]
		var determinant:float=length_sq*other_sq-product*product
		if not is_finite(determinant) or determinant<1e-20 or length_sq<1e-20:return false
		var length:=sqrt(length_sq);var height:=sqrt(determinant/length_sq);var horizontal:=product/length
		var gx:=PackedFloat64Array([-1./length,1./length,0.])
		var gy:=PackedFloat64Array([horizontal/(length*height)-1./height,-horizontal/(length*height),1./height])
		cells.append({"nodes":cell.nodes,"area":float(cell.area),"gx":gx,"gy":gy})
	_cells=cells;_count=count
	return true

func evaluate(xyz:PackedFloat64Array,mu:float,lambda:float)->Dictionary:
	if _cells.is_empty() or xyz.size()!=_count*3:return invalid("state_size")
	if not is_finite(mu) or mu<=0. or not is_finite(lambda) or lambda<0.:return invalid("material")
	for value in xyz:
		if not is_finite(value) or absf(value)>16.:return invalid("coordinate")
	var gradient:=PackedFloat64Array();gradient.resize(xyz.size())
	var energy:=0.;var minimum_area_ratio:=INF
	for cell in _cells:
		var fx:=PackedFloat64Array([0.,0.,0.]);var fy:=fx.duplicate()
		for j in range(3):
			for axis in range(3):
				fx[axis]+=xyz[cell.nodes[j]*3+axis]*cell.gx[j]
				fy[axis]+=xyz[cell.nodes[j]*3+axis]*cell.gy[j]
		var c00:=0.;var c01:=0.;var c11:=0.
		for axis in range(3):c00+=fx[axis]*fx[axis];c01+=fx[axis]*fy[axis];c11+=fy[axis]*fy[axis]
		var determinant:float=c00*c11-c01*c01
		if not is_finite(determinant) or determinant<=1e-20:return invalid("collapsed_cell")
		var logarithm:float=.5*log(determinant);var coefficient:float=lambda*logarithm-mu
		energy+=cell.area*(.5*mu*(c00+c11-2.-2.*logarithm)+.5*lambda*logarithm*logarithm)
		minimum_area_ratio=minf(minimum_area_ratio,sqrt(determinant))
		for axis in range(3):
			var px:float=mu*fx[axis]+coefficient*(fx[axis]*c11-fy[axis]*c01)/determinant
			var py:float=mu*fy[axis]+coefficient*(fy[axis]*c00-fx[axis]*c01)/determinant
			for j in range(3):gradient[cell.nodes[j]*3+axis]+=cell.area*(px*cell.gx[j]+py*cell.gy[j])
	if not is_finite(energy):return invalid("energy_overflow")
	for value in gradient:
		if not is_finite(value):return invalid("gradient_overflow")
	return {"valid":true,"reason":"","energy":energy,"gradient":gradient,"minimum_area_ratio":minimum_area_ratio}
