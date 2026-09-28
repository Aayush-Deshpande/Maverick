"""Real terrain elevation sampling from the actual Ladakh canyon GLB mesh (ARCH-2026-MP-001).

Loads the vertex positions straight out of the glTF binary (no Draco compression on this
asset, so no decoder dependency is needed) and rasterizes them once into a bilinear-
interpolated height grid, mirroring the pattern the standalone Blender flight sim uses
(``TacticalTerrainRadar`` in ``apps/blender_twin/standalone_canyon_flight_app.py``): O(1)
lookups per query instead of a per-frame mesh raycast.

Coordinate convention: the terrain GLB is loaded by the browser client
(``apps/canyon_flight/index.html``) with no scale/rotation/translation applied — its local
mesh X/Z axes ARE the scene's East/North-ish local meters, and mesh-local Y already IS
absolute elevation in meters AMSL (confirmed against real Ladakh altitudes, 3050-6200m).
This module treats those same raw mesh coordinates as the mission's local ENU frame, so a
mission waypoint's (pos_x_m, pos_y_m) maps directly onto (mesh_x, -mesh_z) with zero
reprojection -- guaranteeing the physics AGL and the rendered terrain always agree.
"""

from __future__ import annotations

import json
import logging
import struct
from pathlib import Path
from typing import Optional, Tuple

logger = logging.getLogger("MissionTerrain")

_GLTF_CHUNK_JSON = 0x4E4F534A
_GLTF_CHUNK_BIN = 0x004E4942

_COMPONENT_SIZES = {
    5120: 1,  # BYTE
    5121: 1,  # UNSIGNED_BYTE
    5122: 2,  # SHORT
    5123: 2,  # UNSIGNED_SHORT
    5125: 4,  # UNSIGNED_INT
    5126: 4,  # FLOAT
}
_COMPONENT_FORMAT = {
    5120: "b", 5121: "B", 5122: "h", 5123: "H", 5125: "I", 5126: "f",
}


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _read_glb_positions(glb_path: Path) -> Tuple[list, list, list]:
    """Parses a (non-Draco) glTF-Binary file and returns the first mesh primitive's
    POSITION accessor as parallel (xs, ys, zs) lists, using only stdlib struct/json."""
    data = glb_path.read_bytes()
    magic, version, length = struct.unpack_from("<4sII", data, 0)
    if magic != b"glTF":
        raise ValueError(f"{glb_path} is not a valid .glb file (bad magic)")

    offset = 12
    json_chunk = None
    bin_chunk = None
    while offset < length:
        chunk_len, chunk_type = struct.unpack_from("<II", data, offset)
        chunk_data = data[offset + 8: offset + 8 + chunk_len]
        if chunk_type == _GLTF_CHUNK_JSON:
            json_chunk = json.loads(chunk_data)
        elif chunk_type == _GLTF_CHUNK_BIN:
            bin_chunk = chunk_data
        offset += 8 + chunk_len

    if json_chunk is None or bin_chunk is None:
        raise ValueError(f"{glb_path} is missing JSON or BIN chunk")

    if json_chunk.get("extensionsUsed") and "KHR_draco_mesh_compression" in json_chunk["extensionsUsed"]:
        raise ValueError(
            f"{glb_path} uses Draco compression; this lightweight parser only reads "
            "plain (uncompressed) glTF accessors. Decode it to a plain .glb first."
        )

    meshes = json_chunk.get("meshes", [])
    if not meshes or not meshes[0].get("primitives"):
        raise ValueError(f"{glb_path} has no mesh primitives")

    pos_accessor_idx = meshes[0]["primitives"][0]["attributes"]["POSITION"]
    accessor = json_chunk["accessors"][pos_accessor_idx]
    buffer_view = json_chunk["bufferViews"][accessor["bufferView"]]

    component_type = accessor["componentType"]
    count = accessor["count"]
    if accessor.get("type") != "VEC3" or component_type != 5126:
        raise ValueError("Expected VEC3 float32 POSITION accessor")

    start = buffer_view.get("byteOffset", 0) + accessor.get("byteOffset", 0)
    fmt = f"<{count * 3}f"
    floats = struct.unpack_from(fmt, bin_chunk, start)

    xs = list(floats[0::3])
    ys = list(floats[1::3])
    zs = list(floats[2::3])
    return xs, ys, zs


