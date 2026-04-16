"""
Main controller for DTU pathfinding project.
Runs different algorithms and visualizes results.
"""

import math
import pickle
import random
import time
import os
import networkx as nx

# Import your modules
from MapVisuals import create_path_map, create_comprehensive_comparison_map
from Data.utils import load_adjacency_list
from DataSaver import save_path_data_to_files, save_graph_statistics

from Algorithms import (
    dijkstra_nx,
    astar_nx,
    bidirectional_astar_nx,
    alt_nx,
    dijkstra_adj,
    astar_adj,
    bidirectional_astar_adj,
    alt_adj,
    analyze_complexity,
    select_landmarks,
    precompute_landmark_distances
)

# Configuration
GRAPH_FILE = 'Data/Old_Graph_data/walkability_graph.pkl'
ADJACENCY_PATH = "Data/Data/Adjacency_list_ObstacleAwareGraph.json"

# ============================================================================
# NETWORKX LOADING (Original)
# ============================================================================

def load_nx_graph():
    """Load the pre-built graph."""
    print(f"\n📂 Loading NetworkX graph from {GRAPH_FILE}...")
    with open(GRAPH_FILE, 'rb') as f:
        G = pickle.load(f)
    # print(f"  ✅ Graph loaded: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges")
    # return G
    nx_nodes = G.number_of_nodes()
    nx_edges = G.number_of_edges()
    print(f"  ✅ Graph loaded: {nx_nodes} nodes, {nx_edges} edges")
    return G, nx_nodes, nx_edges


def select_random_nodes_nx(G, num_pairs=1):
    """Select random source-target pairs from largest component."""
    from MapVisuals import filter_outliers
    
    # Filter outliers and get largest component
    kept_nodes = filter_outliers(G)
    subgraph = G.subgraph(kept_nodes)
    components = list(nx.connected_components(subgraph))
    largest = list(max(components, key=len))
    
    pairs = []
    for _ in range(num_pairs):
        source, target = random.sample(largest, 2)
        pairs.append((source, target))
    
    return pairs

# ============================================================================
# ADJACENCY LIST LOADING (New)
# ============================================================================

def load_adjacency_graph():
    """Load the adjacency list from JSON file."""
    print(f"\n📂 Loading AdjacencyList from {ADJACENCY_PATH}...")
    adjacency_list, success = load_adjacency_list(ADJACENCY_PATH)
    
    if not success:
        raise FileNotFoundError(f"Could not load adjacency list from {ADJACENCY_PATH}")
    
    # # Count edges
    # num_nodes = len(adjacency_list.keys())
    # num_edges = 0
    # for node in adjacency_list.keys():
    #     neighbors = adjacency_list.neighbors(node)
    #     if neighbors:
    #         current = neighbors.head
    #         while current is not None:
    #             num_edges += 1
    #             current = current.next
    # num_edges //= 2
    
    # print(f"  ✅ AdjacencyList loaded: {num_nodes} nodes, {num_edges} edges")
    # return adjacency_list, num_nodes, num_edges

    adj_nodes = len(adjacency_list.keys())
    adj_edges = adjacency_list.numEdges()  # Or your method to count edges
    adj_edges //= 2  # If counting each edge twice
    
    print(f"  ✅ AdjacencyList loaded: {adj_nodes} nodes, {adj_edges} edges")
    return adjacency_list, adj_nodes, adj_edges


def select_random_nodes_adj(adjacency_list, num_pairs=1):
    """Select random source-target pairs from adjacency list."""
    all_nodes = list(adjacency_list.keys())
    pairs = []
    for _ in range(num_pairs):
        source, target = random.sample(all_nodes, 2)
        pairs.append((source, target))
    
    return pairs

# ============================================================================
# RUNNING ALGORITHMS (Both versions)
# ============================================================================

