
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from flask import Flask, request, jsonify
from flask_cors import CORS
import pickle
import math
import sys
import os
from pyproj import Transformer

app = Flask(__name__)
CORS(app)

# ========== CONFIGURE PATHS ==========
# Your Bachelor project root

# Path to your adjacency list file (try different options)
ADJACENCY_PATH = "../Data/ObbyMap32_pruned.json"


# Import your modules
from Data.utils import load_adjacency_list
from Algorithms.A_AStar import astar
from Algorithms.ALT import *
import Data.KDtree as KDtree
from Data.routeToPath import build_continuous_path, project_point_onto_path
import Data.Database_access.loadFromDb as loadFromDb
import Data.Obstacle_algebra.spatial_intersection as spatial_intersection

# ========== LOAD GRAPH ==========
print("📂 Loading adjacency list...")

adj_list = None
success = False


adj_list, success = load_adjacency_list(ADJACENCY_PATH)

print(f"✅ Graph loaded: {len(adj_list.keys())} nodes")

node_tree = KDtree.buildKDtree(list(adj_list.keys()))

print("✅ KD-tree ready")

landmark_data = loadPointsDataFromFile("../Data/ObbyMap32_pruned_graph_landmark_distances.json")

Landmark_dist = {}
for node, LandmarkDists in landmark_data.values():
    Landmark_dist[tuple(node)] = LandmarkDists


print("✅ Landmarks ready")


OBSTACLES_PATH = "../Data/obstacles.json"
CELL_SIZE = 10

def load_or_build_obstacles(path):
    if os.path.exists(path):
        print("📂 Loading cached obstacles...")
        return loadPointsDataFromFile(path)          # list of polygons (lists of [x, y])
    print("🌐 No cache found — fetching obstacles from geoserver...")
    raw = loadFromDb.remove_near_zero_polygon_outliers(
        loadFromDb.geodataframe_to_polygon_lists(loadFromDb.fetch_obstacle_gdfs()))
    # coerce to plain floats so json.dump can serialise (geopandas gives numpy floats)
    polygons = [[[float(pt[0]), float(pt[1])] for pt in poly] for poly in raw]
    savePointsDataToFile(polygons, path)             # cache it for next time
    return polygons

polygons = load_or_build_obstacles(OBSTACLES_PATH)
spatial_index = spatial_intersection.build_spatial_index(polygons, CELL_SIZE)
polygon_bboxes = spatial_intersection.precompute_bboxes(polygons)
print(f"✅ Obstacles ready: {len(polygons)} polygons")

SEARCH_LIBRARY_PATH = "../Data/Data/SearchLibrary.json"
search_library = loadPointsDataFromFile(SEARCH_LIBRARY_PATH)
print(f"✅ Search library loaded: {len(search_library.keys())} search keys")

LABELED_POINTS_PATH = "../Data/LabeledPoints.json"
labeled_points = loadPointsDataFromFile(LABELED_POINTS_PATH)
print(f"✅ Labeled points loaded: {len(labeled_points.keys())} locations")

# ========== COORDINATE CONVERSION ==========
_to_grid = Transformer.from_crs(4326, 4095, always_xy=True)
_to_wgs  = Transformer.from_crs(4095, 4326, always_xy=True)
 
def lat_lon_to_grid(lat, lon):
    x, y = _to_grid.transform(lon, lat)
    return (x, y)
 
def grid_to_lat_lon(x, y):
    lon, lat = _to_wgs.transform(x, y)
    return (lat, lon)


def closest_node(point):
    """Nearest graph node to `point`, plus its distance (grid units ≈ metres)."""
    heap = KDtree.KNN_KDtree(node_tree, point, 1)
    distance, coords = heap.extractMax()   # k=1 → the single nearest element
    return coords, distance

def _graph_latlon_bounds():
    """Lat/lon envelope of the graph — the area where routing is possible."""
    xs = [p[0] for p in adj_list.keys()]
    ys = [p[1] for p in adj_list.keys()]
    corners = [(min(xs), min(ys)), (min(xs), max(ys)),
               (max(xs), min(ys)), (max(xs), max(ys))]
    lls = [grid_to_lat_lon(x, y) for (x, y) in corners]
    lats = [lat for lat, lon in lls]
    lons = [lon for lat, lon in lls]
    return {'south': min(lats), 'west': min(lons),
            'north': max(lats), 'east': max(lons)}

_AREA_BOUNDS = _graph_latlon_bounds()   # computed once at startup

