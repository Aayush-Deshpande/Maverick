import urllib.request
import re
import json

def search_github_web(term):
    url = f"https://github.com/search?q={urllib.parse.quote(term)}&type=repositories"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=10) as r:
            html = r.read().decode('utf-8', errors='ignore')
            # Look for repo links
            links = re.findall(r'href="\/([a-zA-Z0-9_\-]+\/[a-zA-Z0-9_\-]+)"\s+data-testid="list-item-title"', html)
            if not links:
                links = re.findall(r'class="v-align-middle"[^>]*>([^<]+)<\/a>', html)
            print(f"Term: {term} -> {links[:5]}")
            return links[:5]
    except Exception as e:
        print(f"Error for {term}: {e}")
        return []

import urllib.parse
terms = [
    "Aeronex SIH",
    "Aeronex UAV",
    "Aetheris GAT",
    "InnovativeX SIH",
    "InnovativeX UAV",
    "Nirvanaa SIH",
    "SIH26054",
    "Jay Suryawanshi",
    "Bala Sabarish"
]

for t in terms:
    search_github_web(t)
