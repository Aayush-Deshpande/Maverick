param(
    [Parameter(Mandatory=$true)][string]$Root,
    [int]$Port = 8791
)

$Root = (Resolve-Path $Root).Path.TrimEnd('\')

$mime = @{
    '.html' = 'text/html; charset=utf-8'
    '.htm'  = 'text/html; charset=utf-8'
    '.js'   = 'text/javascript; charset=utf-8'
    '.mjs'  = 'text/javascript; charset=utf-8'
    '.cjs'  = 'text/javascript; charset=utf-8'
    '.css'  = 'text/css; charset=utf-8'
    '.json' = 'application/json'
    '.map'  = 'application/json'
    '.glb'  = 'model/gltf-binary'
    '.gltf' = 'model/gltf+json'
    '.bin'  = 'application/octet-stream'
    '.wasm' = 'application/wasm'
    '.hdr'  = 'image/vnd.radiance'
    '.exr'  = 'image/x-exr'
    '.png'  = 'image/png'
    '.jpg'  = 'image/jpeg'
    '.jpeg' = 'image/jpeg'
    '.webp' = 'image/webp'
    '.svg'  = 'image/svg+xml'
    '.ico'  = 'image/x-icon'
    '.woff' = 'font/woff'
    '.woff2'= 'font/woff2'
    '.ttf'  = 'font/ttf'
    '.otf'  = 'font/otf'
}

$pidPath = Join-Path $env:TEMP "anumaan_threejs_server_$Port.pid"
try {
    $PID | Out-File -FilePath $pidPath -Encoding ascii -Force
} catch {}

$listener = New-Object System.Net.HttpListener
$listener.Prefixes.Add("http://127.0.0.1:$Port/")
try {
    $listener.Start()
} catch {
    Write-Host "Port $Port already in use - assuming server is already running."
    exit 0
}

Write-Host "Serving $Root at http://127.0.0.1:$Port/ [PID: $PID] (Ctrl+C to stop)"

while ($listener.IsListening) {
    try {
        $context = $listener.GetContext()
    } catch {
        break
    }
    $req = $context.Request
    $res = $context.Response
    try {
        $res.Headers.Add('Access-Control-Allow-Origin', '*')
        $res.Headers.Add('Access-Control-Allow-Methods', 'GET, HEAD, OPTIONS')
        $res.Headers.Add('Access-Control-Allow-Headers', '*')
        if ($req.HttpMethod -eq 'OPTIONS') {
            $res.StatusCode = 204
            $res.Close()
            continue
        }
        $relPath = [Uri]::UnescapeDataString($req.Url.AbsolutePath) -replace '/', '\'
        if ($relPath -eq '\') { $relPath = '\index.html' }
        $fullPath = Join-Path $Root $relPath.TrimStart('\')
        $fullPath = [System.IO.Path]::GetFullPath($fullPath)

        if (-not $fullPath.StartsWith($Root, [StringComparison]::OrdinalIgnoreCase)) {
            $res.StatusCode = 403
            $res.Close()
            continue
        }

        if (Test-Path $fullPath -PathType Leaf) {
            $ext = [System.IO.Path]::GetExtension($fullPath).ToLower()
            $ct = $mime[$ext]
            if (-not $ct) { $ct = 'application/octet-stream' }
            $res.ContentType = $ct
            $res.Headers.Add('Cache-Control', 'no-cache')
            $bytes = [System.IO.File]::ReadAllBytes($fullPath)
            $res.ContentLength64 = $bytes.Length
            if ($req.HttpMethod -ne 'HEAD') {
                $res.OutputStream.Write($bytes, 0, $bytes.Length)
            }
        } else {
            $res.StatusCode = 404
            $msg = [System.Text.Encoding]::UTF8.GetBytes("404 Not Found: $relPath")
            $res.OutputStream.Write($msg, 0, $msg.Length)
        }
    } catch {
        try { $res.StatusCode = 500 } catch {}
    } finally {
        try { $res.Close() } catch {}
    }
}
