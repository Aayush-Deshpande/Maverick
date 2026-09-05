import bpy, shutil, os

src_dir = r"E:\Blender\5.2\datafiles\studiolights\world"
dst_dir = r"E:\TalentForge\Clay\3d_engine\digital_twin_web\studiolights"
os.makedirs(dst_dir, exist_ok=True)

for fname in os.listdir(src_dir):
    if fname.endswith(('.exr', '.hdr', '.png', '.jpg')):
        shutil.copy2(os.path.join(src_dir, fname), os.path.join(dst_dir, fname))
        print(f"Copied {fname}")

# Let's also use Blender to convert all the EXR files to standard HDR or high quality PNG equirectangular maps
for fname in ['sunset.exr', 'sunrise.exr', 'studio.exr', 'forest.exr', 'courtyard.exr', 'interior.exr', 'city.exr', 'night.exr']:
    exr_path = os.path.join(src_dir, fname)
    if os.path.exists(exr_path):
        img = bpy.data.images.load(exr_path)
        hdr_name = fname.replace('.exr', '.hdr')
        hdr_out = os.path.join(dst_dir, hdr_name)
        img.file_format = 'HDR'
        img.filepath_raw = hdr_out
        img.save()
        print(f"Converted {fname} -> {hdr_name}")
