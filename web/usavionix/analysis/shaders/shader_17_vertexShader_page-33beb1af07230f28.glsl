// Extracted from page-33beb1af07230f28.js (vertexShader)
// -----------------------------------------

  varying vec3 vViewNormal;
  varying vec2 vUv;
  varying vec3 vPosition;
  varying vec3 vWorldPosition;
  varying vec3 vViewPosition;
  varying vec3 vNormal;
  
  void main() {
      vec3 pos = position;
  
      vec4 viewPosition = modelViewMatrix * vec4(pos, 1.0);
  
      gl_Position = projectionMatrix * viewPosition;
  
      vViewNormal = normalMatrix * normal;
      vUv = uv;
      vPosition = position;
      vWorldPosition = (modelMatrix * vec4(pos, 1.0)).xyz;
      vViewPosition = -viewPosition.xyz;
      vNormal = normal;
  }
  
        