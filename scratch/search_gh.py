import urllib.request
import urllib.parse
import json

def search_gh(query):
    url = f"https://api.github.com/search/repositories?q={urllib.parse.quote(query)}&sort=stars&order=desc"
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0', 'Accept': 'application/vnd.github.v3+json'})
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            data = json.loads(r.read().decode())
            print(f"=== Query: {query} (total: {data.get('total_count', 0)}) ===")
            for item in data.get('items', [])[:5]:
                print(f"- {item['full_name']}: {item['html_url']}")
                print(f"  Desc: {item.get('description')}")
    except Exception as e:
        print(f"Error searching {query}: {e}")

queries = [
    'SIH26054',
    '26054 UAV',
    '26054 digital twin',
    'Dronanetra',
    'Aeronex UAV',
    'Aetheris',
    'InnovativeX',
    'ASTRA 5',
    'Nirvanaa',
    'vikram-sharma-96',
    'Bala Sabarish',
    'Rotax 912 digital twin',
    'MALE UAV digital twin'
]

for q in queries:
    search_gh(q)
