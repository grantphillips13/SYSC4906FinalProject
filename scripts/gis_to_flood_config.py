#!/usr/bin/env python3
"""
Convert GIS rasters into flood Cell-DEVS configs.

Outputs (defaults):
  - flood_gis_config.json
  - flood_viewer_gis_config.json

Usage example:
  python3 config/gis_to_flood_config.py \
    --dem /path/to/dem.tif \
    --blocked /path/to/blocked_mask.tif \
    --stride 20 \
    --water-source rc:10,10
"""

import argparse
import json
import math
from typing import Dict, Optional, Tuple

import numpy as np
import rasterio
from rasterio.warp import reproject, Resampling


CELL_TYPE_NORMAL = 0
CELL_TYPE_BLOCKED = 1
CELL_TYPE_SOURCE = 2
CELL_TYPE_RAIN = 3


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Build flood configs from GIS rasters")
    p.add_argument("--dem", required=True, help="Path to DEM GeoTIFF")
    p.add_argument("--blocked", help="Optional blocked mask raster (1=blocked)")
    p.add_argument("--stride", type=int, default=20, help="Sampling step in pixels")
    p.add_argument(
        "--elevation-levels",
        type=int,
        default=11,
        help="Number of discrete elevation levels (default: 11 -> 0..10)",
    )
    p.add_argument(
        "--water-source",
        default="center",
        help="Water source as center, highest, or rc:<row,col> in output grid, e.g. rc:10,10",
    )
    p.add_argument("--source-water", type=int, default=10, help="Source water level")
    p.add_argument("--rain-radius", type=int, default=0, help="Rain disk radius in cells (0 disables rain)")
    p.add_argument("--rain-amount", type=float, default=0.0, help="Rain amount added each step on rain cells")
    p.add_argument(
        "--rain-center",
        choices=["source", "center"],
        default="source",
        help="Center for rain disk: source or grid center",
    )
    p.add_argument("--target-rows", type=int, default=28, help="Fixed output grid rows")
    p.add_argument("--target-cols", type=int, default=28, help="Fixed output grid cols")
    p.add_argument(
        "--model-out",
        default="flood_gis_config.json",
        help="Output simulation config path",
    )
    p.add_argument(
        "--viewer-out",
        default="flood_viewer_gis_config.json",
        help="Output viewer config path",
    )
    return p.parse_args()


def cell_id(r: int, c: int) -> str:
    return f"({r},{c})"


def moore_neighbor_coords(r: int, c: int, rows: int, cols: int):
    for dr in (-1, 0, 1):
        for dc in (-1, 0, 1):
            if dr == 0 and dc == 0:
                continue
            nr, nc = r + dr, c + dc
            if 0 <= nr < rows and 0 <= nc < cols:
                yield nr, nc


def load_dem_sampled(path: str, stride: int) -> np.ndarray:
    with rasterio.open(path) as src:
        dem = src.read(1).astype(np.float32)
        nodata = src.nodata

    if nodata is not None:
        dem = np.where(dem == nodata, np.nan, dem)

    return dem[::stride, ::stride]


def load_blocked_sampled(path: str, dem_path: str, stride: int, out_shape: Tuple[int, int]) -> np.ndarray:
    """Read blocked raster and align to DEM grid before sampling."""
    with rasterio.open(dem_path) as dem_src:
        dem_transform = dem_src.transform
        dem_crs = dem_src.crs
        dem_height = dem_src.height
        dem_width = dem_src.width

    with rasterio.open(path) as blk_src:
        blk = blk_src.read(1).astype(np.float32)
        dst = np.zeros((dem_height, dem_width), dtype=np.float32)
        reproject(
            source=blk,
            destination=dst,
            src_transform=blk_src.transform,
            src_crs=blk_src.crs,
            dst_transform=dem_transform,
            dst_crs=dem_crs,
            resampling=Resampling.nearest,
        )

    sampled = dst[::stride, ::stride]
    if sampled.shape != out_shape:
        sampled = sampled[: out_shape[0], : out_shape[1]]
    return sampled


def parse_water_source(s: str, rows: int, cols: int) -> Tuple[int, int]:
    if s == "center":
        return rows // 2, cols // 2
    if s == "highest":
        return -1, -1
    if s.startswith("rc:"):
        part = s[3:]
        r_txt, c_txt = part.split(",")
        r, c = int(r_txt), int(c_txt)
        if not (0 <= r < rows and 0 <= c < cols):
            raise ValueError("--water-source rc:<r,c> out of range")
        return r, c
    raise ValueError("--water-source must be 'center' or rc:<row,col>")


