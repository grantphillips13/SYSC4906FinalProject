#!/usr/bin/env python3
"""
Generates a channel-focused flood scenario.
Goal: visibly route water downhill through a carved channel faster than surrounding terrain.
"""
import json
import os

ROWS = 28
COLS = 28
_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_OUT_FILE = os.path.join(_DIR, "flood_channel_config.json")
VIEWER_OUT_FILE = os.path.join(_DIR, "flood_viewer_channel_config.json")

CELL_TYPE_NORMAL = 0
CELL_TYPE_BLOCKED = 1
CELL_TYPE_SOURCE = 2
CELL_TYPE_RAIN = 3

SOURCE = (4, 4)
SOURCE_WATER = 10.0
SOURCE_LEVEL = 10.0

# Keep rain off in this demo
RAIN_CELLS = {}

# A few scattered 1x2 blocks away from the main channel
WALLS = {
    (22, 4), (22, 5),
    (9, 24), (9, 25),
    (23, 22), (23, 23)
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


# Build a descending channel path from source area to far basin:
# segment A: row 4, col 4..13  -> elev 2
# segment B: col 13, row 5..18 -> elev 1
# segment C: row 18, col 14..24 -> elev 0
CHANNEL_E2 = {(4, c) for c in range(4, 14)}
CHANNEL_E1 = {(r, 13) for r in range(5, 19)}
CHANNEL_E0 = {(18, c) for c in range(14, 25)}

# Slightly widen the channel by one-cell shoulders
CHANNEL_E2 |= {(5, c) for c in range(5, 12)}
CHANNEL_E1 |= {(r, 12) for r in range(7, 17)}
CHANNEL_E0 |= {(17, c) for c in range(16, 23)}


def elevation_at(r, c):
    """
    Multi-level terrain:
      4 = high berm / plateau (default)
      3 = source pocket
      2,1,0 = descending channel to basin
    """
    # Source pocket (still high, but lower than surrounding berm)
    if 3 <= r <= 6 and 3 <= c <= 6:
        return 3

    if (r, c) in CHANNEL_E0:
        return 0
    if (r, c) in CHANNEL_E1:
        return 1
    if (r, c) in CHANNEL_E2:
        return 2

    # Everywhere else high so water prefers/downselects to channel
    return 4


cells = {}

cells["default"] = {
    "delay": "inertial",
    "model": "flood",
    "state": {
        "water": 0.0,
        "elevation": 4,
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
            "state": {"water": 0, "elevation": 4, "blocked": 0},
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
            "breaks": [-0.5, 0.5, 1.5, 2.5, 3.5, 4.5],
            "colors": [
                [240, 228, 202],
                [214, 188, 136],
                [181, 147, 94],
                [142, 108, 64],
                [104, 76, 45]
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
print(f"Channel cells (e2/e1/e0): {len(CHANNEL_E2)}/{len(CHANNEL_E1)}/{len(CHANNEL_E0)}")
print(f"Scattered blocked cells: {len(WALLS)}")
