import requests, re

def get_ddg_images(query):
    s = requests.Session()
    s.headers.update({'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36'})
    r = s.get(f'https://duckduckgo.com/?q={query}')
    vqd_match = re.search(r'vqd=([\d-]+)', r.text)
    if not vqd_match:
        vqd_match = re.search(r'vqd=\"([^\"]+)\"', r.text)
    print('VQD match:', vqd_match.group(1) if vqd_match else None)
    if vqd_match:
        params = {'l': 'us-en', 'o': 'json', 'q': query, 'vqd': vqd_match.group(1), 'f': ',,,', 'p': '1'}
        res = s.get('https://duckduckgo.com/i.js', params=params)
        print('Status:', res.status_code)
        if res.status_code == 200:
            data = res.json()
            print('Results count:', len(data.get('results', [])))
            for item in data.get('results', [])[:3]:
                print(item.get('title')[:40], item.get('image')[:60])

get_ddg_images('Bayraktar TB2')