def resolve_valid_source_cell(
    requested: Tuple[int, int], valid_cell_mask: np.ndarray
) -> Tuple[int, int]:
    if requested == (-1, -1):
        valid_positions = np.argwhere(valid_cell_mask)
        if valid_positions.size == 0:
            raise RuntimeError("No valid DEM cells available for water source placement")
        # Caller uses this sentinel for "highest" after remapping to valid positions.
        return -1, -1

    req_r, req_c = requested
    if valid_cell_mask[req_r, req_c]:
        return requested

    valid_positions = np.argwhere(valid_cell_mask)
    if valid_positions.size == 0:
        raise RuntimeError("No valid DEM cells available for water source placement")

    nearest_r, nearest_c = min(
        valid_positions,
        key=lambda pos: math.hypot(int(pos[0]) - req_r, int(pos[1]) - req_c),
    )
    print(
        f"Requested source ({req_r},{req_c}) is not a valid sampled DEM cell; "
        f"using nearest valid cell ({int(nearest_r)},{int(nearest_c)}) instead."
    )
    return int(nearest_r), int(nearest_c)


def choose_highest_cell(dem_grid: np.ndarray, valid_mask: np.ndarray) -> Tuple[int, int]:
    masked = np.where(valid_mask, dem_grid, -np.inf)
    idx = np.unravel_index(int(np.argmax(masked)), masked.shape)
    return int(idx[0]), int(idx[1])


def in_rain_disk(r: int, c: int, center_r: int, center_c: int, radius: int) -> bool:
    if radius <= 0:
        return False
    dr = r - center_r
    dc = c - center_c
    return (dr * dr + dc * dc) <= (radius * radius)


def build_fixed_dense_grid(
    dem_sampled: np.ndarray,
    blocked_sampled: Optional[np.ndarray],
    target_rows: int,
    target_cols: int,
) -> Tuple[np.ndarray, Optional[np.ndarray], np.ndarray]:
    valid_cell_mask = ~np.isnan(dem_sampled)
    valid_positions = np.argwhere(valid_cell_mask)
    if valid_positions.size == 0:
        raise RuntimeError("DEM has no valid cells after sampling")

    min_r = int(valid_positions[:, 0].min())
    max_r = int(valid_positions[:, 0].max())
    min_c = int(valid_positions[:, 1].min())
    max_c = int(valid_positions[:, 1].max())

    dem_compact = dem_sampled[min_r : max_r + 1, min_c : max_c + 1]
    compact_valid = ~np.isnan(dem_compact)

    if target_rows <= 0 or target_cols <= 0:
        raise ValueError("--target-rows and --target-cols must be positive")

    row_idx = np.linspace(0, dem_compact.shape[0] - 1, target_rows).round().astype(int)
    col_idx = np.linspace(0, dem_compact.shape[1] - 1, target_cols).round().astype(int)

    dem_grid = dem_compact[np.ix_(row_idx, col_idx)].astype(np.float32)
    source_valid_mask = compact_valid[np.ix_(row_idx, col_idx)]

    if not np.any(source_valid_mask):
        raise RuntimeError("No valid DEM cells in fixed output grid")

    fill_value = float(np.nanmedian(dem_compact[compact_valid]))
    dem_grid = np.where(np.isnan(dem_grid), fill_value, dem_grid)

    blocked_grid: Optional[np.ndarray] = None
    if blocked_sampled is not None:
        blk_compact = blocked_sampled[min_r : max_r + 1, min_c : max_c + 1]
        blocked_grid = blk_compact[np.ix_(row_idx, col_idx)]

    return dem_grid, blocked_grid, source_valid_mask


def quantize_elevation_levels(dem_grid: np.ndarray, levels: int) -> np.ndarray:
    if levels < 2:
        raise ValueError("--elevation-levels must be >= 2")

    dem_min = float(np.min(dem_grid))
    dem_max = float(np.max(dem_grid))
    if abs(dem_max - dem_min) < 1e-12:
        return np.zeros_like(dem_grid, dtype=np.int32)

    scaled = (dem_grid - dem_min) / (dem_max - dem_min)
    quantized = np.rint(scaled * (levels - 1)).astype(np.int32)
    return np.clip(quantized, 0, levels - 1)


def interpolate_color(c1: Tuple[int, int, int], c2: Tuple[int, int, int], t: float):
    return [
        int(round(c1[0] + (c2[0] - c1[0]) * t)),
        int(round(c1[1] + (c2[1] - c1[1]) * t)),
        int(round(c1[2] + (c2[2] - c1[2]) * t)),
    ]


def build_elevation_colors(levels: int):
    low = (235, 235, 235)
    high = (72, 52, 30)
    if levels == 1:
        return [list(low)]
    return [
        interpolate_color(low, high, i / (levels - 1))
        for i in range(levels)
    ]


