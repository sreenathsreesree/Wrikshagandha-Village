shader_type spatial;
render_mode blend_mix, cull_back, diffuse_lambert, specular_schlick_ggx;

// Cheap per-vertex sway for grass/flowers/leaves, plus a lightweight
// "bend away from the player" response driven by a single global uniform
// (VegetationController updates it once per frame, not per-blade — safe
// for mobile even with many instances on screen).

uniform vec4 base_color : source_color = vec4(0.4, 0.65, 0.25, 1.0);
uniform float sway_speed = 1.5;
uniform float sway_amount = 0.06;
uniform float roughness_value : hint_range(0.0, 1.0) = 0.9;

global uniform vec3 wg_player_position;

const float BEND_RADIUS = 1.35;
const float BEND_STRENGTH = 0.3;

void vertex() {
	float phase = TIME * sway_speed + VERTEX.x * 3.0 + VERTEX.z * 3.0;
	// Scale by height above the mesh's own base so the sway pivots near
	// the ground instead of rocking the whole prop.
	float lever = clamp(VERTEX.y, 0.0, 4.0);
	VERTEX.x += sin(phase) * sway_amount * lever;
	VERTEX.z += cos(phase * 0.8) * sway_amount * 0.5 * lever;

	vec3 world_pos = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
	vec2 offset = world_pos.xz - wg_player_position.xz;
	float dist = length(offset);
	float bend = clamp(1.0 - dist / BEND_RADIUS, 0.0, 1.0);
	bend *= bend;
	vec2 away = dist > 0.0001 ? normalize(offset) : vec2(0.0, 1.0);
	VERTEX.xz += away * bend * BEND_STRENGTH * lever;
}

void fragment() {
	ALBEDO = base_color.rgb;
	ROUGHNESS = roughness_value;
}
