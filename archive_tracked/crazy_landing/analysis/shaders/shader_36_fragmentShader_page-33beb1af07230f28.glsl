// Extracted from page-33beb1af07230f28.js (fragmentShader)
// -----------------------------------------

            uniform sampler2D map;
            uniform float opacity;
            varying vec2 vUv;
            void main() {
              vec2 uv = vUv;
              if (uv.y < 0.32) {
                uv.y = 0.0;
              } else {
                uv.y = (uv.y - 0.32) / 0.68;
              }

              vec4 texColor = texture2D(map, uv);
              texColor.a = texColor.a * 1.35;
              // texColor *= smoothstep(0.00, 0.15, 1.0 - uv.y);
              gl_FragColor = texColor;
            }
          