extends "res://tests/test_volumetric_encounter.gd"
var installed:=false
class Cutter extends RefCounted:
 var inner=load("res://scripts/membrane_cut.gd").new()
 var captured:=false
 var previous:Dictionary={}
 func slice_triangle(points,indices,a,b,c,max_vertices=4096,max_triangles=8192,material_partition=false)->Dictionary:
  var result:Dictionary=inner.slice_triangle(points,indices,a,b,c,max_vertices,max_triangles,material_partition)
  if not result.valid and not captured:
   captured=true
   var packet:={"points":points,"indices":indices,"patch":PackedVector3Array([a,b,c]),"max_vertices":max_vertices,"max_triangles":max_triangles,"material_partition":material_partition,"result":result,"previous":previous}
   DirAccess.make_dir_recursive_absolute("res://reports")
   FileAccess.open("res://reports/legacy-blade-first-cut-failure.bin",FileAccess.WRITE).store_var(packet)
   print("Owned legacy blade failure: ",result.reason," vertices=",points.size()," faces=",indices.size()/3)
  if result.valid and result.changed:previous=result.duplicate(true)
  return result
func tick(app,n:=1)->void:
 if not installed:
  installed=true;app.capsule._cutter=Cutter.new()
 super.tick(app,n)
