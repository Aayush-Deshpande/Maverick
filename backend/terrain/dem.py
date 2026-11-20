"""Terrain elevation service (card M5-07, P Part 4 Step 5.7).

Source: Copernicus GLO-30 DSM, public AWS bucket copernicus-dem-30m (configs/planning.json "dem"), one 1 x 1 degree
GeoTIFF tile cached under var/dem/ (runtime data, never committed). The GeoTIFF georeference tags give the grid:
ModelTiepoint = (lon, lat) of pixel (0, 0), ModelPixelScale = degrees per pixel; rows run north -> south.

  elevation_m(lat, lon)   bilinear between the four surrounding posts
  block_max(step)         coarse grid of maximum elevation per step x step pixel block (conservative for clearance)
A missing tile raises TerrainUnavailable with the download command; the service never substitutes a flat terrain.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Optional, Tuple

import numpy as np


class TerrainUnavailable(RuntimeError):
    pass


class DemTile:
    def __init__(self, path: Path) -> None:
        if not path.exists():
            raise TerrainUnavailable(f"DEM tile {path.name} not found in {path.parent}: run "
                                     f"python -m backend.terrain.fetch")
        import tifffile                                     # optional dependency (requirements-optional.txt)
        with tifffile.TiffFile(path) as tif:
            page = tif.pages[0]
            tie = page.tags["ModelTiepointTag"].value
            scale = page.tags["ModelPixelScaleTag"].value
            self.z = page.asarray().astype(np.float64)
        self.name = path.stem                                  # tile id (load_tile appends .tif)
        self.lon0, self.lat0 = float(tie[3]), float(tie[4])       # north-west corner post
        self.dlon, self.dlat = float(scale[0]), float(scale[1])
        self.rows, self.cols = self.z.shape

    @property
    def bounds(self) -> Tuple[float, float, float, float]:
        """(lat_min, lat_max, lon_min, lon_max) covered by posts."""
        return (self.lat0 - (self.rows - 1) * self.dlat, self.lat0,
                self.lon0, self.lon0 + (self.cols - 1) * self.dlon)

    def contains(self, lat: float, lon: float) -> bool:
        la0, la1, lo0, lo1 = self.bounds
        return la0 <= lat <= la1 and lo0 <= lon <= lo1

    def elevation_m(self, lat: float, lon: float) -> float:
        if not self.contains(lat, lon):
            raise ValueError(f"({lat:.4f}, {lon:.4f}) is outside tile {self.name} {self.bounds}")
        r = (self.lat0 - lat) / self.dlat
        c = (lon - self.lon0) / self.dlon
        r0, c0 = min(int(r), self.rows - 2), min(int(c), self.cols - 2)
        fr, fc = r - r0, c - c0
        z = self.z
        return float((1 - fr) * ((1 - fc) * z[r0, c0] + fc * z[r0, c0 + 1])
                     + fr * ((1 - fc) * z[r0 + 1, c0] + fc * z[r0 + 1, c0 + 1]))

    def block_max(self, step: int) -> np.ndarray:
        """Maximum elevation per step x step block (edge blocks may be smaller)."""
        nr, nc = -(-self.rows // step), -(-self.cols // step)
        pad = np.full((nr * step, nc * step), -np.inf)
        pad[: self.rows, : self.cols] = self.z
        return pad.reshape(nr, step, nc, step).max(axis=(1, 3))


def tile_name(lat: float, lon: float) -> str:
    """Copernicus GLO-30 tile name for the 1-degree cell containing (lat, lon) (northern / eastern hemisphere)."""
    return f"Copernicus_DSM_COG_10_N{int(np.floor(lat)):02d}_00_E{int(np.floor(lon)):03d}_00_DEM"


@lru_cache(maxsize=4)
def load_tile(name: str, folder: Optional[str] = None) -> DemTile:
    if folder is None:
        from backend.runtime.paths import var_path            # lazy: keeps this module free of runtime imports
        base = var_path("dem")
    else:
        base = Path(folder)
    return DemTile(base / f"{name}.tif")
