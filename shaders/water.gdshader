shader_type spatial;
render_mode blend_mix, cull_back, diffuse_lambert, specular_schlick_ggx;

// Lightweight pond water: a single sine ripple in the vertex shader plus a
// flat tint. No textures, no screen reads — cheap enough for a low-poly
// mobile scene.

uniform vec4 water_color : source_color = vec4(0.25, 0.55, 0.65, 0.8);
uniform float wave_speed = 1.0;
uniform float wave_height = 0.03;

void vertex() {
	VERTEX.y += sin(TIME * wave_speed + VERTEX.x * 2.0 + VERTEX.z * 2.0) * wave_height;
}

void fragment() {
	ALBEDO = water_color.rgb;
	ALPHA = water_color.a;
	ROUGHNESS = 0.1;
	SPECULAR = 0.7;
}
