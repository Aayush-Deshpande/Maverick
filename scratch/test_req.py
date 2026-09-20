import requests
import json
from bs4 import BeautifulSoup

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36',
    'Accept-Language': 'en-US,en;q=0.9',
}
r = requests.get('https://www.bing.com/images/search?q=Bayraktar+TB2+blueprint&form=HDRSC2&first=1', headers=headers, timeout=10)
soup = BeautifulSoup(r.text, 'html.parser')
iusc = soup.find_all('a', class_='iusc')
print('Direct requests found iusc:', len(iusc))
for i, el in enumerate(iusc):
    try:
        m = json.loads(el['m'])
        title = m.get('t', '')
        murl = m.get('murl', '')
        print(f"[{i}] {title[:50]} -> {murl[:60]}")
    except:
        pass
