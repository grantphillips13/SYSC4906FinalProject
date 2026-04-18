#!/usr/bin/env python3
"""
Convert GIS rasters into flood Cell-DEVS configs.

Outputs:
  - flood_simple_config.json            (simulation config)
  - flood_viewer_simple_config.json     (viewer config)

Usage example:
  python3 config/gis_to_flood_config.py \
    --dem /path/to/dem.tif \
    --blocked /path/to/blocked_mask.tif \
    --stride 20 \
    --water-source rc:10,10
"""

import argparse
import json
from typing import Dict, Tuple, Optional

import numpy as np
import rasterio
from rasterio.warp import reproject, Resampling


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Build flood configs from GIS rasters")
    p.add_argument("--dem", required=True, help="Path to DEM GeoTIFF")
    p.add_argument("--blocked", help="Optional blocked mask raster (1=blocked)")
    p.add_argument("--stride", type=int, default=20, help="Sampling step in pixels")
    p.add_argument(
        "--elevation-threshold",
        type=float,
        default=None,
        help="DEM threshold for elevation=1 (default: use DEM 75th percentile)",
    )
    p.add_argument(
        "--water-source",
        default="center",
        help="Water source as center or rc:<row,col> in sampled grid, e.g. rc:10,10",
    )
    p.add_argument("--source-water", type=int, default=10, help="Initial source water level")
    p.add_argument(
        "--model-out",
        default="flood_simple_config.json",
        help="Output simulation config path",
    )
    p.add_argument(
        "--viewer-out",
        default="flood_viewer_simple_config.json",
        help="Output viewer config path",
    )
    return p.parse_args()


def cell_id(r: int, c: int) -> str:
    return f"[{r},{c}]"


def moore_neighbors(r: int, c: int, rows: int, cols: int) -> Dict[str, float]:
    out: Dict[str, float] = {}
    for dr in (-1, 0, 1):
        for dc in (-1, 0, 1):
            if dr == 0 and dc == 0:
                continue
            nr, nc = r + dr, c + dc
            if 0 <= nr < rows and 0 <= nc < cols:
                out[cell_id(nr, nc)] = 1.0
    return out


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
    if s.startswith("rc:"):
        part = s[3:]
        r_txt, c_txt = part.split(",")
        r, c = int(r_txt), int(c_txt)
        if not (0 <= r < rows and 0 <= c < cols):
            raise ValueError("--water-source rc:<r,c> out of range")
        return r, c
    raise ValueError("--water-source must be 'center' or rc:<row,col>")


def main() -> None:
    args = parse_args()

    dem_sampled = load_dem_sampled(args.dem, args.stride)
    rows, cols = dem_sampled.shape

    valid_dem = dem_sampled[~np.isnan(dem_sampled)]
    if valid_dem.size == 0:
        raise RuntimeError("DEM has no valid cells after sampling")

    elev_threshold = (
        float(np.nanpercentile(dem_sampled, 75))
        if args.elevation_threshold is None
        else args.elevation_threshold
    )

    blocked_sampled: Optional[np.ndarray] = None
    if args.blocked:
        blocked_sampled = load_blocked_sampled(args.blocked, args.dem, args.stride, (rows, cols))

    source_r, source_c = parse_water_source(args.water_source, rows, cols)

    cells: Dict[str, dict] = {
        "default": {
            "delay": "inertial",
            "model": "flood",
            "state": {"water": 0, "elevation": 0, "blocked": 0},
        }
    }

    for r in range(rows):
        for c in range(cols):
            dem_val = dem_sampled[r, c]
            if np.isnan(dem_val):
                continue

            state = {
                "water": int(args.source_water) if (r, c) == (source_r, source_c) else 0,
                "elevation": 1 if dem_val >= elev_threshold else 0,
                "blocked": 0,
            }

            if blocked_sampled is not None:
                state["blocked"] = 1 if blocked_sampled[r, c] > 0 else 0
                if state["blocked"] == 1:
                    state["water"] = 0

            cells[cell_id(r, c)] = {
                "state": state,
                "neighborhood": moore_neighbors(r, c, rows, cols),
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
        "filter": {"port_name": [""]},
        "viewer": [
            {
                "field": "water",
                "breaks": [-1, 0, 2, 4, 6, 8, 10],
                "colors": [
                    [235, 235, 235],
                    [205, 225, 255],
                    [160, 200, 255],
                    [110, 170, 245],
                    [60, 130, 225],
                    [20, 80, 180],
                ],
            }
        ],
    }

    with open(args.model_out, "w", encoding="utf-8") as f:
        json.dump(model_config, f, indent=2)

    with open(args.viewer_out, "w", encoding="utf-8") as f:
        json.dump(viewer_config, f, indent=2)

    print(f"Generated model config: {args.model_out}")
    print(f"Generated viewer config: {args.viewer_out}")
    print(f"Grid size: {rows}x{cols}, elevation threshold: {elev_threshold:.3f}")


if __name__ == "__main__":
    main()
