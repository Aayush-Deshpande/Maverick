// Extracted from page-33beb1af07230f28.js (vertexShader)
// -----------------------------------------
#define GLSLIFY 1
varying vec2 vUv;
varying vec3 vViewNormal;
varying vec3 vPosition;
varying vec3 vViewPosition;
varying vec3 vWorldPosition;
varying vec3 vWorldNormal;

void main() {
    vUv = uv;
    vPosition = position;
    vViewNormal = normalMatrix * normalize(vec3(2.0 * normal.x, 1.0 * normal.y, 2.0 * normal.z));
    vWorldNormal = normalize((modelMatrix * vec4(normal, 0.0)).xyz);
    vec4 worldPosition = modelMatrix * vec4(position, 1.0);
    vWorldPosition = worldPosition.xyz;
    vec4 mvPosition = modelViewMatrix * vec4(position, 1.0);
    vViewPosition = -mvPosition.xyz;
    gl_Position = projectionMatrix * mvPosition;
}
