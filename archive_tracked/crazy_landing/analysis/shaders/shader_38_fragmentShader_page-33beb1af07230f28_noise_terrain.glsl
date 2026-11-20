// Extracted from page-33beb1af07230f28.js (fragmentShader)
// -----------------------------------------

            varying vec2 vUv; 
            uniform vec3 uBgColor;
            uniform sampler2D uBlueNoiseTexture;
            uniform float uStrength;

            void main() {
            	vec2 blueNoiseTexelSize = vec2(textureSize(uBlueNoiseTexture, 0));
              vec4 blueNoiseSample = texture2D(uBlueNoiseTexture, gl_FragCoord.xy / blueNoiseTexelSize);

              gl_FragColor = vec4(uBgColor, smoothstep(uStrength, 1.0, 1.0 - vUv.y) + blueNoiseSample.x / 255.0);
            }