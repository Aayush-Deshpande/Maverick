import cv2
img = cv2.imread(r"e:\TalentForge\Clay\3d_engine\digital_twin_web\frames\frame_000.jpg")
bg_pixel = img[10, 10] # Top-left background pixel in BGR
print(f"Background RGB: [{bg_pixel[2]}, {bg_pixel[1]}, {bg_pixel[0]}] -> Hex: #{bg_pixel[2]:02X}{bg_pixel[1]:02X}{bg_pixel[0]:02X}")