class TerrainHeightfield:
    """Bilinear-interpolated elevation grid sampled once from a terrain mesh's raw
    vertex positions. Local mesh (X, Z) are treated directly as mission ENU (east, -north)."""

    def __init__(self, grid_resolution: int = 160) -> None:
        self.grid_resolution = grid_resolution
        self.min_x = 0.0
        self.max_x = 0.0
        self.min_z = 0.0
        self.max_z = 0.0
        self._grid: Optional[list] = None  # [gx][gz] -> elevation (min of cell, ground floor)
        self._fallback_elev_m: float = 3097.64
        self._loaded = False

    @property
    def loaded(self) -> bool:
        return self._loaded

    def load(self, glb_path: Optional[Path] = None) -> None:
        """Loads and rasterizes the terrain mesh. Safe to call once at mission-executive
        startup; cheap enough (~46k vertices) to redo per process if ever needed."""
        path = glb_path or (_repo_root() / "frontend" / "public" / "models" / "ladakh_canyon_terrain.glb")
        try:
            xs, ys, zs = _read_glb_positions(path)
        except Exception as err:
            logger.error("Failed to load terrain mesh %s for real AGL computation: %s", path, err)
            self._loaded = False
            return

        if not xs:
            logger.error("Terrain mesh %s produced zero vertices", path)
            self._loaded = False
            return

        self.min_x, self.max_x = min(xs), max(xs)
        self.min_z, self.max_z = min(zs), max(zs)
        nx = nz = self.grid_resolution
        span_x = max(1e-6, self.max_x - self.min_x)
        span_z = max(1e-6, self.max_z - self.min_z)

        grid = [[None] * nz for _ in range(nx)]
        for x, y, z in zip(xs, ys, zs):
            gx = min(nx - 1, int((x - self.min_x) / span_x * nx))
            gz = min(nz - 1, int((z - self.min_z) / span_z * nz))
            cell = grid[gx][gz]
            if cell is None or y < cell:
                grid[gx][gz] = y

        # Fill any empty cells (gaps in the point cloud) from nearest filled neighbour so
        # bilinear lookups never hit a hole.
        fallback = sum(v for row in grid for v in row if v is not None)
        filled_count = sum(1 for row in grid for v in row if v is not None)
        self._fallback_elev_m = fallback / filled_count if filled_count else 3097.64
        for gx in range(nx):
            for gz in range(nz):
                if grid[gx][gz] is None:
                    grid[gx][gz] = self._nearest_filled(grid, gx, gz, nx, nz)

        self._grid = grid
        self._loaded = True
        logger.info(
            "Terrain heightfield loaded from %s: %dx%d grid, X[%.0f,%.0f] Z[%.0f,%.0f], mean elev %.0fm",
            path.name, nx, nz, self.min_x, self.max_x, self.min_z, self.max_z, self._fallback_elev_m,
        )

    @staticmethod
    def _nearest_filled(grid: list, gx: int, gz: int, nx: int, nz: int) -> float:
        for radius in range(1, max(nx, nz)):
            for dx in range(-radius, radius + 1):
                for dz in range(-radius, radius + 1):
                    x2, z2 = gx + dx, gz + dz
                    if 0 <= x2 < nx and 0 <= z2 < nz and grid[x2][z2] is not None:
                        return grid[x2][z2]
        return 3097.64

    def elevation_at(self, enu_x_m: float, enu_y_m: float) -> float:
        """Returns ground elevation (m AMSL) at local ENU (east=enu_x_m, north=enu_y_m).

        Terrain mesh Z axis is -north (see module docstring), so we look up mesh Z = -enu_y_m.
        """
        if not self._loaded or self._grid is None:
            return self._fallback_elev_m

        mesh_z = -enu_y_m
        nx = nz = self.grid_resolution
        span_x = max(1e-6, self.max_x - self.min_x)
        span_z = max(1e-6, self.max_z - self.min_z)

        # Clamp query to grid bounds (outside the authored terrain -> flat extrapolation
        # from the nearest edge, not a fabricated fresh height field).
        fx = (enu_x_m - self.min_x) / span_x * nx - 0.5
        fz = (mesh_z - self.min_z) / span_z * nz - 0.5
        fx = max(0.0, min(nx - 1.001, fx))
        fz = max(0.0, min(nz - 1.001, fz))

        gx0, gz0 = int(fx), int(fz)
        gx1, gz1 = min(nx - 1, gx0 + 1), min(nz - 1, gz0 + 1)
        tx, tz = fx - gx0, fz - gz0

        h00 = self._grid[gx0][gz0]
        h10 = self._grid[gx1][gz0]
        h01 = self._grid[gx0][gz1]
        h11 = self._grid[gx1][gz1]

        h0 = h00 * (1 - tx) + h10 * tx
        h1 = h01 * (1 - tx) + h11 * tx
        return h0 * (1 - tz) + h1 * tz

    def in_bounds(self, enu_x_m: float, enu_y_m: float) -> bool:
        mesh_z = -enu_y_m
        return self.min_x <= enu_x_m <= self.max_x and self.min_z <= mesh_z <= self.max_z


_shared_heightfield: Optional[TerrainHeightfield] = None


def get_terrain_heightfield() -> TerrainHeightfield:
    """Process-wide singleton -- the 46k-vertex parse/rasterize only needs to happen once."""
    global _shared_heightfield
    if _shared_heightfield is None:
        _shared_heightfield = TerrainHeightfield()
        _shared_heightfield.load()
    return _shared_heightfield
