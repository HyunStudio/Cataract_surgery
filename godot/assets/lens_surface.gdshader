shader_type spatial;
render_mode cull_disabled;
uniform float cloudiness : hint_range(0.0,1.0) = 1.0;
uniform vec4 cloud_color : source_color = vec4(0.76,0.67,0.44,1.0);
void fragment(){
 vec2 p=(UV-vec2(.5))*2.0;
 float cloud=sin(p.x*13.7+sin(p.y*9.1)*.8)*sin(p.y*10.3-p.x*3.7);
 float wisps=sin(p.x*36.0+p.y*18.0+cloud*3.0)*.025;
 float density=clamp(.65+cloud*.12+wisps,0.0,1.0);
 vec3 nucleus=mix(cloud_color.rgb*.70,cloud_color.rgb*1.08,density);
 ALBEDO=mix(vec3(.55,.66,.67),nucleus,cloudiness);
 ROUGHNESS=.35; SPECULAR=.38;
}