def main() -> None:
    args = parse_args()

    dem_sampled = load_dem_sampled(args.dem, args.stride)
    sampled_rows, sampled_cols = dem_sampled.shape

    blocked_sampled: Optional[np.ndarray] = None
    if args.blocked:
        blocked_sampled = load_blocked_sampled(args.blocked, args.dem, args.stride, (sampled_rows, sampled_cols))

    dem_grid, blocked_grid, source_valid_mask = build_fixed_dense_grid(
        dem_sampled,
        blocked_sampled,
        args.target_rows,
        args.target_cols,
    )
    rows, cols = dem_grid.shape

    elevation_grid = quantize_elevation_levels(dem_grid, args.elevation_levels)

    requested_source = parse_water_source(args.water_source, rows, cols)
    if requested_source == (-1, -1):
        source_r, source_c = choose_highest_cell(dem_grid, source_valid_mask)
    else:
        source_r, source_c = resolve_valid_source_cell(requested_source, source_valid_mask)

    if args.rain_center == "source":
        rain_center_r, rain_center_c = source_r, source_c
    else:
        rain_center_r, rain_center_c = rows // 2, cols // 2

    cells: Dict[str, dict] = {
        "default": {
            "delay": "inertial",
            "model": "flood",
            "state": {
                "water": 0.0,
                "elevation": 0,
                "blocked": 0,
                "cell_type": CELL_TYPE_NORMAL,
                "rain_amount": 0.0,
                "source_level": 0.0,
            },
        }
    }

    for r in range(rows):
        for c in range(cols):
            dem_val = dem_grid[r, c]

            is_source = (r, c) == (source_r, source_c)

            state = {
                "water": float(args.source_water) if is_source else 0.0,
                "elevation": int(elevation_grid[r, c]),
                "blocked": 0,
                "cell_type": CELL_TYPE_SOURCE if is_source else CELL_TYPE_NORMAL,
                "rain_amount": 0.0,
                "source_level": float(args.source_water) if is_source else 0.0,
            }

            if (
                args.rain_radius > 0
                and args.rain_amount > 0.0
                and in_rain_disk(r, c, rain_center_r, rain_center_c, args.rain_radius)
            ):
                state["rain_amount"] = float(args.rain_amount)
                if not is_source:
                    state["cell_type"] = CELL_TYPE_RAIN

            if blocked_grid is not None and blocked_grid[r, c] > 0:
                state["blocked"] = 1
                state["cell_type"] = CELL_TYPE_BLOCKED
                state["water"] = 0.0
                state["rain_amount"] = 0.0
                state["source_level"] = 0.0

            if state["blocked"]:
                cells[cell_id(r, c)] = {"state": state, "neighborhood": {}}
                continue

            neighborhood: Dict[str, float] = {}
            for nr, nc in moore_neighbor_coords(r, c, rows, cols):
                if blocked_grid is not None and blocked_grid[nr, nc] > 0:
                    continue
                neighborhood[cell_id(nr, nc)] = 1.0

            cells[cell_id(r, c)] = {
                "state": state,
                "neighborhood": neighborhood,
            }

    model_config = {"cells": cells}

    viewer_config = {
        "scenario": {
            "shape": [rows, cols],
            "origin": [0, 0],
            "wrapped": False,
        },
        "cells": {
            "default": {
                "delay": "inertial",
                "model": "flood",
                "state": {"water": 0, "elevation": 0, "blocked": 0},
                "neighborhood": [{"type": "moore", "range": 1}],
            },
            "water_source": {
                "state": {"water": int(args.source_water), "elevation": 0, "blocked": 0},
                "cell_map": [[source_r, source_c]],
            },
        },
        "viewer": [
            {
                "field": "water",
                "breaks": [-0.5, 0.5, 2.5, 4.5, 6.5, 8.5, 10.5],
                "colors": [
                    [235, 235, 235],
                    [205, 225, 255],
                    [160, 200, 255],
                    [110, 170, 245],
                    [60, 130, 225],
                    [20, 80, 180],
                ],
            },
            {
                "field": "elevation",
                "breaks": [-0.5] + [i + 0.5 for i in range(args.elevation_levels)],
                "colors": build_elevation_colors(args.elevation_levels),
            },
            {
                "field": "blocked",
                "breaks": [-0.5, 0.5, 1.5],
                "colors": [
                    [235, 235, 235],
                    [20, 20, 20],
                ],
            },
        ],
    }

    with open(args.model_out, "w", encoding="utf-8") as f:
        json.dump(model_config, f, indent=2)

    with open(args.viewer_out, "w", encoding="utf-8") as f:
        json.dump(viewer_config, f, indent=2)

    print(f"Generated model config: {args.model_out}")
    print(f"Generated viewer config: {args.viewer_out}")
    print(
        f"Grid size: sampled {sampled_rows}x{sampled_cols}, fixed output {rows}x{cols}; "
        f"elevation levels: 0..{args.elevation_levels - 1}, DEM range: {float(np.min(dem_grid)):.3f}..{float(np.max(dem_grid)):.3f}"
    )
    if args.rain_radius > 0 and args.rain_amount > 0.0:
        print(
            f"Rain enabled: center=({rain_center_r},{rain_center_c}), radius={args.rain_radius}, amount={args.rain_amount}"
        )


if __name__ == "__main__":
    main()
