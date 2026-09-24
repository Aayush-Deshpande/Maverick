from PIL import Image, ImageDraw, ImageFont
import os

img_path = r"e:\backup-llm\backup-no-llm\3d_engine\3d_models\renders\render_02_wireframe_subdiv0_fdda.png"
artifact_path = r"C:\Users\Aayush\.gemini\antigravity-ide\brain\59abf336-b0e2-4242-aa30-d1e91dfcd0a7\render_02_wireframe_subdiv0_fdda.png"

if os.path.exists(img_path):
    im = Image.open(img_path).convert("RGBA")
    draw = ImageDraw.Draw(im)
    
    text = "Subdivision Level 0"
    
    # Try system fonts
    font_names = ["segoeui.ttf", "arial.ttf", "calibri.ttf", "tahoma.ttf"]
    font = None
    for fn in font_names:
        try:
            font = ImageFont.truetype(fn, 36)
            break
        except Exception:
            pass
    if font is None:
        font = ImageFont.load_default()
        
    # Measure text
    bbox = draw.textbbox((0, 0), text, font=font)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    
    # Top-right position matching fdda7fefdc.jpg (~50px from top, 60px from right)
    x = im.width - tw - 65
    y = 48
    
    # Pure clean white text with 95% opacity
    draw.text((x, y), text, font=font, fill=(245, 245, 245, 240))
    
    # Save back
    im.convert("RGB").save(img_path, "PNG")
    im.convert("RGB").save(artifact_path, "PNG")
    print(f"Successfully stamped '{text}' onto {img_path} and artifact!")
