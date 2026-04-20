#!/usr/bin/env python3
"""
Generates an Asymmetric Cell-DEVS JSON config for the flood simulation.
Each cell is named "r_ROW_COL" and its Moore neighborhood is listed explicitly.
"""
import json, sys, os

ROWS            = 20
COLS            = 20
SIM_TIME        = 50
_DIR            = os.path.dirname(os.path.abspath(__file__))
MODEL_OUT_FILE  = os.path.join(_DIR, "flood_simple_config.json")
VIEWER_OUT_FILE = os.path.join(_DIR, "flood_viewer_simple_config.json")

# Source cell
SOURCE      = (10, 10)
SOURCE_WATER = 10

# Elevation ridge: column 0
RIDGE_COLS  = {0}
ELEVATION   = 1

# Elevated block to the right of source (col 13-14, rows 7-13) — for testing elevation barrier
ELEVATED_CELLS = {(r, c) for r in range(7, 14) for c in range(13, 15)}

# Wall segment: cells (row, col)
WALLS = {(9,7),(9,8),(9,9),(9,10),(9,11),(9,12)}

def cell_id(r, c):
    return f"({r},{c})"

def moore_neighbors(r, c):
    """Return list of (row, col) for all valid Moore neighbors."""
    neighbors = []
    for dr in [-1, 0, 1]:
        for dc in [-1, 0, 1]:
            if dr == 0 and dc == 0:
                continue
            nr, nc = r + dr, c + dc
            if 0 <= nr < ROWS and 0 <= nc < COLS:
                neighbors.append((nr, nc))
    return neighbors

cells = {}

# Default cell (used as template by Cadmium — overridden per cell below)
cells["default"] = {
    "delay": "inertial",
    "model": "flood",
    "state": {"water": 0, "elevation": 0, "blocked": 0}
}

# Define every cell with its explicit Moore neighborhood
for r in range(ROWS):
    for c in range(COLS):
        cid = cell_id(r, c)

        state = {"water": 0, "elevation": 0, "blocked": 0}

        if (r, c) == SOURCE:
            state["water"] = SOURCE_WATER
        if c in RIDGE_COLS or (r, c) in ELEVATED_CELLS:
            state["elevation"] = ELEVATION
        if (r, c) in WALLS:
            state["blocked"] = 1

        # Blocked cells have no neighborhood — they are isolated from flow
        if state["blocked"]:
            cells[cid] = {"state": state, "neighborhood": {}}
            continue

        # Non-blocked cells: only include non-blocked neighbors
        neighborhood = {}
        for (nr, nc) in moore_neighbors(r, c):
            if (nr, nc) not in WALLS:
                neighborhood[cell_id(nr, nc)] = 1.0

        cells[cid] = {
            "state": state,
            "neighborhood": neighborhood
        }

model_config = {
    "cells": cells
}

viewer_config = {
    "scenario": {
        "shape": [ROWS, COLS],
        "origin": [0, 0],
        "wrapped": False
    },
    "cells": {
        "default": {
            "delay": "inertial",
            "model": "flood",
            "state": {"water": 0, "elevation": 0, "blocked": 0},
            "neighborhood": [
                {"type": "moore", "range": 1}
            ]
        },
        "water_source": {
            "state": {"water": SOURCE_WATER, "elevation": 0, "blocked": 0},
            "cell_map": [[SOURCE[0], SOURCE[1]]]
        }
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
                [60,  130, 225],
                [20,  80,  180]
            ]
        },
        {
            "field": "elevation",
            "breaks": [-0.5, 0.5, 1.5],
            "colors": [
                [235, 235, 235],
                [160, 120, 60]
            ]
        },
        {
            "field": "blocked",
            "breaks": [-0.5, 0.5, 1.5],
            "colors": [
                [235, 235, 235],
                [20,  20,  20]
            ]
        }
    ]
}

with open(MODEL_OUT_FILE, "w") as f:
    json.dump(model_config, f, indent=2)

with open(VIEWER_OUT_FILE, "w") as f:
    json.dump(viewer_config, f, indent=2)

print(f"Generated {MODEL_OUT_FILE}  ({ROWS}x{COLS} grid, {ROWS*COLS} cells)")
print(f"Generated {VIEWER_OUT_FILE}")
