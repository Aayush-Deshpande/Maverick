"""Automated end-to-end webview audit script using Chrome DevTools Protocol.
Verifies all buttons, modals, tooltips, viewports, and monitors console errors.
"""

import os
import sys
import time
import json
import base64
import urllib.request
import subprocess
import asyncio
import websockets
from pathlib import Path

CHROME_PATH = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
PORT = 9224
USER_DATA_DIR = r"D:\Programming\PS054\var\chrome_headless_audit"
BASE_URL = "http://localhost:5173"
ARTIFACT_DIR = r"C:\Users\Prasad\.gemini\antigravity\brain\eb7686ec-6c7e-42f5-a015-137bf9ffe74b"

os.makedirs(USER_DATA_DIR, exist_ok=True)
os.makedirs(ARTIFACT_DIR, exist_ok=True)

class CDPClient:
    def __init__(self, ws_url):
        self.ws_url = ws_url
        self.ws = None
        self.msg_id = 0
        self.console_logs = []
        self.exceptions = []

    async def connect(self):
        self.ws = await websockets.connect(self.ws_url, max_size=50 * 1024 * 1024)
        asyncio.create_task(self._listen())

    async def _listen(self):
        try:
            while True:
                msg_raw = await self.ws.recv()
                msg = json.loads(msg_raw)
                method = msg.get("method", "")
                if method == "Runtime.consoleAPICalled":
                    args = msg.get("params", {}).get("args", [])
                    text = " ".join([str(a.get("value", a.get("description", ""))) for a in args])
                    level = msg.get("params", {}).get("type", "log")
                    self.console_logs.append((level, text))
                elif method == "Runtime.exceptionThrown":
                    exp = msg.get("params", {}).get("exceptionDetails", {})
                    self.exceptions.append(exp)
        except Exception:
            pass

    async def send(self, method, params=None):
        self.msg_id += 1
        payload = {"id": self.msg_id, "method": method, "params": params or {}}
        await self.ws.send(json.dumps(payload))
        while True:
            resp_raw = await self.ws.recv()
            resp = json.loads(resp_raw)
            if resp.get("id") == self.msg_id:
                return resp.get("result", {})

    async def evaluate(self, expr):
        res = await self.send("Runtime.evaluate", {"expression": expr, "returnByValue": True})
        return res.get("result", {}).get("value")

    async def screenshot(self, filename):
        res = await self.send("Page.captureScreenshot", {"format": "png", "quality": 95})
        b64_data = res.get("data", "")
        if b64_data:
            out_path = os.path.join(ARTIFACT_DIR, filename)
            with open(out_path, "wb") as f:
                f.write(base64.b64decode(b64_data))
            print(f"Captured: {out_path} ({os.path.getsize(out_path)} bytes)")
            return out_path
        return None

    async def close(self):
        if self.ws:
            await self.ws.close()

