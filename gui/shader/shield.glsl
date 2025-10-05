uniform vec2 pos_uv;     // Center of the shield
uniform float radius;    // Radius of shield in UV space
uniform vec4 color;      // Base color
uniform float time;      // Time for pulsing effect
uniform float activity_level;  // maximum brightness multiplicator. When the shield is turned off it fades away.

void mainImage(out vec4 fragColor, in vec2 fragCoord) {
    // compute the coordinates in real
    vec2 posCoord = pos_uv.xy * iResolution.xy;

    // Compute distance from center
    float distance = distance(fragCoord, posCoord);
    // Alpha fades with distance
    float alpha = 1. - distance / radius;  // todo make this a squared decay instead. This also should help solve the issue, that that the shield does not visually reach the border of effectiveness
    alpha = max(0, alpha);
    // pulsate
    alpha = alpha * (sin(time * 2) / 8 + 0.875);
    // alpha = alpha * (sin(distance  * 3.14)) + time * 0.00001;  I want a wavy pattern, that moves slowly outwards
    alpha = alpha * activity_level;

    fragColor = vec4(color.rgb, alpha);
}
