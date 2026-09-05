import subprocess, sys

# Install imageio and freeimage / openexr if needed, or use imageio to read EXR and write HDR
try:
    import imageio.v2 as imageio
    import numpy as np

    src = r"E:\Blender\5.2\datafiles\studiolights\world\sunset.exr"
    dst = r"E:\TalentForge\Clay\3d_engine\digital_twin_web\studiolights\sunset.hdr"

    img = imageio.imread(src)
    print("Read EXR successfully, shape:", img.shape, "dtype:", img.dtype)
    imageio.imwrite(dst, img.astype(np.float32), format='HDR-FI')
    print("Saved HDR successfully to", dst)
except Exception as e:
    print("ImageIO conversion:", e)
