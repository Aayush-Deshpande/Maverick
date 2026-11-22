"""Capture screenshots of CAN Bus Inspector and Command Palette via Chrome CDP."""

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
from pathlib import Path

CHROME_PATH = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
PORT = 9223
USER_DATA_DIR = r"D:\Programming\PS054\var\chrome_headless_can"
TARGET_URL = "http://localhost:5173/?workspace=runtime"
ARTIFACT_DIR = r"C:\Users\Prasad\.gemini\antigravity\brain\eb7686ec-6c7e-42f5-a015-137bf9ffe74b"
os.makedirs(USER_DATA_DIR, exist_ok=True)
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
    chrome_cmd = [
        CHROME_PATH,
        f"--remote-debugging-port={PORT}",
        f"--user-data-dir={USER_DATA_DIR}",
        "--headless=new",
        "--disable-gpu",
        "--hide-scrollbars",
        "--window-size=1600,1000",
        "--no-first-run",
        "--no-default-browser-check",
        TARGET_URL
    ]
    proc = subprocess.Popen(chrome_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    print("Launched headless Chrome CDP...")

    ws_url = None
    for _ in range(30):
        await asyncio.sleep(0.5)
        try:
            req = urllib.request.urlopen(f"http://127.0.0.1:{PORT}/json/list")
            tabs = json.loads(req.read().decode())
            if tabs:
                ws_url = tabs[0].get("webSocketDebuggerUrl")
                if ws_url:
                    break
        except Exception:
            pass

    if not ws_url:
        print("Failed to get WebSocket debugger URL")
        proc.kill()
        return

    cdp = CDPClient(ws_url)
    await cdp.connect()
    try:
        await cdp.send("Page.enable")
        await cdp.send("Runtime.enable")
        await cdp.send("DOM.enable")

        print("Waiting 5s for 3D twin and WebSockets to settle...")
        await asyncio.sleep(5)

        # 1. Main Overview
        res = await cdp.send("Page.captureScreenshot", {"format": "png"})
        main_path = os.path.join(ARTIFACT_DIR, "gcs_overview_hud.png")
        with open(main_path, "wb") as f:
            f.write(base64.b64decode(res["data"]))
        print(f"Captured: {main_path}")

        # 2. Click Commands (Ctrl+K) button
        js_click_cmd = """
        (() => {
            const btns = Array.from(document.querySelectorAll('button'));
            const btn = btns.find(b => b.textContent && b.textContent.includes('Commands'));
            if (btn) { btn.click(); return true; }
            return false;
        })()
        """
        r = await cdp.send("Runtime.evaluate", {"expression": js_click_cmd, "returnByValue": True})
        print("Clicked Commands button:", r.get("result", {}).get("value"))
        await asyncio.sleep(1.0)

        res = await cdp.send("Page.captureScreenshot", {"format": "png"})
        cmd_path = os.path.join(ARTIFACT_DIR, "gcs_command_palette.png")
        with open(cmd_path, "wb") as f:
            f.write(base64.b64decode(res["data"]))
        print(f"Captured: {cmd_path}")

        # Press Escape / Close palette
        js_esc = """
        (() => {
            window.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape' }));
            return true;
        })()
        """
        await cdp.send("Runtime.evaluate", {"expression": js_esc, "returnByValue": True})
        await asyncio.sleep(0.5)

        # 3. Click SOURCE button to open CAN Bus Inspector
        js_click_can = """
        (() => {
            const btns = Array.from(document.querySelectorAll('button'));
            const btn = btns.find(b => b.textContent && b.textContent.includes('SOURCE'));
            if (btn) { btn.click(); return true; }
            return false;
        })()
        """
        r = await cdp.send("Runtime.evaluate", {"expression": js_click_can, "returnByValue": True})
        print("Clicked SOURCE button:", r.get("result", {}).get("value"))
        await asyncio.sleep(1.5)

        res = await cdp.send("Page.captureScreenshot", {"format": "png"})
        can_path = os.path.join(ARTIFACT_DIR, "gcs_can_bus_inspector.png")
        with open(can_path, "wb") as f:
            f.write(base64.b64decode(res["data"]))
        print(f"Captured: {can_path}")

    finally:
        await cdp.close()
        proc.kill()
        shutil.rmtree(USER_DATA_DIR, ignore_errors=True)
        print("Capture complete.")

if __name__ == "__main__":
    asyncio.run(run_capture())
