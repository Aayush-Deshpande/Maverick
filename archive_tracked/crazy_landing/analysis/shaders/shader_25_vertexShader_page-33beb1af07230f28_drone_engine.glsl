// Extracted from page-33beb1af07230f28.js (vertexShader)
// -----------------------------------------
#define GLSLIFY 1
varying vec3 vViewNormal;
varying vec2 vUv;
varying vec3 vModelPosition;
varying vec3 vWorldPosition;
varying vec3 vViewPosition;
varying vec3 vNormal;

void main() {
    vec3 pos = position;
    vec3 transformedNormal = normal;
    
    #ifdef USE_INSTANCING
      mat4 instanceModelMatrix = instanceMatrix;
      pos = (instanceModelMatrix * vec4(pos, 1.0)).xyz;
      transformedNormal = mat3(instanceModelMatrix) * normal;
    #endif
    
    vec4 mvPosition = modelViewMatrix * vec4(pos, 1.0);
    gl_Position = projectionMatrix * mvPosition;
    
    #ifdef USE_INSTANCING
      vViewNormal = normalMatrix * mat3(instanceModelMatrix) * normal;
      vWorldPosition = (modelMatrix * instanceModelMatrix * vec4(position, 1.0)).xyz;
    #else
      vViewNormal = normalMatrix * normal;
      vWorldPosition = (modelMatrix * vec4(pos, 1.0)).xyz;
    #endif
    
    vUv = uv;
    vModelPosition = position;
    vViewPosition = -mvPosition.xyz;
    vNormal = transformedNormal;
}
