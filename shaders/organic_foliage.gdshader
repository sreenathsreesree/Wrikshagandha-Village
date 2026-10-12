shader_type spatial;
render_mode blend_mix, cull_back, diffuse_lambert, specular_schlick_ggx;

// Organic foliage (Stage B0, D-60): the same cheap per-vertex sway and
// "bend away from the player" as sway.gdshader (unchanged, still used by the
// grass/flower placeholders), plus the mesh's vertex colour, so one shared
// material serves every canopy, bush and grass tuft. Sway scales with height
// above the mesh's own origin (the ground), so trunks never move — only the
// foliage surface uses this material.

uniform vec4 tint : source_color = vec4(1.0, 1.0, 1.0, 1.0);
uniform float sway_speed = 1.2;
uniform float sway_amount = 0.02;
uniform float roughness_value : hint_range(0.0, 1.0) = 0.9;

global uniform vec3 wg_player_position;

const float BEND_RADIUS = 1.35;
const float BEND_STRENGTH = 0.3;
// Bending is for low foliage only (grass, bushes); canopies far above the
// player don't lean away from them.
const float BEND_MAX_HEIGHT = 0.8;

void vertex() {
	float phase = TIME * sway_speed + VERTEX.x * 3.0 + VERTEX.z * 3.0;
	float lever = clamp(VERTEX.y, 0.0, 4.0);
	VERTEX.x += sin(phase) * sway_amount * lever;
	VERTEX.z += cos(phase * 0.8) * sway_amount * 0.5 * lever;

	vec3 world_pos = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
	vec2 offset = world_pos.xz - wg_player_position.xz;
	float dist = length(offset);
	float bend = clamp(1.0 - dist / BEND_RADIUS, 0.0, 1.0);
	bend *= bend * step(VERTEX.y, BEND_MAX_HEIGHT);
	vec2 away = dist > 0.0001 ? normalize(offset) : vec2(0.0, 1.0);
	VERTEX.xz += away * bend * BEND_STRENGTH * lever;
}

void fragment() {
	ALBEDO = COLOR.rgb * tint.rgb;
	ROUGHNESS = roughness_value;
}
