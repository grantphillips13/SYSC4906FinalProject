# Flood Simulation — Cell-DEVS Cadmium Model

---

## Overview

This project simulates water flood dynamics across terrain using the **Cell-DEVS formalism** and the **Cadmium v2** framework.

Cells are arranged on a fixed **28×28 grid**, each representing a spatial location with terrain elevation. Water propagates from high-elevation cells to adjacent lower/equal-elevation cells. The model supports both **GIS-based DEMs** (real geographic elevation data) and **synthetic painted scenarios** for controlled testing.

Key features:
- Asymmetric cell neighborhoods (8-connected Moore)
- Elevation-constrained water flow (no uphill propagation)
- Optional rain injection and persistent water sources
- 11 discrete elevation levels (0–10)
---

## File Organization

```
SYSC4906FinalProject/
├── main/
│   ├── main.cpp                             # Simulation entry point
│   └── include/
│       ├── flood_cell.hpp                   # Cell local transition logic
│       └── flood_state.hpp                  # Cell state definition
├── config/
│   ├── gis/
│   │   ├── model/                           # GIS model configs (5 scenarios)
│   │   └── viewer/                          # GIS viewer configs
│   └── painted/
│       ├── model/                           # Synthetic model configs (6 scenarios)
│       └── viewer/                          # Synthetic viewer configs
├── logs/
│   ├── gis/                                 # GIS scenario output logs
│   └── non_gis/                             # Painted scenario output logs
├── scripts/
│   ├── gis_to_flood_config.py               # Generate configs from DEM rasters
│   ├── generate_painted_framework_scenarios.py  # Generate synthetic scenarios
│   ├── generate_flood_config.py             # Legacy config generator
│   └── *.py                                 # Other utility scripts
├── data/
│   ├── AlgonquinPark.tif                    # DEM GeoTIFF files
│   ├── Kenora.tif
│   ├── Muskoka.tif
│   ├── SaultSteMarie.tif
│   └── dem.tif
├── bin/
│   └── flood_sim                            # Compiled executable
├── build/                                   # Generated CMake build artifacts
├── CMakeLists.txt                           # Top-level CMake config
├── build.sh                                 # Build script
└── README.md
```

---

## Prerequisites

- **C++17** compatible compiler (e.g., `g++`)
- **CMake** 3.16 or later
- **Cadmium v2** (header-only)

Cadmium must be available at either:
- `../cadmium_v2/` relative to this project, or
- the `CADMIUM` environment variable pointing to Cadmium `include/`

Example:

```bash
export CADMIUM=/path/to/cadmium_v2/include
```

**Optional Python dependencies** (for scenario generation):
- `rasterio` (GIS raster I/O)
- `numpy` (numerical operations)
- `nlohmann/json` (via C++ headers)

Install Python dependencies:

```bash
pip install rasterio numpy
```

---

## Compilation Instructions

Build with the provided script:

```bash
source build_sim.sh
```

This script:
1. Verifies the Cadmium include path
2. Recreates `build/`
3. Runs `cmake ..`
4. Runs `make`
5. Outputs executable to `bin/flood_sim`

Manual build alternative:

```bash
mkdir -p build && cd build
cmake ..
make
cd ..
```

---

## Running Simulations

Run a single scenario with optional simulation time (default: 500 steps):

```bash
./bin/flood_sim config/gis/model/flood_gis_Algonquin_base_config.json [sim_time]
```

Run a painted scenario:

```bash
./bin/flood_sim config/painted/model/flood_painted_fw_channel_open_config.json 500
```

Each run produces `flood_log.csv` in the working directory.

---

## Scenario Summary

### GIS-Based Scenarios (Real Elevation Data)

Generated from Digital Elevation Model (DEM) GeoTIFF files. Terrain features real geographic topography with highest-elevation source placement and optional rain injection.

| Config File | DEM Source | Rain | Description |
|---|---|---|---|
| `flood_gis_Algonquin_base_config.json` | AlgonquinPark.tif | None | Baseline flow from peak elevation |
| `flood_gis_Kenora_base_config.json` | Kenora.tif | None | Baseline flow from peak elevation |
| `flood_gis_Muskoka_rain_config.json` | Muskoka.tif | Disk (r=4, amt=0.6) | Rain-driven landscape pooling |
| `flood_gis_Sault_burst_config.json` | SaultSteMarie.tif | Intense (r=2, amt=2.0) | High-intensity rain burst |
| `flood_gis_dem_multispot_rain_config.json` | dem.tif | 3 clusters (no source) | Multi-center rain without injection |

### Painted (Synthetic) Scenarios

Hand-crafted elevation functions for controlled testing of specific flood behaviors.

| Config File | Terrain Type | Special Features | Description |
|---|---|---|---|
| `flood_painted_fw_channel_open_config.json` | Channel network | None | Unobstructed water flow baseline |
| `flood_painted_fw_channel_barrier_config.json` | Channel network | 2-cell partial blockage | Demonstrates barrier resistance & bypass |
| `flood_painted_fw_river_bend_blockage_config.json` | River network | 1-cell obstruction | Water diverts around single obstruction |
| `flood_painted_fw_basin_pooling_config.json` | Two pits | Center source (14,12) | Validates multi-pool filling priority |
| `flood_painted_fw_urban_downhill_config.json` | Left-to-right slope | 11 building blocks (~56 cells) | Urban environment water routing |
| `flood_painted_fw_rain_plaza_drain_config.json` | Plaza + drainage lane | 27 rain cells, 4 buildings | Rain accumulation & drainage dynamics |

---

## Cell State Variables

Each cell maintains 6 state fields:

| Variable | Type | Range | Description |
|---|---|---|---|
| `water` | double | [0, ∞) | Current water level (internal precision; clamped [0,10] for display) |
| `elevation` | int | [0, 10] | Terrain height (11 discrete levels) |
| `blocked` | int | {0, 1} | Obstacle indicator (0=open, 1=wall/house) |
| `cell_type` | int | {0, 1, 2, 3} | 0=normal, 1=blocked, 2=source/pond, 3=rain |
| `rain_amount` | double | [0, ∞) | Water added per step if `cell_type==3` |
| `source_level` | double | [0, ∞) | Persistent minimum water level if `cell_type==2` |

---

## Water Propagation Rules

1. **No uphill flow**: Water only spreads to neighbors with `elevation ≥ current_elevation`
2. **Symmetric spread**: Water diffuses equally to valid neighbors
3. **Source maintenance**: Source cells retain `source_level` water each step
4. **Rain injection**: Rain cells receive `rain_amount` per step
5. **Blocked cells**: Do not propagate or receive water


---

## Configuration Generation

### From GIS DEMs

Generate a config from a GeoTIFF DEM with rain:

```bash
python3 scripts/gis_to_flood_config.py \
  --dem data/Muskoka.tif \
  --stride 50 \
  --target-rows 28 --target-cols 28 \
  --elevation-levels 11 \
  --water-source highest \
  --source-water 10 \
  --rain-radius 4 \
  --rain-amount 0.6 \
  --rain-center source \
  --model-out config/gis/model/flood_gis_Muskoka_rain_config.json \
  --viewer-out config/gis/viewer/flood_viewer_gis_Muskoka_rain_config.json
```

Key options:
- `--stride`: Sampling step in pixels (50 = 50-pixel stride over DEM)
- `--elevation-levels`: Number of discrete elevation bins (default: 11 → levels 0–10)
- `--water-source highest|center|rc:r,c`: Source placement strategy
- `--rain-radius`, `--rain-amount`: Rain disk parameters
- `--target-rows`, `--target-cols`: Fixed output grid size (default: 28×28)

### Synthetic Scenarios

Regenerate all painted scenarios:

```bash
python3 scripts/generate_painted_framework_scenarios.py
```

This writes all 6 scenarios to:
- `config/painted/model/*.json` (simulation configs)
- `config/painted/viewer/*.json` (viewer configs)

---

## Visualization

Use the [Cell-DEVS Web Viewer](https://devssim.carleton.ca/cell-devs-viewer/):

1. Load a model config file (e.g., `config/gis/model/flood_gis_Algonquin_base_config.json`)
2. Load the corresponding viewer config (e.g., `config/gis/viewer/flood_viewer_gis_Algonquin_base_config.json`)
3. Load the generated `flood_log.csv`
4. Step/animate to observe water propagation

### Viewer Color Schemes

**Water level** (0–10 discrete):

| Level | Color | RGB |
|---|---|---|
| 0 | Light gray | (235, 235, 235) |
| 1–2 | Light blue | (205, 225, 255) |
| 3–4 | Sky blue | (160, 200, 255) |
| 5–6 | Azure | (110, 170, 245) |
| 7–8 | Cornflower | (60, 130, 225) |
| 9–10 | Deep blue | (20, 80, 180) |

**Elevation** (0–10 discrete):

| Level | Color | Gradient |
|---|---|---|
| 0 | Light tan | (235, 235, 235) |
| 10 | Dark brown | (72, 52, 30) |
| 1–9 | Linear blend | Tan → Brown |

**Blocked cells**:

| State | Color |
|---|---|
| Open (0) | Light gray (235, 235, 235) |
| Blocked (1) | Black (20, 20, 20) |

---

## Log Format

Logs are semicolon-delimited CSV with format:

```
<time>;<cell_id>;<water>,<elevation>,<blocked>
```

Example:

```
0;(0,0);0,5,0
0;(0,1);0,5,0
1;(0,0);0.5,5,0
1;(1,5);1.2,4,0
```

Parse with:

```bash
grep "^[0-9]" flood_log.csv | awk -F ';' '{print $1, $2, $3}'
```

---

## Architecture Notes

- **Asymmetric Cell-DEVS**: Each cell computes transition based on its current state and all neighbors' states (no explicit message passing)
- **Inertial Delays**: Output delay of 1.0 time unit per cell transition
- **Discrete Elevation Quantization**: Continuous DEM elevations mapped to 11 levels via linear scaling and rounding
- **No Flow Capacity**: Water can accumulate indefinitely (display clamping is output-only; internal model has no overflow logic)

---

## Troubleshooting

### Build fails with "Could not find coupled.hpp"

Verify Cadmium path:

```bash
echo $CADMIUM
ls $CADMIUM/cadmium/modeling/celldevs/grid/coupled.hpp
```

If missing, set environment variable:

```bash
export CADMIUM=/path/to/cadmium_v2/include
bash build.sh
```

### Simulation produces empty log

- Verify config file paths are correct
- Check that model config file contains valid cell definitions
- Ensure `flood_sim` binary is up to date: `bash build.sh`

### Python script errors (GIS generation)

Install rasterio and numpy:

```bash
pip install rasterio numpy
```

If GDAL/rasterio fails to install, pre-built wheels may be available via conda:

```bash
conda install rasterio
```

---

## Project Context

This simulation was developed for **SYSC4906: Final Project** to model water flooding dynamics across real geographic terrain (GIS integration) and controlled synthetic environments for behavioral validation.

The 10-scenario framework combines:
- **5 GIS scenarios** (real DEM topography)
- **5 painted scenarios** (synthetic controlled tests)

All scenarios run for 300–500 simulation steps to capture meaningful flooding patterns and reach quasi-steady behavior.