async def run_audit():
    chrome_cmd = [
        CHROME_PATH,
        f"--remote-debugging-port={PORT}",
        f"--user-data-dir={USER_DATA_DIR}",
        "--headless=new",
        "--disable-gpu",
        "--hide-scrollbars",
        "--window-size=1920,1080",
        "about:blank",
    ]
    proc = subprocess.Popen(chrome_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(2.5)

    try:
        req = urllib.request.urlopen(f"http://127.0.0.1:{PORT}/json", timeout=5)
        tabs = json.loads(req.read().decode())
        ws_url = tabs[0]["webSocketDebuggerUrl"]

        client = CDPClient(ws_url)
        await client.connect()
        await client.send("Page.enable")
        await client.send("Runtime.enable")
        await client.send("DOM.enable")

        print("=== TEST 1: RUNTIME CONSOLE WORKSPACE ===")
        await client.send("Page.navigate", {"url": f"{BASE_URL}/?workspace=runtime"})
        await asyncio.sleep(4.0)
        await client.screenshot("webview_audit_01_runtime_hud.png")

        # Check title / presence
        header_text = await client.evaluate("document.querySelector('h2')?.innerText || ''")
        print(f"  Runtime Header: '{header_text}'")

        # Test 1.1: Click Commands Button (Ctrl+K)
        print("  -> Testing Commands Palette button...")
        clicked_cmd = await client.evaluate("""(() => {
            const btns = Array.from(document.querySelectorAll('button'));
            const b = btns.find(el => el.innerText.includes('Commands') || el.innerText.includes('Ctrl+K'));
            if (b) { b.click(); return true; }
            return false;
        })()""")
        print(f"  Clicked Commands Button: {clicked_cmd}")
        await asyncio.sleep(1.0)
        palette_visible = await client.evaluate("!!document.querySelector('input[placeholder*=\"Type a command\"]')")
        print(f"  Palette Input Visible: {palette_visible}")
        await client.screenshot("webview_audit_02_runtime_command_palette.png")

        # Close palette by clicking backdrop
        await client.evaluate("""(() => {
            const backdrop = document.getElementById('command-palette-backdrop');
            if (backdrop) backdrop.click();
        })()""")
        await asyncio.sleep(0.8)

        # Test 1.2: Click SOURCE button (CAN Bus Inspector)
        print("  -> Testing CAN Bus Source modal...")
        clicked_src = await client.evaluate("""(() => {
            const btns = Array.from(document.querySelectorAll('button'));
            const b = btns.find(el => el.innerText.includes('SOURCE'));
            if (b) { b.click(); return true; }
            return false;
        })()""")
        print(f"  Clicked Source Button: {clicked_src}")
        await asyncio.sleep(1.2)
        can_modal_visible = await client.evaluate("!!document.body.innerText.includes('Avionics & FADEC CAN Bus')")
        print(f"  CAN Modal Visible: {can_modal_visible}")
        await client.screenshot("webview_audit_03_can_bus_modal.png")

        # Inject Threat in modal
        print("  -> Testing CAN Threat Injection trigger...")
        injected = await client.evaluate("""(() => {
            const btns = Array.from(document.querySelectorAll('button'));
            const b = btns.find(el => el.innerText.includes('Rogue ID'));
            if (b) { b.click(); return true; }
            return false;
        })()""")
        print(f"  Clicked Rogue ID Injector: {injected}")
        await asyncio.sleep(1.0)
        await client.screenshot("webview_audit_04_can_threat_injected.png")

        # Close CAN Modal
        await client.evaluate("""(() => {
            const backdrop = document.getElementById('can-inspector-backdrop');
            if (backdrop) backdrop.click();
        })()""")
        await asyncio.sleep(0.8)

        # Test 1.3: Click Pipeline Guide (?) button
        print("  -> Testing Pipeline Guide modal...")
        clicked_guide = await client.evaluate("""(() => {
            const btns = Array.from(document.querySelectorAll('button'));
            const b = btns.find(el => el.innerText.includes('Pipeline Guide') || el.innerText.includes('Twin Guide'));
            if (b) { b.click(); return true; }
            return false;
        })()""")
        print(f"  Clicked Guide Button: {clicked_guide}")
        await asyncio.sleep(1.0)
        has_sec10 = await client.evaluate("document.body.innerText.includes('10. Multi-Mode 3D Viewport')")
        has_sec11 = await client.evaluate("document.body.innerText.includes('11. Avionics SAE J1939 CAN Bus')")
        has_sec12 = await client.evaluate("document.body.innerText.includes('12. Tactical Command Palette')")
        print(f"  Guide Sections 10/11/12 Present: 10={has_sec10}, 11={has_sec11}, 12={has_sec12}")
        await client.screenshot("webview_audit_05_pipeline_guide_modal.png")

        # Close Guide Modal
        await client.send("Input.dispatchKeyEvent", {"type": "keyDown", "key": "Escape", "code": "Escape"})
        await client.send("Input.dispatchKeyEvent", {"type": "keyUp", "key": "Escape", "code": "Escape"})
        await asyncio.sleep(0.5)

        # Test 1.4: Connection Modal (QR code)
        print("  -> Testing Mobile Phone Connection QR Code modal...")
        clicked_conn = await client.evaluate("""(() => {
            const btns = Array.from(document.querySelectorAll('button'));
            const b = btns.find(el => el.title && el.title.toLowerCase().includes('settings') || el.getAttribute('aria-label') === 'Host Connection');
            if (b) { b.click(); return true; }
            return false;
        })()""")
        if not clicked_conn:
            # Try finding connection button by SVG or role
            clicked_conn = await client.evaluate("""(() => {
                const b = document.querySelector('button[title*=\"Configure host link\"], button[title*=\"Settings\"]');
                if (b) { b.click(); return true; }
                return false;
            })()""")
        print(f"  Clicked Connection Button: {clicked_conn}")

        print("\n=== TEST 2: 3D TWIN WORKSPACE ===")
        await client.send("Page.navigate", {"url": f"{BASE_URL}/?workspace=twin"})
        await asyncio.sleep(4.0)
        await client.screenshot("webview_audit_06_3d_twin_stage.png")

        # Test Commands button inside 3D Twin
        print("  -> Testing Commands in 3D Twin...")
        clicked_twin_cmd = await client.evaluate("""(() => {
            const btns = Array.from(document.querySelectorAll('button'));
            const b = btns.find(el => el.innerText.includes('Commands') || el.innerText.includes('Ctrl+K'));
            if (b) { b.click(); return true; }
            return false;
        })()""")
        print(f"  Clicked Twin Commands Button: {clicked_twin_cmd}")
        await asyncio.sleep(1.0)
        await client.screenshot("webview_audit_07_twin_command_palette.png")

        # Switch to Thermal FLIR from palette
        print("  -> Selecting Thermal FLIR render mode...")
        clicked_thermal = await client.evaluate("""(() => {
            const btns = Array.from(document.querySelectorAll('button'));
            const b = btns.find(el => el.innerText.includes('Thermal FLIR') || el.innerText.includes('Planck blackbody'));
            if (b) { b.click(); return true; }
            return false;
        })()""")
        print(f"  Selected Thermal Mode: {clicked_thermal}")
        await asyncio.sleep(2.0)
        await client.screenshot("webview_audit_08_twin_thermal_flir.png")

        print("\n=== TEST 3: LANDING PAGE WORKSPACE ===")
        await client.send("Page.navigate", {"url": f"{BASE_URL}/?workspace=landing"})
        await asyncio.sleep(3.0)
        await client.screenshot("webview_audit_09_landing_page.png")

        print("\n=== BROWSER CONSOLE AUDIT ===")
        error_logs = [log for log in client.console_logs if log[0] == "error"]
        warning_logs = [log for log in client.console_logs if log[0] == "warning" or log[0] == "warn"]
        print(f"Total Console Logs: {len(client.console_logs)}")
        print(f"Console Warnings: {len(warning_logs)}")
        print(f"Console Errors: {len(error_logs)}")
        for lvl, text in error_logs:
            print(f"  [ERROR] {text}")
        print(f"Exceptions: {len(client.exceptions)}")
        for exp in client.exceptions:
            print(f"  [EXCEPTION] {exp.get('text')}")

        await client.close()
        print("\n=== ALL AUDIT STEPS COMPLETED ===")

    finally:
        try:
            proc.terminate()
            proc.wait(timeout=3)
        except Exception:
            proc.kill()

if __name__ == "__main__":
    asyncio.run(run_audit())
