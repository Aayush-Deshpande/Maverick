// Extracted from page-33beb1af07230f28.js (fragmentShader)
// -----------------------------------------

          uniform float uTime;
          uniform float uCloudSpeed;
          uniform float uCloudScale;
          uniform float uCloudDensity;
          uniform vec3 uSunPosition;
          uniform vec3 uSkyColor;
          uniform vec3 uCloudColor;
          uniform float uOffset;
          uniform float uFade;
          uniform float uZoom;
          uniform float uIndex;
          
          varying vec3 vPosition;
          varying vec3 vNormal;
          varying vec3 vViewNormal;
          varying vec2 vUv;
          varying vec3 vViewPosition;
          
          // Hash function for noise
          float hash(vec3 p) {
            p = fract(p * 0.3183099 + 0.1);
            p *= 17.0;
            return fract(p.x * p.y * p.z * (p.x + p.y + p.z));
          }
          
          // 3D Noise
          float noise(vec3 x) {
            vec3 p = floor(x);
            vec3 f = fract(x);
            f = f * f * (3.0 - 2.0 * f);
            
            float n = p.x + p.y * 157.0 + 113.0 * p.z;
            return mix(
              mix(mix(hash(vec3(n + 0.0)), hash(vec3(n + 1.0)), f.x),
                  mix(hash(vec3(n + 157.0)), hash(vec3(n + 158.0)), f.x), f.y),
              mix(mix(hash(vec3(n + 113.0)), hash(vec3(n + 114.0)), f.x),
                  mix(hash(vec3(n + 270.0)), hash(vec3(n + 271.0)), f.x), f.y),
              f.z);
          }
          
          // Fractal Brownian Motion
          float fbm(vec3 p) {
            float f = 0.0;
            float amplitude = 0.5;
            float frequency = 1.0;
            
            for(int i = 0; i < 3; i++) {
              f += amplitude * noise(p * frequency);
              amplitude *= 0.5;
              frequency *= 2.0;
            }
            
            return f;
          }
          
          void main() {
            // Create cloud pattern using FBM
            vec3 windDir = normalize(vec3(0., 1., 0.));
            vec3 pos = vPosition * uCloudScale * uZoom;
            pos -= windDir * (uTime + uOffset) * .4;
            pos.z += uTime * uCloudSpeed;
            
            float cloud = fbm(pos + uOffset);
            cloud = smoothstep(uCloudDensity - 0.2, uCloudDensity + 0.2, cloud);
            
            // Add depth variation
            float depth = fbm(pos * 0.5 + vec3(0.0, (uTime + uOffset) * 0.02, 0.0));
            cloud *= depth;
            
            // Lighting
            vec3 sunDir = normalize(uSunPosition);
            float lightDot = max(dot(vNormal, sunDir), 0.0);
            float lightIntensity = lightDot * 0.5 + 0.5;
            
            // Color mixing
            vec3 finalColor = mix(uSkyColor, uCloudColor, cloud);
            finalColor *= lightIntensity;
            
            // Add some atmospheric scattering
            float scatter = pow(1.0 - abs(vUv.y), 2.0) * 0.3;
            finalColor += scatter;
            
            // Apply fade
            float alpha = cloud * uFade;
            
            gl_FragColor = vec4(finalColor, alpha * 0.3 - uIndex * 0.01);
          }
        