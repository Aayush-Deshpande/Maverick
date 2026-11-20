"""Download a Copernicus GLO-30 tile into var/dem/ (card M5-07). Public bucket, no credentials.
Run: python -m backend.terrain.fetch [tile_name]   (default: the tile in configs/planning.json)
"""
from __future__ import annotations

import json
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def main(name: str | None = None) -> Path:
    from backend.runtime.paths import var_path
    dem = json.loads((ROOT / "configs" / "planning.json").read_text(encoding="utf-8"))["dem"]
    name = name or dem["tile"]
    target = var_path("dem") / f"{name}.tif"
    if not target.exists():
        url = f"{dem['bucket_url']}/{name}/{name}.tif"
        print(f"downloading {url}")
        urllib.request.urlretrieve(url, target)
    print(target)
    return target


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else None)
