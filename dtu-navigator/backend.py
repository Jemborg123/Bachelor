from flask import Flask, request, jsonify
from flask_cors import CORS
import pickle
import math
import sys
import os

app = Flask(__name__)
CORS(app)

# ========== CONFIGURE PATHS ==========
# Your Bachelor project root
PROJECT_ROOT = r'C:\Users\amola\OneDrive\Dokumenter\GitHub\Bachelor'
sys.path.append(PROJECT_ROOT)

# Path to your adjacency list file (try different options)
ADJACENCY_PATH_CANDIDATES = [
    os.path.join(PROJECT_ROOT, "Data/Data/Adjacency_list_ObstacleAwareGraph.json"),
    os.path.join(PROJECT_ROOT, "Data/Adjacency_list_ObstacleAwareGraph.json"),
    "Adjacency_list_ObstacleAwareGraph.json",  # If copied to current folder
]

# Import your modules
from Data.utils import load_adjacency_list
from Algorithms.A_AStar import astar

# ========== LOAD GRAPH ==========
print("📂 Loading adjacency list...")

adj_list = None
success = False

for path in ADJACENCY_PATH_CANDIDATES:
    print(f"   Trying: {path}")
    if os.path.exists(path):
        print(f"   ✅ File found!")
        adj_list, success = load_adjacency_list(path)
        if success:
            print(f"   ✅ Loaded successfully!")
            break
    else:
        print(f"   ❌ File not found")

if not success or adj_list is None:
    print("❌ Failed to load graph from all paths!")
    print("   Make sure the adjacency list file exists.")
    exit(1)

print(f"✅ Graph loaded: {len(adj_list.keys())} nodes")

# ========== COORDINATE CONVERSION ==========
def lat_lon_to_utm(lat, lon):
    """
    Convert lat/lon to approximate UTM coordinates (EPSG:25832)
    This is approximate - for production, use pyproj
    """
    # Rough conversion for DTU area (latitude ~55.78)
    # 1 degree lat ≈ 111,000 m
    # 1 degree lon ≈ 111,000 * cos(lat) m
    
    # Reference point: DTU (55.7858, 12.5215) should map to ~(648000, 1184000)
    # Your graph coordinates are around this area
    
    # Simple offset approximation
    x = lon * 111320 * math.cos(math.radians(lat))
    y = lat * 110574
    
    # Adjust to match DTU's coordinate system
    # You may need to calibrate these values
    x = x + 648000 - (12.5215 * 111320 * math.cos(math.radians(55.7858)))
    y = y + 1184000 - (55.7858 * 110574)
    
    return (x, y)

def utm_to_lat_lon(x, y):
    """Convert UTM to approximate lat/lon"""
    # Reverse of above
    lat = (y - 1184000) / 110574 + 55.7858
    lon = (x - 648000) / (111320 * math.cos(math.radians(55.7858))) + 12.5215
    return (lat, lon)

def find_closest_node(adj_list, x, y):
    """Find closest node in graph to given coordinates"""
    min_dist = float('inf')
    closest = None
    for node in adj_list.keys():
        dist = (node[0] - x)**2 + (node[1] - y)**2
        if dist < min_dist:
            min_dist = dist
            closest = node
    return closest

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
        
        # Convert to graph coordinates
        source_utm = lat_lon_to_utm(source_lat, source_lon)
        target_utm = lat_lon_to_utm(target_lat, target_lon)
        
        print(f"   Source UTM: {source_utm}")
        print(f"   Target UTM: {target_utm}")
        
        # Find closest nodes in graph
        source_node = find_closest_node(adj_list, source_utm[0], source_utm[1])
        target_node = find_closest_node(adj_list, target_utm[0], target_utm[1])
        
        print(f"   Source node: {source_node}")
        print(f"   Target node: {target_node}")
        
        if source_node is None or target_node is None:
            return jsonify({'error': 'Could not find nodes near clicked points'}), 400
        
        # Run A* algorithm
        import time
        start_time = time.time()
        path, distance, stats = astar(adj_list, source_node, target_node)
        elapsed_ms = (time.time() - start_time) * 1000
        
        print(f"   Path found: {len(path)} nodes, {distance:.1f}m, {elapsed_ms:.1f}ms")
        
        # Convert path back to lat/lon for display
        path_latlon = []
        for node in path:
            lat, lon = utm_to_lat_lon(node[0], node[1])
            path_latlon.append([lat, lon])
        
        return jsonify({
            'path': path_latlon,
            'distance': distance,
            'time_ms': elapsed_ms,
            'nodes_visited': stats['nodes_visited'],
            'edges_relaxed': stats['edges_relaxed'],
            'algorithm': stats.get('algorithm', 'A*')
        })
        
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