def run_single_algorithm_nx(G, algorithm_func, source, target, algo_name, **kwargs):
    """Run a single algorithm and return results."""
    print(f"\n🔍 Running {algo_name} (NetworkX)...")
    
    V = G.number_of_nodes()
    E = G.number_of_edges()
    
    start_time = time.time()
    path, cost, stats = algorithm_func(G, source, target, **kwargs)
    elapsed = time.time() - start_time

    stats['time_ms'] = elapsed * 1000
    
    print(f"  ✅ Path found: {len(path)} nodes, {cost:.1f} m")
    
    # Analyze complexity
    analyze_complexity(V, E, stats, elapsed)
    
    return path, cost, stats

def run_single_algorithm_adj(adj_list, algorithm_func, source, target, algo_name):
    """Run a single AdjacencyList-based algorithm."""
    print(f"\n🔍 Running {algo_name} (AdjacencyList)...")
    
    V = adj_list.length()
    E = adj_list.numEdges()
    E //= 2
    
    start_time = time.time()
    path, cost, stats = algorithm_func(adj_list, source, target)
    elapsed = time.time() - start_time
    cost = math.sqrt(cost)

    stats['time_ms'] = elapsed * 1000
    
    print(f"  ✅ Path found: {len(path)} nodes, {cost:.1f} m")
    
    from Algorithms.A_Dijkstra import analyze_complexity
    analyze_complexity(V, E, stats, elapsed)
    print(dir(adj_list)) 
    return path, cost, stats

# ============================================================================
# MAIN COMPARISON
# ============================================================================

def find_closest_nx_node(G_nx, x, y):
    """Find the closest node in NetworkX to given coordinates."""
    closest_node = None
    min_dist = float('inf')
    
    for node in G_nx.nodes():
        if 'x' in G_nx.nodes[node] and 'y' in G_nx.nodes[node]:
            nx_x = G_nx.nodes[node]['x']
            nx_y = G_nx.nodes[node]['y']
            dist = (nx_x - x)**2 + (nx_y - y)**2  # Squared distance (no sqrt needed)
            if dist < min_dist:
                min_dist = dist
                closest_node = node
    
    return closest_node


def select_same_points(adj_list, G_nx, num_pairs=1):
    """Pick random points from adjacency list, find closest in NetworkX."""
    
    # Get random nodes from adjacency list
    all_adj_nodes = list(adj_list.keys())

    if len(all_adj_nodes) < 2:
        print("❌ Not enough nodes in adjacency list!")
        return None, None
    
    source_adj, target_adj = random.sample(all_adj_nodes, 2)
    
    # Find closest NetworkX nodes by coordinates
    source_nx = find_closest_nx_node(G_nx, source_adj[0], source_adj[1])
    target_nx = find_closest_nx_node(G_nx, target_adj[0], target_adj[1])

    if source_nx is None or target_nx is None:
        print("❌ Could not find matching nodes in NetworkX!")
        return None, None
    
    print(f"\n🎯 Selected points:")
    print(f"  AdjacencyList: {source_adj} → {target_adj}")
    print(f"  NetworkX (closest): {source_nx} → {target_nx}")
    
    return (source_nx, target_nx), (source_adj, target_adj)

def select_identical_points(adj_list, G_nx):
    """Pick random points from adjacency list, find EXACT match in NetworkX."""
    
    # Get random nodes from adjacency list
    all_adj_nodes = list(adj_list.keys())
    source_adj, target_adj = random.sample(all_adj_nodes, 2)
    
    # Find EXACT matching coordinates in NetworkX
    source_nx = None
    target_nx = None
    
    for node in G_nx.nodes():
        if 'x' in G_nx.nodes[node] and 'y' in G_nx.nodes[node]:
            # Round to 2 decimals to handle floating point
            nx_x = round(G_nx.nodes[node]['x'], 2)
            nx_y = round(G_nx.nodes[node]['y'], 2)
            adj_x = round(source_adj[0], 2)
            adj_y = round(source_adj[1], 2)
            
            if nx_x == adj_x and nx_y == adj_y:
                source_nx = node
                break
    
    for node in G_nx.nodes():
        if 'x' in G_nx.nodes[node] and 'y' in G_nx.nodes[node]:
            nx_x = round(G_nx.nodes[node]['x'], 2)
            nx_y = round(G_nx.nodes[node]['y'], 2)
            adj_x = round(target_adj[0], 2)
            adj_y = round(target_adj[1], 2)
            
            if nx_x == adj_x and nx_y == adj_y:
                target_nx = node
                break
    
    if source_nx is None or target_nx is None:
        print("❌ Could not find exact matching nodes!")
        return None, None
    
    print(f"\n🎯 EXACT matching points:")
    print(f"  AdjacencyList: {source_adj} → {target_adj}")
    print(f"  NetworkX: node {source_nx} → node {target_nx}")
    
    return (source_nx, target_nx), (source_adj, target_adj)


