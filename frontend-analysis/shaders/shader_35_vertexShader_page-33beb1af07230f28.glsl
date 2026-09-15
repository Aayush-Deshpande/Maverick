// Extracted from page-33beb1af07230f28.js (vertexShader)
// -----------------------------------------

            varying vec2 vUv;
            void main() {
              vUv = uv;
              gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
            }
          