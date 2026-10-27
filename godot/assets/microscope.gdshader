shader_type canvas_item;
uniform float focus : hint_range(0.0,1.0) = 1.0;
uniform float illumination : hint_range(0.5,1.5) = 1.0;
uniform float vignette_strength : hint_range(0.0,1.0) = 0.35;
uniform bool high_contrast = false;
void fragment(){
 vec4 base=texture(TEXTURE,UV);
 vec2 spread=TEXTURE_PIXEL_SIZE*(1.0-clamp(focus,0.0,1.0))*2.0;
 vec3 blur=base.rgb*.40;
 blur+=(texture(TEXTURE,UV+vec2(spread.x,0.0)).rgb+texture(TEXTURE,UV-vec2(spread.x,0.0)).rgb)*.15;
 blur+=(texture(TEXTURE,UV+vec2(0.0,spread.y)).rgb+texture(TEXTURE,UV-vec2(0.0,spread.y)).rgb)*.15;
 vec3 color=mix(base.rgb,blur,(1.0-focus)*.55);
 color*=clamp(illumination,.5,1.5);
 if(high_contrast){color=clamp((color-vec3(.5))*1.18+vec3(.5),vec3(0.0),vec3(1.0));}
 float radius=length((UV-vec2(.5))*2.0);
 float field=smoothstep(.65,1.40,radius);
 color*=1.0-field*clamp(vignette_strength,0.0,1.0)*.52;
 COLOR=vec4(color,base.a);
}
