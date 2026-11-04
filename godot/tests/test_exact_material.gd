extends SceneTree
var failures:=0
func check(ok:bool,message:String)->void:
 if not ok:failures+=1;push_error(message)
func _initialize()->void:
 check(FileAccess.file_exists("res://scripts/exact_material.gd"),"material reduction needs exact binary64 predicates, never proximity collinearity")
 if failures:quit(1);return
 var helper=load("res://scripts/exact_material.gd")
 var fixture:Dictionary=JSON.parse_string(FileAccess.get_file_as_string("res://tests/fixtures/exact-material-predicates.json"))
 for row in fixture.cases:
  var values:=Marshalls.base64_to_raw(row.binary64_le).to_float64_array()
  var a:=values.slice(0,3);var b:=values.slice(3,6);var c:=values.slice(6,9)
  var result:Dictionary=helper.orientation(a,b,c)
  check(result.valid and result.sign==int(row.orientation),"exact homogeneous orientation agrees with independent Fraction oracle: "+str(row))
  check(helper.collinear_between(a,b,c)==row.between,"exact affine line/between agrees with independent Fraction oracle: "+str(row))
 var a:=PackedFloat64Array([1.,0.,0.]);var b:=PackedFloat64Array([.5,.5,0.]);var c:=PackedFloat64Array([0.,1.,0.])
 check(helper.collinear_between(a,b,c),"exact material midpoint is redundant")
 check(not helper.collinear_between(a,a,c) and not helper.collinear_between(b,a,c),"endpoints and extrapolation cannot remove tissue")
 for bad in [PackedFloat64Array([NAN,0.,1.]),PackedFloat64Array([-1.,1.,1.]),PackedFloat64Array([1e-200,0.,1.]),PackedFloat64Array([0.,0.]),PackedFloat64Array([0.,0.,0.])]:
  check(not helper.orientation(bad,b,c).valid and not helper.collinear_between(bad,b,c),"unbounded/unsafe predicate data conservatively rejects")
 print("Exact material predicates: ",failures," failures");quit(1 if failures else 0)
