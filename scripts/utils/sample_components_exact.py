import cv2
import numpy as np

img_path = r"C:\Users\Aayush\.gemini\antigravity-ide\brain\e2548946-1632-4c38-b23b-948278f5e132\.user_uploaded\media_1787871447179.jpg"
img = cv2.imread(img_path)
H, W, _ = img.shape
print(f"Image dimensions: {W} x {H}")

# Normalize coordinates (percentages 0.0 to 1.0)
comp_coords = {
    "Background Studio Gray": (0.05, 0.05, 0.15, 0.15),
    "Valve Covers (Green '912 iS' & 'ROTAX')": (0.45, 0.40, 0.54, 0.65),
    "Airbox Body (Black Top Plenum)": (0.38, 0.12, 0.53, 0.28),
    "Airbox Lettering ('ROTAX' White Text)": (0.40, 0.13, 0.49, 0.20),
    "Intake Runners (Polished Chrome Tubes)": (0.42, 0.26, 0.49, 0.45),
    "Gearbox & Reduction Drive Hub (Machined Steel)": (0.12, 0.30, 0.23, 0.52),
    "Alternator Housing & Stator Fins (Cast Alloy)": (0.18, 0.36, 0.29, 0.52),
    "Exhaust Downpipe (Dark Heat-Treated Steel)": (0.49, 0.65, 0.60, 0.94),
    "Exhaust Canister (Muffler Body)": (0.45, 0.58, 0.54, 0.70),
    "Oil Tank / Reservoir (Shadowed Warm Steel)": (0.59, 0.08, 0.69, 0.28),
    "Fuse/ECU Box on Base (Brushed Silver Plate)": (0.55, 0.52, 0.73, 0.71),
    "ECU Lid Plate (Off-White Module Lid)": (0.76, 0.40, 0.90, 0.53),
    "ECU Base & Wiring Harness (Molded Black Plastic)": (0.71, 0.38, 0.89, 0.56),
    "High-Tension Wiring Loom & Hoses (Jet Black Rubber)": (0.56, 0.26, 0.83, 0.42),
    "Engine Crankcase Block (Center Casting)": (0.30, 0.28, 0.42, 0.48),
}

print("-----------------------------------------------------------------------------------------")
print(f"{'Component':<45} | {'RGB':<16} | {'Hex Code':<10} | {'Material Shader Grade'}")
print("-----------------------------------------------------------------------------------------")

for name, (rx1, ry1, rx2, ry2) in comp_coords.items():
    x1, y1, x2, y2 = int(rx1*W), int(ry1*H), int(rx2*W), int(ry2*H)
    crop = img[y1:y2, x1:x2]
    rgb = crop[:, :, [2, 1, 0]]
    
    # Calculate median RGB
    med = np.median(rgb, axis=(0, 1)).astype(int)
    hex_code = f"#{med[0]:02X}{med[1]:02X}{med[2]:02X}"
    
    # Determine physical shader parameters
    desc = ""
    if "Green" in name:
        desc = "Dark Forest Racing Green (Roughness 0.32, Metal 0.08)"
    elif "Chrome" in name:
        desc = "Polished Specular Chrome (Roughness 0.08, Metal 0.98)"
    elif "Black" in name or "Loom" in name:
        desc = "Jet Matte Black Rubber/Plastic (Roughness 0.65, Metal 0.0)"
    elif "White" in name:
        desc = "Off-White Satin (Roughness 0.28, Metal 0.02)"
    elif "Steel" in name or "Exhaust" in name or "Tank" in name:
        desc = "Dark Gunmetal Steel (Roughness 0.35, Metal 0.90)"
    elif "Alloy" in name or "Gearbox" in name or "Crankcase" in name or "Plate" in name:
        desc = "Aero Cast/Brushed Alloy (Roughness 0.32, Metal 0.85)"
    else:
        desc = "Studio Neutral Slate (Roughness 1.0, Metal 0.0)"
        
    print(f"{name:<45} | {str(med.tolist()):<16} | {hex_code:<10} | {desc}")
