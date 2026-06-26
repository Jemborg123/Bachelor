# DTU Campus Pedestrian Navigation

Bachelor project — comparative analysis of shortest-path algorithms for
pedestrian navigation on DTU Lyngby campus, with a working routing prototype.

**Authors:** Amalia Ahmed Salah Osman (s235280), Jonas Emborg (s235251)
**Advisors:** Inge Li Gørtz, Philip Bille

## Overview

The project builds a navigable graph of DTU Lyngby campus from public GeoServer
data, compares four shortest-path algorithms on it, and serves routes through a
web application. It has three parts:

1. **Graph construction** — turn raw geospatial layers into a clean, obstacle-aware
   walkable graph (cleaning, DBSCAN merging, obstacle-aware KNN).
2. **Algorithm analysis** — implement and compare Dijkstra, A*, bidirectional A*,
   and ALT (A* with landmarks).
3. **Application** — a Flask backend and React frontend that route in real time
   and track the user's live location.

## Requirements

- Python 3.10 (CPython)
- Node.js (for the React frontend)
- Python packages: `flask`, `flask-cors`, `pyproj`, `geopandas` (for data access)

Coordinates use the projected CRS **ETRS89 / DKTM3 (EPSG:4095)**; the application
converts to/from WGS84 (EPSG:4326) for display.

## Layout

```
Data/                geospatial loading, graph construction, data structures
  BuildGraph.py        graph generators (obstacle map, grid, comparison graphs)
  KDtree.py            KD-tree (range + k-NN search)
  clearDisjoint.py     largest-connected-component pruning
  routeToPath.py       stitch precise endpoints onto a graph route
  utils.py             AdjacencyList, Heap/MinHeap, Queue, helpers
  Obstacle_algebra/    polygon offset + segment/obstacle intersection
  Database_access/     GeoServer loading (loadFromDb.py)
Algorithms/          Dijkstra.py, AStar.py, bidirectionals.py, ALT.py
backend.py           Flask API (/path, /progress, /bounds, /search, /health)
frontend/            React app (App.js, searchField.js)   <!-- adjust path -->
```

## Building the graphs

Generate the four comparison graphs into `Data/Compare/`:

```python
from Data.BuildGraph import generate_comparison_graphs
generate_comparison_graphs(grid_tile=5)
```

To regenerate only the obstacle-aware grid:

```python
from Data.BuildGraph import gridMapObstacleAware
gridMapObstacleAware("Data/Compare/grid.json", tileSize=5, CELLSIZE=10)
```

Prune a graph to its largest connected component (also done in-memory by the
comparison script):

```python
from Data.BuildGraph import prune_to_largest_component
prune_to_largest_component("Data/in.json", "Data/in_pruned.json")
```

## Comparing graphs

```bash
python Data/compareGraphs.py --queries 200 --seed 0
```

Reports, per graph: vertices, edges, memory, connectivity rate, validity rate
(no edge crosses an obstacle), mean snap distance, and mean valid path length.
Prints LaTeX table rows for the report.

## Comparing algorithms

Runs Dijkstra, A*, bidirectional A*, and ALT on the same 100 query pairs drawn
from the largest connected component, recording time, vertices visited, edges
relaxed, and memory.

## Running the application

Backend:

```bash
python backend.py        # serves on port 5000 by default
```

Frontend:

```bash
cd frontend
npm install
npm start                # serves on port 3000
```

Set `REACT_APP_API_URL` to the backend address if not on localhost. The deployed
backend routes with **ALT**.

