import os

target_file = os.path.join('web', 'usavionix', 'mirror', 'index.html')
if os.path.exists(target_file):
    with open(target_file, 'r', encoding='utf-8') as f:
        content = f.read()

    target = '<head>'
    replacement = '<head><link rel="stylesheet" href="/assets/fonts/pixelcode/pixelcode.css"><style>body, * { --font-geist-mono: "Pixel Code", monospace !important; } .font-mono, [class*="mono"], .text-m-mono, .text-d-mono, [data-nav-touch] span { font-family: "Pixel Code", monospace !important; }</style>'

    if '/assets/fonts/pixelcode/pixelcode.css' not in content:
        content = content.replace(target, replacement, 1)
        with open(target_file, 'w', encoding='utf-8') as f:
            f.write(content)
        print('Successfully injected Pixel Code into usavionix mirror index.html')
    else:
        print('Pixel Code already present in usavionix mirror index.html')
else:
    print('File not found:', target_file)
