uniform vec2 center_uv;     // Center of the shield (0..1 UV coordinates)
uniform float radius;    // Radius of shield in UV space
uniform vec4 color;      // Base color
uniform float time;      // Time for pulsing effect

void mainImage(out vec4 fragColor, in vec2 fragCoord) {
    // Compute distance from center
    float distance = distance(v_uv, center_uv);  // todo make this a squarred decay instead. THis also should help solve the issue, that that the shield does not visually reach the border of effectiveness
    // Alpha fades with distance
    float alpha = 1. - distance / radius;
    alpha = max(0, alpha);
    // pulsate
    alpha = alpha * (sin(time * 2) / 8 + 0.875);
    // alpha = alpha * (sin(distance  * 3.14)) + time * 0.00001;  I want a wavy pattern, that moves slowly outwards
    fragColor = vec4(color.rgb, alpha);
}
