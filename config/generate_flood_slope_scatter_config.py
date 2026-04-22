#!/usr/bin/env python3
"""
Generates a slope-focused flood scenario with only a few scattered 1x2 blocks.
Source starts on high elevation to demonstrate downhill propagation.
"""
import json
import os

ROWS = 24
COLS = 24
_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_OUT_FILE = os.path.join(_DIR, "flood_slope_scatter_config.json")
VIEWER_OUT_FILE = os.path.join(_DIR, "flood_viewer_slope_scatter_config.json")

# Cell roles
CELL_TYPE_NORMAL = 0
CELL_TYPE_BLOCKED = 1
CELL_TYPE_SOURCE = 2
CELL_TYPE_RAIN = 3

# Source on the highest plateau
SOURCE = (6, 6)
SOURCE_WATER = 10.0
SOURCE_LEVEL = 10.0

# Optional rain off for this scenario
RAIN_CELLS = {}

# Scattered 1x2 blocks (kept away from source/slope core)
WALLS = {
    (16, 3), (16, 4),
    (20, 18), (20, 19),
    (8, 20), (8, 21)
}


def cell_id(r, c):
    return f"({r},{c})"


def moore_neighbors(r, c):
    neighbors = []
    for dr in [-1, 0, 1]:
        for dc in [-1, 0, 1]:
            if dr == 0 and dc == 0:
                continue
            nr, nc = r + dr, c + dc
            if 0 <= nr < ROWS and 0 <= nc < COLS:
                neighbors.append((nr, nc))
    return neighbors


def elevation_at(r, c):
    """
    4-level slope landscape:
      3 = high plateau (contains source)
      2 = upper slope
      1 = lower slope
      0 = basin/plain
    """
    if 4 <= r <= 8 and 4 <= c <= 8:
        return 3
    if 3 <= r <= 11 and 3 <= c <= 11:
        return 2
    if 2 <= r <= 14 and 2 <= c <= 14:
        return 1
    return 0


cells = {}

cells["default"] = {
    "delay": "inertial",
    "model": "flood",
    "state": {
        "water": 0.0,
        "elevation": 0,
        "blocked": 0,
        "cell_type": CELL_TYPE_NORMAL,
        "rain_amount": 0.0,
        "source_level": 0.0
    }
}

for r in range(ROWS):
    for c in range(COLS):
        cid = cell_id(r, c)

        state = {
            "water": 0.0,
            "elevation": elevation_at(r, c),
            "blocked": 0,
            "cell_type": CELL_TYPE_NORMAL,
            "rain_amount": 0.0,
            "source_level": 0.0
        }

        if (r, c) == SOURCE:
            state["water"] = SOURCE_WATER
            state["cell_type"] = CELL_TYPE_SOURCE
            state["source_level"] = SOURCE_LEVEL

        if (r, c) in WALLS:
            state["blocked"] = 1
            state["cell_type"] = CELL_TYPE_BLOCKED

        if (r, c) in RAIN_CELLS and not state["blocked"]:
            if state["cell_type"] != CELL_TYPE_SOURCE:
                state["cell_type"] = CELL_TYPE_RAIN
            state["rain_amount"] = float(RAIN_CELLS[(r, c)])

        if state["blocked"]:
            cells[cid] = {"state": state, "neighborhood": {}}
            continue

        neighborhood = {}
        for (nr, nc) in moore_neighbors(r, c):
            if (nr, nc) not in WALLS:
                neighborhood[cell_id(nr, nc)] = 1.0

        cells[cid] = {
            "state": state,
            "neighborhood": neighborhood
        }

model_config = {"cells": cells}

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
            "state": {"water": int(SOURCE_WATER), "elevation": 3, "blocked": 0},
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
                [60, 130, 225],
                [20, 80, 180]
            ]
        },
        {
            "field": "elevation",
            "breaks": [-0.5, 0.5, 1.5, 2.5, 3.5],
            "colors": [
                [235, 235, 235],
                [214, 188, 136],
                [176, 138, 80],
                [120, 86, 42]
            ]
        },
        {
            "field": "blocked",
            "breaks": [-0.5, 0.5, 1.5],
            "colors": [
                [235, 235, 235],
                [20, 20, 20]
            ]
        }
    ]
}

with open(MODEL_OUT_FILE, "w") as f:
    json.dump(model_config, f, indent=2)

with open(VIEWER_OUT_FILE, "w") as f:
    json.dump(viewer_config, f, indent=2)

print(f"Generated {MODEL_OUT_FILE}  ({ROWS}x{COLS} grid, {ROWS * COLS} cells)")
print(f"Generated {VIEWER_OUT_FILE}")
print(f"Scattered blocked cells: {len(WALLS)}")
