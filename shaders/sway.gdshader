shader_type spatial;
render_mode blend_mix, cull_back, diffuse_lambert, specular_schlick_ggx;

// Cheap per-vertex sway for grass/flowers/leaves. One sin() per vertex —
// safe for mobile even with many instances on screen.

uniform vec4 base_color : source_color = vec4(0.4, 0.65, 0.25, 1.0);
uniform float sway_speed = 1.5;
uniform float sway_amount = 0.06;
uniform float roughness_value : hint_range(0.0, 1.0) = 0.9;

void vertex() {
	float phase = TIME * sway_speed + VERTEX.x * 3.0 + VERTEX.z * 3.0;
	// Scale by height above the mesh's own base so the sway pivots near
	// the ground instead of rocking the whole prop.
	float lever = clamp(VERTEX.y, 0.0, 4.0);
	VERTEX.x += sin(phase) * sway_amount * lever;
	VERTEX.z += cos(phase * 0.8) * sway_amount * 0.5 * lever;
}

void fragment() {
	ALBEDO = base_color.rgb;
	ROUGHNESS = roughness_value;
}
