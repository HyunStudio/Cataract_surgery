extends RefCounted
## Error-free binary64 expansions, restricted to nonnegative material weights.
## This is a conservative simplification predicate, never a support/mass gate.
## Degree <=3 and inputs in [2^-128,1] keep every product/residual normal.
static func eligible(a:PackedFloat64Array)->bool:
	if a.size()!=3:return false
	var positive:=false
	for x in a:
		if not is_finite(x) or x<0. or x>1. or (x!=0. and x<pow(2.,-128.)):return false
		positive=positive or x>0.
	return positive
static func _grow(e:PackedFloat64Array,b:float)->PackedFloat64Array:
	var out:=PackedFloat64Array()
	for a in e:
		var sum:=b+a;var av:=sum-b;var bv:=sum-av
		var error:=(b-bv)+(a-av)
		if error!=0.:out.append(error)
		b=sum
	if b!=0. or out.is_empty():out.append(b)
	return out
static func _add(a:PackedFloat64Array,b:PackedFloat64Array,scale:float=1.)->PackedFloat64Array:
	var out:=a.duplicate()
	for x in b:out=_grow(out,scale*x)
	return out
static func _product(a:float,b:float)->PackedFloat64Array:
	var product:=a*b
	var ca:=134217729.*a;var ah:=ca-(ca-a);var al:=a-ah
	var cb:=134217729.*b;var bh:=cb-(cb-b);var bl:=b-bh
	var err1:=product-ah*bh;var err2:=err1-al*bh;var err3:=err2-ah*bl
	var error:=al*bl-err3
	return PackedFloat64Array([error,product]) if error!=0. else PackedFloat64Array([product])
static func _mul(a:PackedFloat64Array,b:PackedFloat64Array)->PackedFloat64Array:
	var out:=PackedFloat64Array([0.])
	for x in a:
		for y in b:out=_add(out,_product(x,y))
	return out
static func _difference(a:float,b:float)->PackedFloat64Array:
	return _grow(PackedFloat64Array([-b]),a)
static func _sign(e:PackedFloat64Array)->int:
	for j in range(e.size()-1,-1,-1):
		if e[j]!=0.:return 1 if e[j]>0. else -1
	return 0
static func orientation(a:PackedFloat64Array,b:PackedFloat64Array,c:PackedFloat64Array)->Dictionary:
	if not eligible(a) or not eligible(b) or not eligible(c):return {"valid":false,"sign":0}
	var out:=PackedFloat64Array([0.])
	for j in range(3):
		var k:=(j+1)%3;var l:=(j+2)%3
		var minor:=_add(_product(b[k],c[l]),_product(b[l],c[k]),-1.)
		out=_add(out,_mul(PackedFloat64Array([a[j]]),minor))
	var value:=0.
	for x in out:value+=x
	return {"valid":true,"sign":_sign(out),"value":value}
static func collinear_between(a:PackedFloat64Array,b:PackedFloat64Array,c:PackedFloat64Array)->bool:
	if not eligible(a) or not eligible(b) or not eligible(c):return false
	var between:=false;var ab:Array[PackedFloat64Array]=[];var bc:Array[PackedFloat64Array]=[]
	for j in range(3):
		between=between or (a[j]<b[j] and b[j]<c[j]) or (a[j]>b[j] and b[j]>c[j])
		ab.append(_difference(b[j],a[j]));bc.append(_difference(c[j],b[j]))
	if not between:return false
	for j in range(3):
		var k:=(j+1)%3
		if _sign(_add(_mul(ab[j],bc[k]),_mul(ab[k],bc[j]),-1.))!=0:return false
	return true
