
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
from Data.routeToPath import build_continuous_path
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

# ========== API ENDPOINTS ==========
@app.route('/path', methods=['POST'])
def get_path():
    """Get shortest path between two points"""
    try:
        data = request.json
        source_lat = data['source']['lat']
        source_lon = data['source']['lng']
        target_lat = data['target']['lat']
        target_lon = data['target']['lng']
        
        print(f"   Source: ({source_lat}, {source_lon})")
        print(f"   Target: ({target_lat}, {target_lon})")
        

        source_grid = lat_lon_to_grid(source_lat, source_lon)
        target_grid = lat_lon_to_grid(target_lat, target_lon)
        print(f"   Source grid: {source_grid}")
        print(f"   Target grid: {target_grid}")
 
        # Snap to nearest graph nodes
        source_node, sdist = closest_node(source_grid)
        target_node, tdist = closest_node(target_grid)
        print(f"   Source node: {source_node}  (snap {sdist:.1f} m)")
        print(f"   Target node: {target_node}  (snap {tdist:.1f} m)")

        
        if source_node is None or target_node is None:
            return jsonify({'error': 'Could not find nodes near clicked points'}), 400
        
        # Run A* algorithm
        import time
        h_adj = lambda p1, p2: adj_euclidean(p1,p2)
        h_alt = lambda p1,p2: landmark_h(p1,p2,Landmark_dist,len(Landmark_dist.get(p1)))
        a_graph = adjGraph(adj_list)
        
        start_time = time.time()
        # distance, path, stats = new_astar(a_graph, source_node, target_node,h_adj) #A star euclid
        distance, path, stats = new_astar(a_graph, source_node, target_node,h_alt) #A star landmarks

        
        
        elapsed_ms = (time.time() - start_time) * 1000
        print(f"   Path found: {len(path)} nodes, {distance:.1f}m, {elapsed_ms:.1f}ms")
        # Convert path back to lat/lon for display


        full_path, total_dist = build_continuous_path(
            source_grid, target_grid, path,
            polygons, spatial_index, CELL_SIZE, polygon_bboxes)

        print(f"   Path: {len(path)} graph nodes -> {len(full_path)} pts, "
              f"{total_dist:.1f} m (graph {distance:.1f} m), {elapsed_ms:.1f} ms")
        
        # path_latlon = [list(grid_to_lat_lon(node[0], node[1])) for node in path]
        path_latlon = [list(grid_to_lat_lon(x, y)) for x, y in full_path]

        return jsonify({
            'path': path_latlon,
            'distance': distance,
            'time_ms': elapsed_ms,
            'nodes_visited': stats,
            'algorithm': str(a_graph)
        })
        # return jsonify({
        #     'path': path_latlon,
        #     'distance': distance,
        #     'time_ms': elapsed_ms,
        #     'nodes_visited': stats['nodes_visited'],
        #     'edges_relaxed': stats['edges_relaxed'],
        #     'algorithm': stats.get('algorithm', 'A*')
        # })
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'ok', 'nodes': len(adj_list.keys())})

if __name__ == '__main__':
    print("\n🚀 Starting backend server...")
    print("📍 Backend running at: http://localhost:5000")
    print("💡 Make sure React is running on port 3000")
    print("\n📌 Test the API:")
    print("   curl http://localhost:5000/health")
    app.run(host='0.0.0.0', port=5000, debug=True)  # Use debug=True for now