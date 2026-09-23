import urllib.request
import urllib.parse
import json

def search_gh_code(query):
    url = f"https://api.github.com/search/code?q={urllib.parse.quote(query)}"
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0', 'Accept': 'application/vnd.github.v3+json'})
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            data = json.loads(r.read().decode())
            print(f'Query "{query}": {data.get("total_count", 0)} results')
            for item in data.get('items', [])[:3]:
                print(f"  {item['repository']['full_name']} -> {item['path']}")
    except Exception as e:
        print(f'Error for "{query}": {e}')

search_gh_code("AERO-P4-EXP4")
search_gh_code("P4-HORIZ-OPP")
search_gh_code("Aetheris SIH26054")
search_gh_code("Aeronex SIH26054")
