// Extracted from page-33beb1af07230f28.js (vertexShader)
// -----------------------------------------
#define GLSLIFY 1
varying vec3 vViewNormal;
varying vec2 vUv;
varying vec3 vModelPosition;
varying vec3 vWorldPosition;
varying vec3 vViewPosition;

uniform float uTime;

const float speed = 80.0;

void main() {
    vec3 pos = position;
    vUv = uv;

    float noise = sin(vUv.y * 81.0 - uTime * speed) *
        cos(vUv.x * 41.0 - uTime * speed * 0.5) *
        sin((vUv.x + vUv.y) * 12.0 - uTime * speed * 0.7);
    pos.x += noise * 0.01;

    vec4 viewPosition = modelViewMatrix * vec4(pos, 1.0);

    gl_Position = projectionMatrix * viewPosition;

    vViewNormal = normalMatrix * normal;
    vModelPosition = position;
    vWorldPosition = (modelMatrix * vec4(pos, 1.0)).xyz;
    vViewPosition = -viewPosition.xyz;
}
