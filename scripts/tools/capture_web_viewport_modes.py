"""
Capture high-definition screenshots of the live ANUMAAN digital twin web application
in all 4 interactive rendering modes:
1. SOLID CAD PBR
2. PHYSICAL X-RAY GLASS
3. DYNAMIC THERMAL FLIR
4. HOLOGRAPHIC TWIN GHOST
"""
import os
import sys
import time
import json
import base64
import urllib.request
import subprocess
import asyncio
import shutil
import websockets

CHROME_PATH = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
PORT = 9222
USER_DATA_DIR = r"D:\Programming\PS054\var\chrome_headless"
TARGET_URL = "http://localhost:5173/?workspace=twin"
ARTIFACT_DIR = r"C:\Users\Prasad\.gemini\antigravity\brain\eb7686ec-6c7e-42f5-a015-137bf9ffe74b"
RENDERS_DIR = r"D:\Programming\PS054\assets\renders"
os.makedirs(USER_DATA_DIR, exist_ok=True)
os.makedirs(RENDERS_DIR, exist_ok=True)
os.makedirs(ARTIFACT_DIR, exist_ok=True)

class CDPClient:
    def __init__(self, ws_url):
        self.ws_url = ws_url
        self.ws = None
        self.msg_id = 0

    async def connect(self):
        self.ws = await websockets.connect(self.ws_url, max_size=50 * 1024 * 1024)

    async def send(self, method, params=None):
        self.msg_id += 1
        payload = {"id": self.msg_id, "method": method, "params": params or {}}
        await self.ws.send(json.dumps(payload))
        while True:
            resp_raw = await self.ws.recv()
            resp = json.loads(resp_raw)
            if resp.get("id") == self.msg_id:
                return resp.get("result", {})

    async def close(self):
        if self.ws:
            await self.ws.close()

async def run_capture():
    print(f"[CDP] Launching Chrome headless...")
    proc = subprocess.Popen([
        CHROME_PATH,
        "--headless=new",
        f"--remote-debugging-port={PORT}",
        "--window-size=1680,1050",
        "--hide-scrollbars",
        f"--user-data-dir={USER_DATA_DIR}",
        "about:blank"
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    try:
        # Wait for Chrome debug port to open
        ws_url = None
        for _ in range(30):
            try:
                with urllib.request.urlopen(f"http://127.0.0.1:{PORT}/json/version", timeout=1) as resp:
                    data = json.loads(resp.read().decode())
                    ws_url = data.get("webSocketDebuggerUrl")
                    if ws_url:
                        break
            except Exception:
                time.sleep(0.3)

        if not ws_url:
            print("[CDP] Failed to get WebSocket debugger URL")
            return False

        print(f"[CDP] Connected to Chrome: {ws_url}")
        browser_client = CDPClient(ws_url)
        await browser_client.connect()

        # Create new target tab
        target_res = await browser_client.send("Target.createTarget", {"url": TARGET_URL})
        target_id = target_res["targetId"]

        # Connect to page target
        page_ws_url = f"ws://127.0.0.1:{PORT}/devtools/page/{target_id}"
        page_client = CDPClient(page_ws_url)
        await page_client.connect()

        print("[CDP] Navigating to digital twin UI...")
        await page_client.send("Page.enable")
        await page_client.send("Page.navigate", {"url": TARGET_URL})

        # Wait for WebGL 3D scene & components to initialize
        print("[CDP] Waiting 4.5s for 3D digital twin GLB and textures to render...")
        await asyncio.sleep(4.5)

        modes = [
            ("SOLID", "web_view_01_solid_pbr.png", "Solid CAD PBR mode: original photorealistic aerospace materials"),
            ("X-RAY GLASS", "web_view_02_xray_glass.png", "X-Ray Glass mode: physical optical glass casing revealing internal pistons and cylinders"),
            ("THERMAL FLIR", "web_view_03_thermal_flir.png", "Thermal FLIR mode: live dynamic vertex incandescence per cylinder CHT and exhaust EGT"),
            ("TWIN GHOST", "web_view_04_twin_ghost.png", "Twin Ghost mode: holographic cyan digital twin overlay"),
        ]

        captured = []
        for label, filename, title in modes:
            print(f"[CDP] Selecting view mode: {label}...")
            # Click the corresponding HUD button
            click_expr = f"""
            (() => {{
                const buttons = Array.from(document.querySelectorAll('button'));
                const btn = buttons.find(b => b.textContent.includes('{label}') || b.title?.includes('{label}'));
                if (btn) {{
                    btn.click();
                    return true;
                }}
                return false;
            }})()
            """
            res = await page_client.send("Runtime.evaluate", {"expression": click_expr, "returnByValue": True})
            print(f"      Button click status: {res.get('result', {}).get('value')}")
            
            # Wait for material/shader switch and frame render
            await asyncio.sleep(1.8)

            # Capture screenshot
            print(f"      Capturing {filename}...")
            shot_res = await page_client.send("Page.captureScreenshot", {"format": "png"})
            b64_data = shot_res.get("data")
            if b64_data:
                img_bytes = base64.b64decode(b64_data)
                render_path = os.path.join(RENDERS_DIR, filename)
                artifact_path = os.path.join(ARTIFACT_DIR, filename)
                
                with open(render_path, "wb") as f:
                    f.write(img_bytes)
                with open(artifact_path, "wb") as f:
                    f.write(img_bytes)
                print(f"      Saved {filename} ({len(img_bytes)} bytes)")
                captured.append(filename)

        await page_client.close()
        await browser_client.close()
        return captured

    finally:
        proc.terminate()
        try:
            proc.wait(timeout=2)
        except Exception:
            proc.kill()

if __name__ == "__main__":
    results = asyncio.run(run_capture())
    print(f"\n[DONE] Captured {len(results or [])} view mode screenshots.")
