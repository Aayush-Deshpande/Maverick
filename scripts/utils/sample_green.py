import cv2
import numpy as np

# Load user's uploaded image
img_path = r"C:\Users\Aayush\.gemini\antigravity-ide\brain\e2548946-1632-4c38-b23b-948278f5e132\.user_uploaded\media_1787871447179.jpg"
img = cv2.imread(img_path)

if img is not None:
    # Let's find green pixels (higher G relative to R and B)
    # BGR format in OpenCV
    b, g, r = cv2.split(img)
    green_mask = (g.astype(int) > r.astype(int) + 20) & (g.astype(int) > b.astype(int) + 20) & (g > 40)
    
    green_pixels = img[green_mask]
    if len(green_pixels) > 0:
        # Calculate mean, median, min, max green values (in RGB)
        rgb_greens = green_pixels[:, [2, 1, 0]] # BGR to RGB
        mean_rgb = np.mean(rgb_greens, axis=0).astype(int)
        median_rgb = np.median(rgb_greens, axis=0).astype(int)
        
        # Also sample top 10% brightest and 10% darkest green
        luminance = 0.299 * rgb_greens[:, 0] + 0.587 * rgb_greens[:, 1] + 0.114 * rgb_greens[:, 2]
        sorted_indices = np.argsort(luminance)
        
        dark_rgb = rgb_greens[sorted_indices[int(len(sorted_indices)*0.1)]]
        mid_rgb = rgb_greens[sorted_indices[int(len(sorted_indices)*0.5)]]
        bright_rgb = rgb_greens[sorted_indices[int(len(sorted_indices)*0.9)]]
        
        print("Green color sampling results:")
        print(f"Mean RGB: {mean_rgb.tolist()} -> Hex: #{mean_rgb[0]:02X}{mean_rgb[1]:02X}{mean_rgb[2]:02X}")
        print(f"Median RGB: {median_rgb.tolist()} -> Hex: #{median_rgb[0]:02X}{median_rgb[1]:02X}{median_rgb[2]:02X}")
        print(f"Shadow Green (10th percentile): {dark_rgb.tolist()} -> Hex: #{dark_rgb[0]:02X}{dark_rgb[1]:02X}{dark_rgb[2]:02X}")
        print(f"Midtone Green (50th percentile): {mid_rgb.tolist()} -> Hex: #{mid_rgb[0]:02X}{mid_rgb[1]:02X}{mid_rgb[2]:02X}")
        print(f"Highlight Green (90th percentile): {bright_rgb.tolist()} -> Hex: #{bright_rgb[0]:02X}{bright_rgb[1]:02X}{bright_rgb[2]:02X}")
else:
    print("Could not load image.")
