shader_type spatial;
render_mode blend_mix, cull_back, diffuse_lambert, specular_disabled;

// Meadow path patches (Stage B0.1, D-61): the same flat cylinder patches, now
// a worn earth track with a darker trodden band and pebble speckle whose edge
// dissolves irregularly into the ground colour (organic_ground.gdshaderinc),
// so overlapping patches read as one winding path instead of discs. Visual
// only — no node, mesh, collider or navigation change.
// Overlaps: each patch's top slopes down from 0.03 m at its centre to the
// ground plane at its rim, so where two patches overlap the one whose centre is
// nearer is on top (no z-fighting), and no step or side wall casts a line. At
// the rim the colour is exactly the ground's, so meeting the plane shows
// nothing. Opaque — no transparency or discard.

#include "res://shaders/organic_ground.gdshaderinc"

uniform vec3 earth_light : source_color = vec3(0.66, 0.53, 0.35);
uniform vec3 earth_mid : source_color = vec3(0.56, 0.44, 0.29);
uniform vec3 earth_dark : source_color = vec3(0.42, 0.32, 0.21);
uniform vec3 pebble : source_color = vec3(0.74, 0.69, 0.6);
// The patch's top height above its base (node y 0.015 + half height 0.015).
uniform float rim_drop = 0.03;

varying vec3 v_world;
varying float v_r;
varying float v_side;

void vertex() {
	v_r = length(VERTEX.xz);
	v_side = 1.0 - step(0.0001, VERTEX.y) * step(0.9, NORMAL.y);
	if (VERTEX.y > 0.0) {
		VERTEX.y -= rim_drop * v_r * v_r;
	}
	// Lit exactly like the flat ground (the side wall too), so the rim
	// shows no seam.
	NORMAL = vec3(0.0, 1.0, 0.0);
	v_world = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
}

void fragment() {
	vec2 xz = v_world.xz;
	vec3 grass = ground_colour(xz);
	// Earth: broad tone variation, a darker trodden band, pebble speckle.
	float tone = wg_fbm(xz * 0.6 + 5.0);
	vec3 earth = mix(earth_mid, earth_light, smoothstep(0.3, 0.75, tone));
	float band = wg_value_noise(xz * 1.4 + 2.0);
	earth = mix(earth, earth_dark, smoothstep(0.62, 0.85, band) * 0.5 * (1.0 - v_r));
	float grit = wg_value_noise(xz * 9.0);
	earth = mix(earth, pebble, smoothstep(0.86, 0.97, grit) * 0.6);
	earth *= 0.92 + 0.16 * wg_value_noise(xz * 4.7 + 3.0);
	// Irregular edge: the earth gives way to grass between r 0.45 and 1.0,
	// with noise so the outline is ragged; a few grass tufts creep inwards.
	float edge = v_r + (wg_fbm(xz * 1.7 + 11.0) - 0.5) * 0.55;
	float earth_w = 1.0 - smoothstep(0.55, 0.92, edge);
	earth_w *= 1.0 - smoothstep(0.8, 0.95, wg_value_noise(xz * 5.5 - 4.0)) * 0.6;
	// The rim itself, and the thin side wall, are exactly ground colour.
	earth_w *= 1.0 - smoothstep(0.9, 0.99, v_r);
	earth_w *= 1.0 - v_side;
	ALBEDO = mix(grass, earth, earth_w);
	ROUGHNESS = mix(0.95, 1.0, earth_w);
}
