from playwright.sync_api import sync_playwright
import urllib.parse, json, requests
from PIL import Image
import os

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    q = 'Bayraktar TB2 high resolution in flight'
    encoded_q = urllib.parse.quote(q)
    search_url = f"https://www.bing.com/images/search?q={encoded_q}&form=HDRSC2&first=1"
    page.goto(search_url, wait_until="domcontentloaded")
    page.wait_for_timeout(2000)
    elements = page.query_selector_all("a.iusc")
    print("Found elements:", len(elements))
    for el in elements[:5]:
        m = json.loads(el.get_attribute("m"))
        murl = m.get("murl")
        turl = m.get("turl")
        title = m.get("t", "")
        desc = m.get("desc", "")
        combined = (title + " " + desc + " " + murl).lower()
        print("Title:", title[:50])
        print("murl:", murl[:70])
        relevant_keys = ["bayraktar", "drone", "uav", "ucav", "aircraft", "rotax", "austro", "tei", "lark", "blueprint", "drawing"]
        rel = any(k in combined for k in relevant_keys)
        print("Is relevant:", rel)
        # Test download
        try:
            r = requests.get(murl, timeout=5, verify=False, headers={'User-Agent': 'Mozilla/5.0'})
            print("Status code:", r.status_code, "Length:", len(r.content))
        except Exception as e:
            print("Download err:", e)
    browser.close()
