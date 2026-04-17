#!/usr/bin/env python3
"""
Generates an Asymmetric Cell-DEVS JSON config for the flood simulation.
Each cell is named "r_ROW_COL" and its Moore neighborhood is listed explicitly.
"""
import json, sys

ROWS            = 20
COLS            = 20
SIM_TIME        = 50
MODEL_OUT_FILE  = "flood_simple_config.json"
VIEWER_OUT_FILE = "flood_viewer_simple_config.json"

# Source cell
SOURCE      = (10, 10)
SOURCE_WATER = 10

# Elevation ridge: column 0
RIDGE_COLS  = {0}
ELEVATION   = 1

# Wall segment: cells (row, col)
WALLS = {(9,7),(9,8),(9,9),(9,10),(9,11),(9,12)}

def cell_id(r, c):
    return f"[{r},{c}]"

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

        # Build neighborhood: neighbor_id -> vicinity (1.0 for all)
        neighborhood = {}
        for (nr, nc) in moore_neighbors(r, c):
            neighborhood[cell_id(nr, nc)] = 1.0

        state = {"water": 0, "elevation": 0, "blocked": 0}

        if (r, c) == SOURCE:
            state["water"] = SOURCE_WATER
        if c in RIDGE_COLS:
            state["elevation"] = ELEVATION
        if (r, c) in WALLS:
            state["blocked"] = 1

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
                [20, 80, 180]
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
