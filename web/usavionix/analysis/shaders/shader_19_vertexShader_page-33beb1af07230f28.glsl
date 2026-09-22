// Extracted from page-33beb1af07230f28.js (vertexShader)
// -----------------------------------------
#define GLSLIFY 1
varying vec2 vUv;
varying vec3 vViewNormal;
varying vec3 vPosition;
varying vec3 vWorldPosition;
varying vec3 vViewPosition;

void main() {
    vUv = uv;
    vPosition = position;
    vWorldPosition = (modelMatrix * vec4(position, 1.0)).xyz;
    vViewNormal = normalMatrix * normalize(vec3(2.0 * normal.x, 1.0 * normal.y, 2.0 * normal.z));
    vec4 mvPosition = modelViewMatrix * vec4(position, 1.0);
    vViewPosition = -mvPosition.xyz;
    gl_Position = projectionMatrix * mvPosition;
}