# ========== LIVE TRACKING STATE ==========
ROUTES = {}              # route_id -> route in grid coords, consumed by /progress
_next_route_id = 0
STRAY_THRESHOLD_M = 10   # metres off the route before we flag "off route"
REROUTE_THRESHOLD_M = 20 # metres off the route before we rebuild it from here
 
 
def compute_route(source_grid, target_grid):
    """A* + continuous path between two grid points, stored for live tracking.
 
    Shared by /path and the reroute branch of /progress so the route-building
    logic lives in exactly one place. Returns a dict, or None if no path exists.
    """
    import time
 
    source_node, sdist = closest_node(source_grid)
    target_node, tdist = closest_node(target_grid)
    print(f"   Source node: {source_node}  (snap {sdist:.1f} m)")
    print(f"   Target node: {target_node}  (snap {tdist:.1f} m)")
    if source_node is None or target_node is None:
        return None
 
    h_alt = lambda p1, p2: landmark_h(p1, p2, Landmark_dist, len(Landmark_dist.get(p1)))
    a_graph = adjGraph(adj_list)
 
    start_time = time.time()
    distance, path, stats = new_astar(a_graph, source_node, target_node, h_alt)  # A* landmarks
    elapsed_ms = (time.time() - start_time) * 1000
 
    full_path, total_dist = build_continuous_path(
        source_grid, target_grid, path,
        polygons, spatial_index, CELL_SIZE, polygon_bboxes)
 
    print(f"   Path: {len(path)} graph nodes -> {len(full_path)} pts, "
          f"{total_dist:.1f} m (graph {distance:.1f} m), {elapsed_ms:.1f} ms")
 
    path_latlon = [list(grid_to_lat_lon(x, y)) for x, y in full_path]
 
    global _next_route_id
    route_id = _next_route_id
    _next_route_id += 1
    ROUTES[route_id] = [(float(x), float(y)) for x, y in full_path]
    if len(ROUTES) > 50:                     # keep memory bounded
        for k in list(ROUTES.keys())[:-50]:
            ROUTES.pop(k, None)
 
    return {
        'route_id': route_id,
        'path_latlon': path_latlon,
        'distance': distance,
        'time_ms': elapsed_ms,
        'stats': stats,
        'algorithm': str(a_graph),
    }
 
 
# ========== API ENDPOINTS ==========
@app.route('/path', methods=['POST'])
def get_path():
    """Get shortest path between two points"""
    try:
        data = request.json
        source_grid = lat_lon_to_grid(data['source']['lat'], data['source']['lng'])
        target_grid = lat_lon_to_grid(data['target']['lat'], data['target']['lng'])
        print(f"   Source grid: {source_grid}")
        print(f"   Target grid: {target_grid}")
 
        result = compute_route(source_grid, target_grid)
        if result is None:
            return jsonify({'error': 'Could not find nodes near clicked points'}), 400
 
        return jsonify({
            'path': result['path_latlon'],
            'distance': result['distance'],
            'time_ms': result['time_ms'],
            'nodes_visited': result['stats'],
            'algorithm': result['algorithm'],
            'route_id': result['route_id'],
        })
 
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500
 
 
@app.route('/progress', methods=['POST'])
def progress():
    """Project the live position onto a stored route and split it into the part
    behind you (transparent) and ahead of you (visible). If the position strays
    past REROUTE_THRESHOLD_M, rebuild the route from here to the destination."""
    try:
        data = request.json
        route_id = data['route_id']
        pos = data['position']
 
        path_grid = ROUTES.get(route_id)
        if not path_grid or len(path_grid) < 2:
            return jsonify({'error': 'Route not found. Recompute the path.'}), 404
 
        p_grid = lat_lon_to_grid(pos['lat'], pos['lng'])
        cp, dist_m, seg_index, _t = project_point_onto_path(p_grid, path_grid)
 
        # Strayed too far -> rebuild the route from the current position to the
        # original destination (the last point of the stored route).
        if dist_m > REROUTE_THRESHOLD_M:
            new = compute_route(p_grid, path_grid[-1])
            if new is not None:
                # The new route starts at the marker, so nothing is "behind" yet.
                return jsonify({
                    'rerouted': True,
                    'route_id': new['route_id'],
                    'path': new['path_latlon'],
                    'distance_m': 0.0,
                    'off_route': False,
                    'traveled': [],
                    'remaining': new['path_latlon'],
                })
            # No path found from here -> fall through and just report off-route.
 
        traveled_grid = list(path_grid[:seg_index + 1]) + [cp]
        remaining_grid = [cp] + list(path_grid[seg_index + 1:])
        to_ll = lambda pts: [list(grid_to_lat_lon(x, y)) for (x, y) in pts]
 
        return jsonify({
            'rerouted': False,
            'closest': list(grid_to_lat_lon(cp[0], cp[1])),
            'distance_m': dist_m,
            'seg_index': seg_index,
            'off_route': dist_m > STRAY_THRESHOLD_M,
            'traveled': to_ll(traveled_grid),
            'remaining': to_ll(remaining_grid),
        })
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

    
@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'ok', 'nodes': len(adj_list.keys())})

@app.route('/bounds', methods=['GET'])
def bounds():
    return jsonify(_AREA_BOUNDS)

@app.route('/search', methods=['GET'])
def search_suggestions():
    query = request.args.get('q', '').strip().lower()
    if not query:
        return jsonify({'suggestions': []})

    suggestions = []
    for name in search_library.get(query, [])[:5]:      # direct hit, already an index
        pts = labeled_points.get(name)
        if pts:
            lat, lng = grid_to_lat_lon(pts[-1][0], pts[-1][1])
            suggestions.append({'name': name, 'lat': lat, 'lng': lng})
        else:
            suggestions.append({'name': name, 'lat': None, 'lng': None})
    return jsonify({'suggestions': suggestions})

if __name__ == '__main__':
    print("\n🚀 Starting backend server...")
    print("📍 Backend running at: http://localhost:5000")
    print("💡 Make sure React is running on port 3000")
    print("\n📌 Test the API:")
    print("   curl http://localhost:5000/health")
    app.run(host='0.0.0.0', port=5000, debug=True)  # Use debug=True for now