#!/usr/bin/env python3
"""
Quick Tkinter grid painter for flood scenarios.

Features (MVP):
- Paint elevation values
- Toggle blocked cells
- Paint rain amount
- Set one source cell
- Export model + viewer JSON files compatible with current flood model
"""

import json
import os
import tkinter as tk
from tkinter import filedialog, messagebox

CELL_TYPE_NORMAL = 0
CELL_TYPE_BLOCKED = 1
CELL_TYPE_SOURCE = 2
CELL_TYPE_RAIN = 3


class ScenarioPainterApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Flood Grid Painter (Quick MVP)")

        self.rows = 20
        self.cols = 20
        self.cell_px = 24

        self.elevation = [[0 for _ in range(self.cols)] for _ in range(self.rows)]
        self.blocked = [[0 for _ in range(self.cols)] for _ in range(self.rows)]
        self.rain = [[0.0 for _ in range(self.cols)] for _ in range(self.rows)]

        self.source = (10, 10)
        self.source_water = 10.0
        self.source_level = 10.0

        self.tool_var = tk.StringVar(value="elevation")
        self.elevation_value = tk.IntVar(value=1)
        self.rain_value = tk.DoubleVar(value=0.5)

        self._build_ui()
        self._draw_grid()

    def _build_ui(self):
        controls = tk.Frame(self.root)
        controls.pack(side=tk.LEFT, fill=tk.Y, padx=8, pady=8)

        tk.Label(controls, text="Tool").pack(anchor="w")
        for t in ["elevation", "blocked", "rain", "source", "erase"]:
            tk.Radiobutton(controls, text=t, variable=self.tool_var, value=t).pack(anchor="w")

        tk.Label(controls, text="Elevation value").pack(anchor="w", pady=(10, 0))
        tk.Spinbox(controls, from_=0, to=9, textvariable=self.elevation_value, width=6).pack(anchor="w")

        tk.Label(controls, text="Rain amount").pack(anchor="w", pady=(10, 0))
        tk.Spinbox(
            controls,
            from_=0.0,
            to=5.0,
            increment=0.1,
            textvariable=self.rain_value,
            width=6,
        ).pack(anchor="w")

        tk.Label(controls, text="Source water").pack(anchor="w", pady=(10, 0))
        self.source_water_var = tk.DoubleVar(value=self.source_water)
        tk.Spinbox(
            controls,
            from_=0.0,
            to=30.0,
            increment=0.5,
            textvariable=self.source_water_var,
            width=6,
        ).pack(anchor="w")

        tk.Label(controls, text="Source level").pack(anchor="w", pady=(10, 0))
        self.source_level_var = tk.DoubleVar(value=self.source_level)
        tk.Spinbox(
            controls,
            from_=0.0,
            to=30.0,
            increment=0.5,
            textvariable=self.source_level_var,
            width=6,
        ).pack(anchor="w")

        tk.Button(controls, text="Clear", command=self.clear_grid).pack(anchor="w", pady=(12, 0))
        tk.Button(controls, text="Export JSON", command=self.export_json).pack(anchor="w", pady=(6, 0))

        self.canvas = tk.Canvas(
            self.root,
            width=self.cols * self.cell_px,
            height=self.rows * self.cell_px,
            bg="white",
            highlightthickness=0,
        )
        self.canvas.pack(side=tk.RIGHT, padx=8, pady=8)
        self.canvas.bind("<Button-1>", self.on_paint)
        self.canvas.bind("<B1-Motion>", self.on_paint)

    def clear_grid(self):
        for r in range(self.rows):
            for c in range(self.cols):
                self.elevation[r][c] = 0
                self.blocked[r][c] = 0
                self.rain[r][c] = 0.0
        self.source = (self.rows // 2, self.cols // 2)
        self._draw_grid()

    def on_paint(self, event):
        c = event.x // self.cell_px
        r = event.y // self.cell_px
        if r < 0 or r >= self.rows or c < 0 or c >= self.cols:
            return

        tool = self.tool_var.get()

        if tool == "elevation":
            self.elevation[r][c] = int(self.elevation_value.get())
            self.blocked[r][c] = 0
        elif tool == "blocked":
            self.blocked[r][c] = 1
            self.rain[r][c] = 0.0
        elif tool == "rain":
            self.rain[r][c] = float(self.rain_value.get())
            self.blocked[r][c] = 0
        elif tool == "source":
            self.source = (r, c)
            self.blocked[r][c] = 0
        elif tool == "erase":
            self.elevation[r][c] = 0
            self.blocked[r][c] = 0
            self.rain[r][c] = 0.0

        self._draw_grid()

    def _cell_color(self, r, c):
        if self.blocked[r][c]:
            return "#111111"
        e = self.elevation[r][c]
        if e <= 0:
            base = (235, 235, 235)
        else:
            shade = max(70, 210 - 22 * e)
            base = (shade, max(60, shade - 28), max(40, shade - 55))

        if self.rain[r][c] > 0:
            base = (150, 190, 255)

        return "#%02x%02x%02x" % base

    def _draw_grid(self):
        self.canvas.delete("all")
        for r in range(self.rows):
            for c in range(self.cols):
                x0 = c * self.cell_px
                y0 = r * self.cell_px
                x1 = x0 + self.cell_px
                y1 = y0 + self.cell_px
                color = self._cell_color(r, c)
                self.canvas.create_rectangle(x0, y0, x1, y1, fill=color, outline="#cccccc")

        sr, sc = self.source
        x0 = sc * self.cell_px
        y0 = sr * self.cell_px
        x1 = x0 + self.cell_px
        y1 = y0 + self.cell_px
        self.canvas.create_rectangle(x0, y0, x1, y1, outline="#0066ff", width=3)

    def _cell_id(self, r, c):
        return f"({r},{c})"

    def _neighbors(self, r, c):
        for dr in (-1, 0, 1):
            for dc in (-1, 0, 1):
                if dr == 0 and dc == 0:
                    continue
                nr, nc = r + dr, c + dc
                if 0 <= nr < self.rows and 0 <= nc < self.cols:
                    yield nr, nc

    def export_json(self):
        self.source_water = float(self.source_water_var.get())
        self.source_level = float(self.source_level_var.get())

        out_model = filedialog.asksaveasfilename(
            title="Save model JSON",
            defaultextension=".json",
            initialfile="flood_painted_config.json",
            filetypes=[("JSON files", "*.json")],
        )
        if not out_model:
            return

        model_cells = {
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

        for r in range(self.rows):
            for c in range(self.cols):
                cid = self._cell_id(r, c)
                is_blocked = self.blocked[r][c] == 1
                is_source = (r, c) == self.source
                rain_amount = float(self.rain[r][c])

                state = {
                    "water": 0.0,
                    "elevation": int(self.elevation[r][c]),
                    "blocked": 1 if is_blocked else 0,
                    "cell_type": CELL_TYPE_BLOCKED if is_blocked else CELL_TYPE_NORMAL,
                    "rain_amount": 0.0,
                    "source_level": 0.0,
                }

                if is_source and not is_blocked:
                    state["water"] = self.source_water
                    state["cell_type"] = CELL_TYPE_SOURCE
                    state["source_level"] = self.source_level

                if rain_amount > 0.0 and not is_blocked and not is_source:
                    state["cell_type"] = CELL_TYPE_RAIN
                    state["rain_amount"] = rain_amount

                if is_blocked:
                    model_cells[cid] = {"state": state, "neighborhood": {}}
                else:
                    nb = {}
                    for nr, nc in self._neighbors(r, c):
                        if self.blocked[nr][nc] == 0:
                            nb[self._cell_id(nr, nc)] = 1.0
                    model_cells[cid] = {"state": state, "neighborhood": nb}

        model_config = {"cells": model_cells}

        viewer_config = {
            "scenario": {
                "shape": [self.rows, self.cols],
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
                    "state": {
                        "water": int(round(self.source_water)),
                        "elevation": int(self.elevation[self.source[0]][self.source[1]]),
                        "blocked": 0,
                    },
                    "cell_map": [[self.source[0], self.source[1]]],
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
                    "breaks": [-0.5, 0.5, 1.5, 2.5, 3.5, 4.5, 5.5],
                    "colors": [
                        [235, 235, 235],
                        [214, 188, 136],
                        [181, 147, 94],
                        [142, 108, 64],
                        [104, 76, 45],
                        [72, 52, 30],
                    ],
                },
                {
                    "field": "blocked",
                    "breaks": [-0.5, 0.5, 1.5],
                    "colors": [[235, 235, 235], [20, 20, 20]],
                },
            ],
        }

        out_viewer = os.path.splitext(out_model)[0].replace("_config", "_viewer_config") + ".json"

        with open(out_model, "w", encoding="utf-8") as f:
            json.dump(model_config, f, indent=2)

        with open(out_viewer, "w", encoding="utf-8") as f:
            json.dump(viewer_config, f, indent=2)

        messagebox.showinfo(
            "Export complete",
            f"Saved model:\n{out_model}\n\nSaved viewer:\n{out_viewer}",
        )


def main():
    root = tk.Tk()
    app = ScenarioPainterApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
