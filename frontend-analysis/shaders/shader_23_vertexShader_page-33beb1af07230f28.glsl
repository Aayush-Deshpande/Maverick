// Extracted from page-33beb1af07230f28.js (vertexShader)
// -----------------------------------------
#define GLSLIFY 1
varying vec3 vPosition;
varying vec3 vWorldPosition;
varying vec2 vUv;

void main() {
    vUv = uv;
    vPosition = position;
    vec4 mvPosition = modelViewMatrix * vec4(position, 1.0);
    gl_Position = projectionMatrix * mvPosition;
    vWorldPosition = (modelMatrix * vec4(position, 1.0)).xyz;
}

