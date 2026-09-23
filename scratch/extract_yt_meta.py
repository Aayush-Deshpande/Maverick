import urllib.request
import re
import json

urls = [
    'https://www.youtube.com/watch?v=u1bJrs-CLG8',
    'https://www.youtube.com/watch?v=9R8kKCKVMqQ',
    'https://www.youtube.com/watch?v=KxE6J0IZOdk',
    'https://www.youtube.com/watch?v=oXN3gUaqNHA',
    'https://www.youtube.com/watch?v=NHvcTRt15CY',
    'https://www.youtube.com/watch?v=F1uMvmKkdms'
]

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept-Language': 'en-US,en;q=0.9'
}

for url in urls:
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=15) as resp:
            html = resp.read().decode('utf-8', errors='ignore')
            title_match = re.search(r'<title>(.*?)</title>', html)
            title = title_match.group(1) if title_match else 'No title'
            
            desc_match = re.search(r'"shortDescription":"(.*?)"', html)
            desc = desc_match.group(1) if desc_match else ''
            
            author_match = re.search(r'"ownerChannelName":"(.*?)"', html)
            author = author_match.group(1) if author_match else ''
            
            # also look for github links in description or page
            gh_links = set(re.findall(r'https?://(?:www\.)?github\.com/[a-zA-Z0-9_\-]+/[a-zA-Z0-9_\-]+', html))
            
            print(f"=== URL: {url} ===")
            print(f"TITLE: {title}")
            print(f"AUTHOR: {author}")
            print(f"DESC: {desc[:500]}")
            if gh_links:
                print(f"GITHUB LINKS: {gh_links}")
            print()
    except Exception as e:
        print(f"Error for {url}: {e}")
