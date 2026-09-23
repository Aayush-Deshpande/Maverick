import cv2
import glob
import os
import pytesseract

# Set tesseract path if in standard location, else try default
tess_paths = [
    r"C:\Program Files\Tesseract-OCR\tesseract.exe",
    r"C:\Users\Aayush\AppData\Local\Programs\Tesseract-OCR\tesseract.exe",
    r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe"
]
for p in tess_paths:
    if os.path.exists(p):
        pytesseract.pytesseract.tesseract_cmd = p
        break

frames = sorted(glob.glob('scratch/competitor_videos/*.jpg'))
ocr_results = {}

for f in frames:
    try:
        img = cv2.imread(f)
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        text = pytesseract.image_to_string(gray)
        clean_text = " ".join(text.split())
        if clean_text:
            ocr_results[os.path.basename(f)] = clean_text[:300]
            print(f"{os.path.basename(f)}: {clean_text[:120]}...")
    except Exception as e:
        print(f"Error on {f}: {e}")