# if __name__ == "__main__":
#     main()

def find_adj_node_by_coords(adj_list, x, y, tolerance=5):
    """Find node in adjacency list by coordinates."""
    for node in adj_list.keys():
        if abs(node[0] - x) < tolerance and abs(node[1] - y) < tolerance:
            return node
    return None


def select_matching_nodes(G_nx, adj_list, num_pairs=1):
    """Select random nodes from NetworkX and find matches in AdjacencyList."""
    from MapVisuals import filter_outliers
    
    # Filter outliers and get largest component
    kept_nodes = filter_outliers(G_nx)
    subgraph = G_nx.subgraph(kept_nodes)
    components = list(nx.connected_components(subgraph))
    largest = list(max(components, key=len))
    
    for _ in range(num_pairs):
        # Pick random nodes from NetworkX
        source_nx, target_nx = random.sample(largest, 2)
        
        # Get coordinates
        sx = G_nx.nodes[source_nx]['x']
        sy = G_nx.nodes[source_nx]['y']
        tx = G_nx.nodes[target_nx]['x']
        ty = G_nx.nodes[target_nx]['y']
        
        # Find matching nodes in adjacency list
        source_adj = find_adj_node_by_coords(adj_list, sx, sy)
        target_adj = find_adj_node_by_coords(adj_list, tx, ty)
        
        if source_adj and target_adj:
            return (source_nx, target_nx), (source_adj, target_adj)
    
    return None, None


def create_adj_path_map(adj_list, path, cost, source, target, filename="adj_path_map.html"):
    """Create a Folium map for adjacency list path."""
    import folium
    import numpy as np
    import geopandas as gpd
    from MapVisuals import detect_crs
    from shapely.geometry import Point
        
    source_crs = detect_crs()
    # Reproject path nodes to WGS84
    path_points = gpd.GeoDataFrame(
    [{'node': i} for i, n in enumerate(path)],
    geometry=[Point(n[0], n[1]) for n in path], 
    crs=source_crs
).to_crs("EPSG:4326")
    
    path_latlon = [(row.geometry.y, row.geometry.x) for _, row in path_points.iterrows()]
    
    if len(path_latlon) == 0:
        print(f"  ⚠️ No valid coordinates found in path, skipping map")
        return

    mid_lat = np.mean([p[0] for p in path_latlon])
    mid_lon = np.mean([p[1] for p in path_latlon])

    # Check for NaN values
    if np.isnan(mid_lat) or np.isnan(mid_lon):
        print(f"  ⚠️ Invalid map center coordinates, skipping map")
        return
    
    m = folium.Map(location=[mid_lat, mid_lon], zoom_start=17, tiles='OpenStreetMap')
    
    # Add DTU buildings WMS layer
    folium.WmsTileLayer(
        url="https://casgis.azurewebsites.net/geoserver/dtu/wms",
        name='DTU Buildings',
        layers='dtu:llyn_bygning_dtu',
        fmt='image/png',
        transparent=True,
        version='1.1.1',
        attr='GeoServer DTU',
        overlay=True,
        control=True
    ).add_to(m)
    
    # Add path
    folium.PolyLine(
        locations=path_latlon,
        color='red',
        weight=5,
        opacity=0.8,
        tooltip=f"Path: {cost:.1f} m"
    ).add_to(m)
    
    # Add markers
    folium.Marker(
        location=path_latlon[0],
        popup=f"Start",
        icon=folium.Icon(color='green', icon='play')
    ).add_to(m)
    
    folium.Marker(
        location=path_latlon[-1],
        popup=f"End",
        icon=folium.Icon(color='red', icon='stop')
    ).add_to(m)
    
    folium.LayerControl().add_to(m)
    m.save(filename)
    print(f"  ✅ Map saved to '{filename}'")


