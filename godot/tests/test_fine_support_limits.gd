extends SceneTree
const Support=preload("res://scripts/membrane_support.gd")
var failures:=0
func check(ok:bool,message:String)->void:
	if not ok:failures+=1;push_error(message)
func _initialize()->void:
	var original:=PackedVector3Array([Vector3.ZERO,Vector3.RIGHT,Vector3.BACK]);var ids:=PackedInt32Array([0,1,2])
	var points:=PackedVector3Array([Vector3(1./3.,0.,1./3.)]);var rows:Array[PackedFloat64Array]=[PackedFloat64Array([1./3.,1./3.,1./3.])]
	for k in range(8191):
		var w:PackedFloat64Array
		if k<2731:
			var t:=float(k)/2731.;w=PackedFloat64Array([1.-t,t,0.])
		elif k<5461:
			var t:=float(k-2731)/2730.;w=PackedFloat64Array([0.,1.-t,t])
		else:
			var t:=float(k-5461)/2730.;w=PackedFloat64Array([t,0.,1.-t])
		points.append(Vector3(w[1],0.,w[2]));rows.append(w)
	var indices:=PackedInt32Array();var ancestors:=PackedInt32Array();var areas:=PackedFloat64Array();var material:=PackedFloat64Array()
	for k in range(8191):
		var next:=(k+1)%8191+1;indices.append_array(PackedInt32Array([0,k+1,next]));ancestors.append(0)
		for index in [0,k+1,next]:material.append_array(rows[index])
		var a:PackedFloat64Array=rows[k+1];var b:PackedFloat64Array=rows[next]
		areas.append(((a[1]-rows[0][1])*(b[2]-rows[0][2])-(a[2]-rows[0][2])*(b[1]-rows[0][1]))*.5)
	check(not Support.build(original,ids,points,indices,ancestors,areas,1.,material).valid,"default support preserves legacy fine capacity")
	var result:=Support.build(original,ids,points,indices,ancestors,areas,1.,material,8192)
	check(result.valid and result.controls.size()==3 and result.point_nodes.size()==8192,"8192fine points may share exactly three mechanical controls")
	var too_many:=original.duplicate();too_many.resize(4097)
	check(not Support.build(too_many,ids,points,indices,ancestors,areas,1.,material,8192).valid,"extended fine geometry does not extend the original mechanical basis limit")
	points=PackedVector3Array();indices=PackedInt32Array();ancestors=PackedInt32Array();areas=PackedFloat64Array();material=PackedFloat64Array()
	for i in range(60):
		for j in range(60-i):
			if ancestors.size()>=1366:break
			var base:=points.size();var x:=i/64.;var z:=j/64.;var step:=.4/64.
			for p in [Vector2(x,z),Vector2(x+step,z),Vector2(x,z+step)]:
				points.append(Vector3(p.x,0.,p.y));material.append_array(PackedFloat64Array([1.-p.x-p.y,p.x,p.y]))
			indices.append_array(PackedInt32Array([base,base+1,base+2]));ancestors.append(0);areas.append(step*step*.5)
	var excessive:=Support.build(original,ids,points,indices,ancestors,areas,1.,material,8192)
	check(not excessive.valid and excessive.reason=="control_budget","4098independent fragment controls cannot bypass the mechanical cap")
	print("Fine support limits: ",failures," failures");quit(1 if failures else 0)
