import http.server
import socketserver
import urllib.parse
import os
import mimetypes
import posixpath

PORT = 3000
DIRECTORY = os.path.dirname(os.path.abspath(__file__))

# Ensure all modern WebGL and asset MIME types are properly registered
mimetypes.add_type("application/wasm", ".wasm")
mimetypes.add_type("model/gltf-binary", ".glb")
mimetypes.add_type("model/gltf+json", ".gltf")
mimetypes.add_type("image/avif", ".avif")
mimetypes.add_type("image/webp", ".webp")
mimetypes.add_type("image/x-exr", ".exr")
mimetypes.add_type("font/woff2", ".woff2")
mimetypes.add_type("font/woff", ".woff")
mimetypes.add_type("application/javascript", ".js")
mimetypes.add_type("text/css", ".css")
mimetypes.add_type("application/json", ".json")

class AvionixHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIRECTORY, **kwargs)

    def end_headers(self):
        # Enable CORS and threading-safe headers for workers and WebGL
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "*")
        self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(200, "ok")
        self.end_headers()

    def translate_path(self, path):
        # 1. Parse URL to separate query parameters and fragment
        parsed = urllib.parse.urlsplit(path)
        clean_path = parsed.path
        
        # 2. Intercept Next.js Image Optimization Route: /_next/image?url=...
        if clean_path == "/_next/image":
            query_params = urllib.parse.parse_qs(parsed.query)
            if "url" in query_params:
                target_asset_url = query_params["url"][0]
                # Decode and clean path
                target_clean = urllib.parse.unquote(target_asset_url).split("?")[0].lstrip("/")
                local_asset_path = os.path.join(DIRECTORY, target_clean.replace("/", os.sep))
                if os.path.exists(local_asset_path):
                    return local_asset_path

        # 3. Handle Draco fallback routes
        if "draco_decoder.wasm" in clean_path:
            return os.path.join(DIRECTORY, "draco", "draco_decoder.wasm")
        if "draco_wasm_wrapper.js" in clean_path:
            return os.path.join(DIRECTORY, "draco", "draco_wasm_wrapper.js")
        if "draco_decoder.js" in clean_path:
            return os.path.join(DIRECTORY, "draco", "draco_decoder.js")

        # 4. Handle Subroute HTML rewrites: /about -> /about/index.html
        local_target = os.path.join(DIRECTORY, clean_path.lstrip("/").replace("/", os.sep))
        if os.path.isdir(local_target):
            index_candidate = os.path.join(local_target, "index.html")
            if os.path.exists(index_candidate):
                return index_candidate
        elif not os.path.exists(local_target):
            # Check if adding /index.html finds it
            candidate = os.path.join(DIRECTORY, clean_path.lstrip("/").replace("/", os.sep), "index.html")
            if os.path.exists(candidate):
                return candidate
            # Check if adding .html finds it
            candidate_html = local_target + ".html"
            if os.path.exists(candidate_html):
                return candidate_html

        # 5. Default translation
        return super().translate_path(clean_path)

def run_server():
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.ThreadingTCPServer(("", PORT), AvionixHTTPRequestHandler) as httpd:
        print("============================================================")
        print(f"Avionix High-Fidelity 3D Simulation Server Running")
        print(f"Local URL: http://localhost:{PORT}/")
        print(f"Serving Directory: {DIRECTORY}")
        print("============================================================")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nServer stopped.")

if __name__ == "__main__":
    run_server()
