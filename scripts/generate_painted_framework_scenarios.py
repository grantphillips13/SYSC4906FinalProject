#!/usr/bin/env python3
import json
import os

ROWS, COLS = 28, 28
CELL_TYPE_NORMAL = 0
CELL_TYPE_BLOCKED = 1
CELL_TYPE_SOURCE = 2
CELL_TYPE_RAIN = 3

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(BASE_DIR)
OUT_MODEL = os.path.join(PROJECT_ROOT, "config", "painted", "model")
OUT_VIEWER = os.path.join(PROJECT_ROOT, "config", "painted", "viewer")
os.makedirs(OUT_MODEL, exist_ok=True)
os.makedirs(OUT_VIEWER, exist_ok=True)


def cell_id(r, c):
	return f"({r},{c})"


def neighbors(r, c):
	out = []
	for dr in (-1, 0, 1):
		for dc in (-1, 0, 1):
			if dr == 0 and dc == 0:
				continue
			nr, nc = r + dr, c + dc
			if 0 <= nr < ROWS and 0 <= nc < COLS:
				out.append((nr, nc))
	return out


def make_viewer(source, source_water, max_elev):
	elev_breaks = [-0.5] + [i + 0.5 for i in range(max_elev + 1)]
	base_colors = [
		[240, 228, 202],
		[214, 188, 136],
		[181, 147, 94],
		[142, 108, 64],
		[104, 76, 45],
		[72, 52, 30],
	]
	if max_elev + 1 <= len(base_colors):
		elev_colors = base_colors[: max_elev + 1]
	else:
		elev_colors = base_colors + [base_colors[-1]] * ((max_elev + 1) - len(base_colors))

	return {
		"scenario": {"shape": [ROWS, COLS], "origin": [0, 0], "wrapped": False},
		"cells": {
			"default": {
				"delay": "inertial",
				"model": "flood",
				"state": {"water": 0, "elevation": max_elev, "blocked": 0},
				"neighborhood": [{"type": "moore", "range": 1}],
			},
			"water_source": {
				"state": {"water": int(source_water), "elevation": 0, "blocked": 0},
				"cell_map": [[source[0], source[1]]],
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
			{"field": "elevation", "breaks": elev_breaks, "colors": elev_colors},
			{
				"field": "blocked",
				"breaks": [-0.5, 0.5, 1.5],
				"colors": [[235, 235, 235], [20, 20, 20]],
			},
		],
	}


def write_scenario(name, source, source_water, source_level, elev_fn, walls=None, rain=None, max_elev=5):
	walls = walls or set()
	rain = rain or {}
	cells = {
		"default": {
			"delay": "inertial",
			"model": "flood",
			"state": {
				"water": 0.0,
				"elevation": max_elev,
				"blocked": 0,
				"cell_type": 0,
				"rain_amount": 0.0,
				"source_level": 0.0,
			},
		}
	}

	for r in range(ROWS):
		for c in range(COLS):
			st = {
				"water": 0.0,
				"elevation": int(elev_fn(r, c)),
				"blocked": 0,
				"cell_type": CELL_TYPE_NORMAL,
				"rain_amount": 0.0,
				"source_level": 0.0,
			}
			if (r, c) == source:
				st["water"] = float(source_water)
				st["cell_type"] = CELL_TYPE_SOURCE
				st["source_level"] = float(source_level)

			if (r, c) in walls:
				st["blocked"] = 1
				st["cell_type"] = CELL_TYPE_BLOCKED
				st["water"] = 0.0
				st["source_level"] = 0.0

			if (r, c) in rain and not st["blocked"]:
				st["rain_amount"] = float(rain[(r, c)])
				if st["cell_type"] != CELL_TYPE_SOURCE:
					st["cell_type"] = CELL_TYPE_RAIN

			if st["blocked"]:
				cells[cell_id(r, c)] = {"state": st, "neighborhood": {}}
				continue

			nb = {}
			for nr, nc in neighbors(r, c):
				if (nr, nc) not in walls:
					nb[cell_id(nr, nc)] = 1.0
			cells[cell_id(r, c)] = {"state": st, "neighborhood": nb}

	model = {"cells": cells}
	viewer = make_viewer(source, source_water, max_elev)

	model_path = os.path.join(OUT_MODEL, f"{name}_config.json")
	viewer_name = name
	if viewer_name.startswith("flood_painted_"):
		viewer_name = viewer_name.replace("flood_painted_", "painted_", 1)
	viewer_path = os.path.join(OUT_VIEWER, f"flood_viewer_{viewer_name}_config.json")
	with open(model_path, "w", encoding="utf-8") as f:
		json.dump(model, f, indent=2)
	with open(viewer_path, "w", encoding="utf-8") as f:
		json.dump(viewer, f, indent=2)
	print("WROTE", model_path)
	print("WROTE", viewer_path)


def main():
	# Scenario 1: channel open
	ch2 = {(4, c) for c in range(4, 14)} | {(5, c) for c in range(5, 12)}
	ch1 = {(r, 13) for r in range(5, 19)} | {(r, 12) for r in range(7, 17)}
	ch0 = {(18, c) for c in range(14, 25)} | {(17, c) for c in range(16, 23)}

	def elev_channel(r, c):
		if 3 <= r <= 6 and 3 <= c <= 6:
			return 3
		if (r, c) in ch0:
			return 0
		if (r, c) in ch1:
			return 1
		if (r, c) in ch2:
			return 2
		return 4

	write_scenario("flood_painted_fw_channel_open", (4, 4), 10, 10, elev_channel, max_elev=4)

	# Scenario 2: channel with barrier (partial blockage, not full cutoff)
	# Keep only a small offset obstruction so water can still route around it.
	partial_barrier = {(11, 14), (12, 14)}
	write_scenario(
		"flood_painted_fw_channel_barrier",
		(4, 4),
		10,
		10,
		elev_channel,
		walls=partial_barrier,
		max_elev=4,
	)

	# Scenario 3: river bend with partial blockage (still passable)
	river = set()
	river |= {(6, c) for c in range(4, 17)}
	river |= {(7, c) for c in range(4, 16)}
	river |= {(r, 16) for r in range(7, 20)}
	river |= {(r, 15) for r in range(8, 19)}
	river |= {(19, c) for c in range(16, 25)}
	river |= {(18, c) for c in range(17, 24)}

	# Single-cell obstruction to demonstrate bypass around blockage.
	bend_partial_block = {(12, 16)}

	def elev_bend(r, c):
		if (r, c) in river:
			return 0
		for rr, cc in river:
			if abs(rr - r) <= 1 and abs(cc - c) <= 1:
				return 1
		return 4

	write_scenario(
		"flood_painted_fw_river_bend_blockage",
		(6, 4),
		10,
		10,
		elev_bend,
		walls=bend_partial_block,
		max_elev=4,
	)

	# Scenario 4: two big side-by-side pits with source in the middle corridor, closer to left pit
	left_pit = {(r, c) for r in range(6, 22) for c in range(3, 11)}
	right_pit = {(r, c) for r in range(6, 22) for c in range(17, 25)}
	center_berm = {(r, c) for r in range(4, 24) for c in range(12, 16)}

	def elev_basin(r, c):
		if (r, c) in left_pit or (r, c) in right_pit:
			return 1
		if (r, c) in center_berm:
			return 4
		# shoulders around pits
		for rr, cc in left_pit | right_pit:
			if abs(rr - r) <= 1 and abs(cc - c) <= 1:
				return 2
		return 3

	# In the middle corridor, biased toward left pit.
	write_scenario("flood_painted_fw_basin_pooling", (14, 12), 10, 10, elev_basin, max_elev=4)

	# Scenario 5 (replacement): rain-fed urban plaza with drainage lane
	# Terrain concept:
	# - center plaza bowl (low) where rain pools,
	# - a drainage lane to the right that lets water escape/flow,
	# - surrounding higher ground and a few building blocks.
	plaza = {(r, c) for r in range(9, 19) for c in range(8, 16)}
	drain_lane = {(r, c) for r in range(12, 16) for c in range(16, 27)}
	building_blocks = set()
	for r0, c0, h, w in [
		(6, 6, 2, 2), (7, 18, 2, 3), (19, 7, 2, 3), (18, 19, 2, 2),
	]:
		for rr in range(r0, min(ROWS, r0 + h)):
			for cc in range(c0, min(COLS, c0 + w)):
				building_blocks.add((rr, cc))

	def elev_rain_plaza(r, c):
		if (r, c) in plaza:
			return 1
		if (r, c) in drain_lane:
			return 0
		# shoulders around plaza/lane
		for rr, cc in plaza | drain_lane:
			if abs(rr - r) <= 1 and abs(cc - c) <= 1:
				return 2
		return 4

	rain_cells = {}
	# three rain clusters: upper-left plaza, center plaza, near lane entry
	for cr, cc, amt in [(11, 10, 0.7), (14, 12, 0.8), (13, 16, 0.6)]:
		for rr in range(cr - 1, cr + 2):
			for cc2 in range(cc - 1, cc + 2):
				if 0 <= rr < ROWS and 0 <= cc2 < COLS and (rr, cc2) not in building_blocks:
					rain_cells[(rr, cc2)] = max(rain_cells.get((rr, cc2), 0.0), amt)

	# keep nominal source at far corner with zero level so scenario behavior is rain-driven
	write_scenario(
		"flood_painted_fw_rain_plaza_drain",
		(0, 0),
		0,
		0,
		elev_rain_plaza,
		walls=building_blocks,
		rain=rain_cells,
		max_elev=4,
	)

	# Scenario 6: urban downhill (left -> right) with building barriers
	buildings = set()
	# scattered building blocks (2x2 and 3x2 footprints)
	for r0, c0, h, w in [
		(4, 6, 2, 2), (8, 10, 3, 2), (5, 16, 2, 3),
		(12, 7, 2, 2), (14, 13, 3, 2), (10, 20, 2, 2),
		(18, 5, 2, 3), (20, 11, 2, 2), (19, 18, 3, 2),
		(23, 8, 2, 2), (22, 15, 2, 3),
	]:
		for rr in range(r0, min(ROWS, r0 + h)):
			for cc in range(c0, min(COLS, c0 + w)):
				buildings.add((rr, cc))

	def elev_urban(r, c):
		# slow monotonic slope from left(high) to right(low): 4 -> 0
		return max(0, 4 - (c * 5 // COLS))

	# source on the left side so water traverses through urban obstacles
	write_scenario(
		"flood_painted_fw_urban_downhill",
		(13, 2),
		10,
		10,
		elev_urban,
		walls=buildings,
		max_elev=4,
	)


if __name__ == "__main__":
	main()
