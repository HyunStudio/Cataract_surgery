extends Control
## Patient monitor and depth diagram read the exact procedure snapshot.
var state: Dictionary = {}
var tip := Vector3(.5,.5,.12)
var depth_mode := false
var high_contrast := false
var font: Font
const MINT := Color("79e0c0")
const DIM := Color("76949c")

func _ready() -> void:
	mouse_filter = Control.MOUSE_FILTER_IGNORE
	font = SystemFont.new()
	font.font_names = PackedStringArray(["Malgun Gothic", "Arial"])

func _draw() -> void:
	if not font:
		return
	if depth_mode:
		draw_depth()
		return
	var w := size.x
	var t: float = float(state.get("tick",0))/60.0
	var alert: String = state.get("alert", "")
	var hr: int = 104 if not alert.is_empty() else 74
	draw_string(font,Vector2(16,25),"PATIENT MONITOR",HORIZONTAL_ALIGNMENT_LEFT,-1,12,DIM)
	draw_string(font,Vector2(16,53),"심박수  /  ECG",HORIZONTAL_ALIGNMENT_LEFT,-1,14,Color.WHITE)
	draw_string(font,Vector2(16,105),str(hr),HORIZONTAL_ALIGNMENT_LEFT,-1,46,MINT)
	draw_string(font,Vector2(104,103),"bpm",HORIZONTAL_ALIGNMENT_LEFT,-1,13,DIM)
	var line: PackedVector2Array = []
	for i in range(int(w)-32):
		var phase := fposmod(float(i)/125.0+t*float(hr)/60.,1.)
		var ecg := .055*sin(phase*TAU)
		ecg += .18*exp(-pow((phase-.20)/.045,2.))
		ecg -= .18*exp(-pow((phase-.38)/.018,2.))
		ecg += .95*exp(-pow((phase-.42)/.012,2.))
		ecg -= .32*exp(-pow((phase-.46)/.018,2.))
		ecg += .22*exp(-pow((phase-.70)/.08,2.))
		line.append(Vector2(i+16,154-ecg*35.))
	for gy in range(125,184,12):
		draw_line(Vector2(16,gy),Vector2(w-16,gy),Color(.12,.24,.25),1.)
	draw_polyline(line,MINT,1.8,true)
	draw_line(Vector2(16,199),Vector2(w-16,199),Color("29434d"))
	draw_string(font,Vector2(16,226),"SpO₂",HORIZONTAL_ALIGNMENT_LEFT,-1,14,DIM)
	draw_string(font,Vector2(w-85,228),"91 %" if alert == "monitor" else "99 %",HORIZONTAL_ALIGNMENT_LEFT,-1,23,Color("77c9ed"))
	draw_string(font,Vector2(16,264),"혈압",HORIZONTAL_ALIGNMENT_LEFT,-1,14,DIM)
	draw_string(font,Vector2(w-119,266),"122 / 76",HORIZONTAL_ALIGNMENT_LEFT,-1,21,Color("e7d4a5"))
	draw_string(font,Vector2(16,302),"가상 환자 · 합성 신호",HORIZONTAL_ALIGNMENT_LEFT,-1,12,DIM)
	draw_string(font,Vector2(16,325),"● 안정" if alert.is_empty() else "! 상태 확인 필요",HORIZONTAL_ALIGNMENT_LEFT,-1,14,MINT if alert.is_empty() else Color("ffb583"))

func draw_depth() -> void:
	var w := size.x
	var center := Vector2(w*.48,87)
	draw_string(font,Vector2(16,24),"DEPTH GUIDE  /  도구 깊이",HORIZONTAL_ALIGNMENT_LEFT,-1,12,DIM)
	# A section through the same normalized procedure depth used by input.
	var cornea: PackedVector2Array = []
	var lens_top: PackedVector2Array = []
	var lens_bottom: PackedVector2Array = []
	for i in range(65):
		var x := float(i)/64.*2.-1.
		cornea.append(center+Vector2(x*w*.30,-28.*sqrt(maxf(0.,1.-x*x))))
		lens_top.append(center+Vector2(x*w*.14,11.-12.*sqrt(maxf(0.,1.-x*x))))
		lens_bottom.append(center+Vector2(x*w*.14,11.+12.*sqrt(maxf(0.,1.-x*x))))
	draw_polyline(cornea,Color("64b8d2"),2,true)
	draw_polyline(lens_top,Color("d9bc7a"),2,true)
	draw_polyline(lens_bottom,Color("d9bc7a"),2,true)
	draw_line(center+Vector2(-w*.25,0),center+Vector2(-w*.12,0),MINT,3)
	draw_line(center+Vector2(w*.12,0),center+Vector2(w*.25,0),MINT,3)
	var p := center+Vector2((tip.x-.5)*w*.55,-tip.z*100.)
	draw_line(p+Vector2(35,-45),p,Color("e6edf0"),3,true)
	draw_circle(p,4.,Color("ffc579"))
	draw_string(font,Vector2(16,139),"Shift + 휠: 깊이    ·    휠: 확대",HORIZONTAL_ALIGNMENT_LEFT,-1,12,DIM)
	draw_string(font,Vector2(w-198,139),"Z %+.2f  ·  게임 좌표" % tip.z,HORIZONTAL_ALIGNMENT_LEFT,-1,12,MINT)
