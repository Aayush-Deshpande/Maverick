import cv2
import numpy as np

img_path = r"C:\Users\Aayush\.gemini\antigravity-ide\brain\e2548946-1632-4c38-b23b-948278f5e132\.user_uploaded\media_1787871447179.jpg"
img = cv2.imread(img_path)

# Regions to sample [y1, y2, x1, x2]
regions = {
    "Background Studio Gray": [10, 60, 10, 60],
    "Valve Covers (Green)": [480, 560, 390, 520],
    "Airbox Body (Black)": [150, 260, 390, 510],
    "Airbox Text (ROTAX White)": [140, 200, 420, 490],
    "Intake Runners (Chrome)": [260, 380, 430, 480],
    "Alternator Housing (Alloy)": [320, 440, 180, 300],
    "Gearbox Drive Hub (Steel)": [300, 480, 120, 220],
    "Exhaust Downpipe (Dark Steel)": [680, 850, 480, 580],
    "Exhaust Canister (Muffler)": [580, 680, 440, 530],
    "Oil Tank Body (Warm Steel)": [130, 270, 600, 680],
    "Fuse/ECU Plate (Rotax Silver Box)": [540, 640, 560, 710],
    "ECU Lid Plate (White)": [390, 490, 750, 880],
    "ECU Housing (Black Plastic)": [380, 520, 710, 790],
    "Wiring Loom Cables (Black)": [280, 380, 550, 780],
    "Engine Crankcase (Center Block)": [280, 420, 320, 410],
}

print("==========================================================================")
print("EXACT COLOR GRADE ANALYSIS OF ALL ENGINE COMPONENTS FROM REFERENCE IMAGE")
print("==========================================================================")

for name, (y1, y2, x1, x2) in regions.items():
    crop = img[y1:y2, x1:x2]
    # convert BGR to RGB
    rgb = crop[:, :, [2, 1, 0]]
    mean_c = np.mean(rgb, axis=(0, 1)).astype(int)
    median_c = np.median(rgb, axis=(0, 1)).astype(int)
    hex_code = f"#{median_c[0]:02X}{median_c[1]:02X}{median_c[2]:02X}"
    print(f"Component: {name:<35} | Median RGB: {str(median_c.tolist()):<15} | Hex: {hex_code}")
