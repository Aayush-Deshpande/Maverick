// Extracted from page-33beb1af07230f28.js (fragmentShader)
// -----------------------------------------
#define GLSLIFY 1
uniform sampler2D uWindTexture;
uniform float uTime;
uniform float uSpeed;
uniform float uFramesPerRow;
uniform float uAlpha;

varying vec2 vUv;

void main() {
    float totalFrames = uFramesPerRow * uFramesPerRow;
    float frameIndex = mod(floor(uTime * uSpeed), totalFrames);
    
    float row = floor(frameIndex / uFramesPerRow);
    float col = mod(frameIndex, uFramesPerRow);
    
    vec2 frameSize = vec2(1.0 / uFramesPerRow);
    float flippedRow = uFramesPerRow - 1.0 - row;
    vec2 frameOffset = vec2(col, flippedRow) * frameSize;

    vec2 frameUv = vUv * frameSize + frameOffset;
    
    vec2 rotatedUv = vec2(1.0) - frameUv;
    
    vec4 color = texture2D(uWindTexture, rotatedUv);
    
    gl_FragColor = color;
    gl_FragColor.a *= uAlpha;
}

