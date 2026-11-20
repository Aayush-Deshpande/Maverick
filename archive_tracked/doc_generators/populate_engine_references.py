import os
import shutil

base_dir = r"E:\backup-llm\backup-no-llm\3d_engine\ANUMAAN\Models_Images"

copies = [
    (
        os.path.join(base_dir, "Austro AE330"),
        os.path.join(base_dir, r"TAPAS_BH201_RustomII\03_Engine_Austro_E4"),
        "TAPAS_Austro_E4"
    ),
    (
        os.path.join(base_dir, "TEI PD170"),
        os.path.join(base_dir, r"TAI_ANKA\03_Engine_TEI_PD170"),
        "ANKA_TEI_PD170"
    ),
    (
        os.path.join(base_dir, "Lark HFE"),
        os.path.join(base_dir, r"CASC_CH4\03_Engine_Lark_HFE"),
        "CH4_Lark_HFE"
    )
]

for src, dst, prefix in copies:
    os.makedirs(dst, exist_ok=True)
    count = 0
    for f in os.listdir(src):
        if f.lower().endswith(('.jpg', '.jpeg', '.png', '.webp')) and not f.startswith('.'):
            src_file = os.path.join(src, f)
            ext = os.path.splitext(f)[1]
            count += 1
            dst_file = os.path.join(dst, f"{prefix}_ref_{count:03d}{ext}")
            shutil.copy2(src_file, dst_file)
    print(f"Copied {count} files from {src} to {dst}")

# Rotax 912iS snapshot
r912_src = r"E:\backup-llm\backup-no-llm\3d_engine\ANUMAAN\Models\engine-rotax-912is-1.snapshot.15\Rotax 912iS.jpg"
r912_dst = os.path.join(base_dir, r"Bayraktar_TB2\03_Engine_Rotax_912iS\TB2_Rotax_912iS_CAD_Solid_001.jpg")
if os.path.exists(r912_src):
    shutil.copy2(r912_src, r912_dst)
    print(f"Copied Rotax 912 snapshot to {r912_dst}")

# Rotax 914 snapshot
r914_src = r"E:\backup-llm\backup-no-llm\3d_engine\ANUMAAN\Models\engine-rotax-914-1.snapshot.2\Rotax 914.jpg"
r914_dst = os.path.join(base_dir, r"MQ1_Predator\03_Engine_Rotax_914F\MQ1_Rotax_914F_CAD_Solid_001.jpg")
if os.path.exists(r914_src):
    shutil.copy2(r914_src, r914_dst)
    print(f"Copied Rotax 914 snapshot to {r914_dst}")

print("Engine references population complete!")