def main():
    print("=" * 80)
    print("ALGORITHM COMPARISON: NetworkX vs AdjacencyList")
    print("=" * 80)
    
    # Load both representations
    # G_nx = load_nx_graph()
    # adj_list, _, _ = load_adjacency_graph()
    G_nx, nx_nodes, nx_edges = load_nx_graph()
    adj_list, adj_nodes, adj_edges = load_adjacency_graph()
    
    # Get matching nodes
    # nx_pair, adj_pair = select_same_points(adj_list, G_nx)
    nx_pair, adj_pair = select_identical_points(adj_list, G_nx)

    if nx_pair is None or adj_pair is None:
        # print("❌ Could not find matching nodes! Trying closest match...")
        nx_pair, adj_pair = select_same_points(adj_list, G_nx)
    
    if nx_pair is None or adj_pair is None:
        # print("❌ Failed to get matching nodes. Exiting.")
        return
    
    source_nx, target_nx = nx_pair
    source_adj, target_adj = adj_pair
    
    print(f"\n🎯 SAME test pair for both representations:")
    print(f"  NetworkX: node {source_nx} → node {target_nx}")
    print(f"    Coordinates: ({G_nx.nodes[source_nx]['x']:.2f}, {G_nx.nodes[source_nx]['y']:.2f}) → ({G_nx.nodes[target_nx]['x']:.2f}, {G_nx.nodes[target_nx]['y']:.2f})")
    print(f"  AdjacencyList: {source_adj} → {target_adj}")

    # Calculate distance between chosen points
    import math
    dx = source_adj[0] - target_adj[0]
    dy = source_adj[1] - target_adj[1]
    direct_dist = math.sqrt(dx*dx + dy*dy)
    print(f"  Direct distance between points: {direct_dist:.0f}m")
    
    # ========== NETWORKX ALGORITHMS ==========
    print("\n" + "=" * 80)
    print("RUNNING NETWORKX ALGORITHMS")
    print("=" * 80)
    
    nx_results = {}
    
    path, cost, stats = run_single_algorithm_nx(G_nx, dijkstra_nx, source_nx, target_nx, "Dijkstra")
    nx_results['Dijkstra'] = (path, cost, stats)
    # Only create map if path is valid
    if path and len(path) > 0:
        create_path_map(G_nx, path, cost, source_nx, target_nx, "nx_dijkstra.html")
    else:
        print(f"  ⚠️ No valid path found, skipping map")
    
    path, cost, stats = run_single_algorithm_nx(G_nx, astar_nx, source_nx, target_nx, "A*")
    nx_results['A*'] = (path, cost, stats)
    if path and len(path) > 0:
        create_path_map(G_nx, path, cost, source_nx, target_nx, "nx_astar.html")
    else:
        print(f"  ⚠️ No path found for A*, skipping map")
    
    path, cost, stats = run_single_algorithm_nx(G_nx, bidirectional_astar_nx, source_nx, target_nx, "Bidirectional A*")
    nx_results['Bidirectional A*'] = (path, cost, stats)
    if path and len(path) > 0:
        create_path_map(G_nx, path, cost, source_nx, target_nx, "nx_bidirectional.html")
    else:
        print(f"  ⚠️ No path found for Bidirectional A*, skipping map")

    # ALT (with preprocessing)
    print("\n🔧 Preprocessing for ALT...")
    all_nodes = list(G_nx.nodes())
    num_landmarks = min(16, len(all_nodes))
    landmarks = select_landmarks(G_nx, num_landmarks=num_landmarks, strategy='random')
    print(f"  Selected {len(landmarks)} random landmarks")
    dist_to, dist_from = precompute_landmark_distances(G_nx, landmarks, max_distance=1500)

    path, cost, stats = run_single_algorithm_nx(G_nx, alt_nx, source_nx, target_nx, "ALT",
                                            landmarks=landmarks, dist_to=dist_to, dist_from=dist_from)
    nx_results['ALT'] = (path, cost, stats)
    if path and len(path) > 0:
        create_path_map(G_nx, path, cost, source_nx, target_nx, "nx_alt.html")
    
    # ========== ADJACENCYLIST ALGORITHMS ==========
    print("\n" + "=" * 80)
    print("RUNNING ADJACENCYLIST ALGORITHMS")
    print("=" * 80)
    
    adj_results = {}
    
    path, cost, stats = run_single_algorithm_adj(adj_list, dijkstra_adj, source_adj, target_adj, "Dijkstra")
    adj_results['Dijkstra (Adj)'] = (path, cost, stats)
    create_adj_path_map(adj_list, path, cost, source_adj, target_adj, "Maps/adj_dijkstra.html")
    
    path, cost, stats = run_single_algorithm_adj(adj_list, astar_adj, source_adj, target_adj, "A*")
    adj_results['A* (Adj)'] = (path, cost, stats)
    create_adj_path_map(adj_list, path, cost, source_adj, target_adj, "Maps/adj_astar.html")

    path, cost, stats = run_single_algorithm_adj(adj_list, bidirectional_astar_adj, source_adj, target_adj, "Bidirectional A*")
    adj_results['Bidirectional A* (Adj)'] = (path, cost, stats)
    create_adj_path_map(adj_list, path, cost, source_adj, target_adj, "Maps/adj_bidirectional.html")
    
    path, cost, stats = run_single_algorithm_adj(adj_list, alt_adj, source_adj, target_adj, "ALT")
    adj_results['ALT (Adj)'] = (path, cost, stats)
    create_adj_path_map(adj_list, path, cost, source_adj, target_adj, "Maps/adj_alt.html")

    print("\n🔍 DEBUG: AdjacencyList results before map creation:")
    for name, (path, cost, stats) in adj_results.items():
        print(f"  {name}: path length={len(path) if path else 0}, cost={cost}")
        if path and len(path) > 0:
            print(f"    First node: {path[0]}, type: {type(path[0])}")
    
    create_comprehensive_comparison_map(
        G_nx, adj_list,
        nx_results, adj_results,
        source_nx, target_nx,
        source_adj, target_adj,
        "comprehensive_comparison.html"
    )

    # ========== SAVE PATH DATA TO FILES ==========
    save_path_data_to_files(
        G_nx, nx_results, adj_results,
        source_nx, target_nx,
        source_adj, target_adj
    )
    
    save_graph_statistics(G_nx, adj_list, nx_nodes, nx_edges, adj_nodes, adj_edges)

    # ========== SUMMARY ==========
    print("\n" + "=" * 80)
    print("PERFORMANCE SUMMARY")
    print("=" * 80)

    # Graph statistics comparison
    print("\n📊 GRAPH STATISTICS:")
    print(f"  {'NetworkX':<20} {nx_nodes:>6} nodes, {nx_edges:>6} edges")
    print(f"  {'AdjacencyList':<20} {adj_nodes:>6} nodes, {adj_edges:>6} edges")
    print(f"  Edge ratio (Adj/NX): {adj_edges/nx_edges:.2f}x")

    print(f"\n{'Algorithm':<30} {'Nodes Visited':<15} {'Time (ms)':<12} {'Distance (m)':<12}")
    print("-" * 70)

    for name, (path, cost, stats) in nx_results.items():
        time_ms = f"{stats.get('time_ms', 0):.3f}"
        print(f"{name:<30} {stats['nodes_visited']:<15} {time_ms:<12} {cost:<12.1f}")

    for name, (path, cost, stats) in adj_results.items():
        time_ms = f"{stats.get('time_ms', 0):.3f}"
        print(f"{name:<30} {stats['nodes_visited']:<15} {time_ms:<12} {cost:<12.1f}")
    
    print("\n✅ Comparison complete! Maps saved to 'Maps/' folder")


if __name__ == "__main__":
    import networkx as nx
    # Create maps folder if it doesn't exist
    os.makedirs("Maps", exist_ok=True)
    main()