"""
Main controller for DTU pathfinding project.
Runs different algorithms and visualizes results.
"""

import pickle
import random
import time
import os
import networkx as nx

# Import your modules
from MapVisuals import create_path_map, create_comparison_map
from Data.utils import load_adjacency_list
# from Algorithms.Dijkstra import dijkstra, analyze_complexity 
# from Algorithms import (
#     dijkstra, 
#     astar,
#     bidirectional_astar, 
#     alt,
#     select_landmarks,          
#     precompute_landmark_distances,
#     analyze_complexity,
# )

from Algorithms import (
    dijkstra_nx,
    astar_nx,
    bidirectional_astar_nx,
    alt_nx,
    dijkstra_adj,
    # astar_adj,
    # bidirectional_astar_adj,
    analyze_complexity,
    select_landmarks,
    precompute_landmark_distances
)

# Configuration
GRAPH_FILE = 'data/walkability_graph.pkl'
ADJACENCY_PATH = "Data/Adjacency_list_ObstacleAware_better.json"

# ============================================================================
# NETWORKX LOADING (Original)
# ============================================================================

def load_nx_graph():
    """Load the pre-built graph."""
    print(f"\n📂 Loading NetworkX graph from {GRAPH_FILE}...")
    with open(GRAPH_FILE, 'rb') as f:
        G = pickle.load(f)
    print(f"  ✅ Graph loaded: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges")
    return G


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
    
    # Count edges
    num_nodes = len(adjacency_list.keys())
    num_edges = 0
    for node in adjacency_list.keys():
        neighbors = adjacency_list.get(node)
        if neighbors:
            current = neighbors.head
            while current is not None:
                num_edges += 1
                current = current.next
    num_edges //= 2
    
    print(f"  ✅ AdjacencyList loaded: {num_nodes} nodes, {num_edges} edges")
    return adjacency_list, num_nodes, num_edges


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

def run_single_algorithm_nx(G, algorithm_func, source, target, algo_name):
    """Run a single algorithm and return results."""
    print(f"\n🔍 Running {algo_name} (NetworkX)...")
    
    V = G.number_of_nodes()
    E = G.number_of_edges()
    
    start_time = time.time()
    path, cost, stats = algorithm_func(G, source, target)
    elapsed = time.time() - start_time
    
    print(f"  ✅ Path found: {len(path)} nodes, {cost:.1f} m")
    
    # Analyze complexity
    analyze_complexity(V, E, stats, elapsed)
    
    return path, cost, stats

def run_single_algorithm_adj(adj_list, algorithm_func, source, target, algo_name):
    """Run a single AdjacencyList-based algorithm."""
    print(f"\n🔍 Running {algo_name} (AdjacencyList)...")
    
    V = adj_list.length()
    E = 0
    for node in adj_list.keys():
        neighbors = adj_list.get(node)
        if neighbors:
            current = neighbors.head
            while current is not None:
                E += 1
                current = current.next
    E //= 2
    
    start_time = time.time()
    path, cost, stats = algorithm_func(adj_list, source, target)
    elapsed = time.time() - start_time
    
    print(f"  ✅ Path found: {len(path)} nodes, {cost:.1f} m")
    
    from Algorithms.A_Dijkstra import analyze_complexity
    analyze_complexity(V, E, stats, elapsed)
    print(dir(adj_list)) 
    return path, cost, stats

# ============================================================================
# MAIN COMPARISON
# ============================================================================

# def run_all_algorithms(G, source, target):
#     """Run all algorithms on the same source-target pair."""
#     results = {}

#     # Preprocess for ALT (do once)
#     print("\n🔧 Preprocessing for ALT...")
#     all_nodes = list(G.nodes())
#     num_landmarks = min(16, len(all_nodes))
#     landmarks = random.sample(all_nodes, num_landmarks)
#     print(f"  Selected {len(landmarks)} random landmarks")
#     dist_to, dist_from = precompute_landmark_distances(G, landmarks, max_distance=1500)

#     # Dictionary of algorithms to test
#     algorithms = {
#         'Dijkstra': lambda g,s,t: dijkstra(g, s, t),
#         'A*': lambda g,s,t: astar(g, s, t),
#         'Bidirectional A*': lambda g,s,t: bidirectional_astar(g, s, t),
#         'ALT': lambda g,s,t: alt(g, s, t, 
#                                landmarks=landmarks, dist_to=dist_to, dist_from=dist_from),
#     }
    
#     for name, func in algorithms.items():
#         path, cost, stats = run_single_algorithm(G, func, source, target, name)
#         results[name] = (path, cost, stats)
    
#     return results


# def main():
#     print("=" * 60)
#     print("DTU PATHFINDING PROJECT")
#     print("=" * 60)
    
#     # Load graph
#     G = load_graph()
    
#     # Select random source-target pair
#     pairs = select_random_nodes(G, num_pairs=1)
#     source, target = pairs[0]
    
#     print(f"\n🎯 Testing on:")
#     print(f"  Source: node {source} @ ({G.nodes[source]['x']:.2f}, {G.nodes[source]['y']:.2f})")
#     print(f"  Target: node {target} @ ({G.nodes[target]['x']:.2f}, {G.nodes[target]['y']:.2f})")
    
#     # Run all algorithms
#     results = run_all_algorithms(G, source, target)
    
#     # Create individual maps for each algorithm
#     # for name, (path, cost, _) in results.items():
#     #     filename = f"{name.lower()}_path.html"
#     #     create_path_map(G, path, cost, source, target, filename)
    
#     for name, (path, cost, _) in results.items():
#         # Clean filename (remove spaces and special chars)
#         clean_name = name.lower().replace(' ', '_').replace('*', 'star').replace('(', '').replace(')', '')
#         filename = f"{clean_name}_path.html"
#         create_path_map(G, path, cost, source, target, filename)

#     # Create comparison map
#     comparison_results = {name: (path, cost) for name, (path, cost, _) in results.items()}
#     create_comparison_map(G, comparison_results, "algorithm_comparison.html")
    
#     print("\n✅ All done!")


# if __name__ == "__main__":
#     # You might need this import for largest component
#     import networkx as nx
#     main()
# ------------------------------------------------------------------------------------------------------------------------------------
# def main():
#     print("=" * 80)
#     print("ALGORITHM COMPARISON: NetworkX vs AdjacencyList")
#     print("=" * 80)
    
#     # Load both graph representations
#     G_nx = load_nx_graph()
#     adj_list, _, _ = load_adjacency_graph()
    
#     # Get source-target pairs
#     pairs_nx = select_random_nodes_nx(G_nx, num_pairs=1)
#     source_nx, target_nx = pairs_nx[0]
    
#     pairs_adj = select_random_nodes_adj(adj_list, num_pairs=1)
#     source_adj, target_adj = pairs_adj[0]
    
#     print(f"\n🎯 NetworkX test pair:")
#     print(f"  Source: node {source_nx}")
#     print(f"  Target: node {target_nx}")
    
#     print(f"\n🎯 AdjacencyList test pair:")
#     print(f"  Source: {source_adj}")
#     print(f"  Target: {target_adj}")
    
#     # ========== NETWORKX ALGORITHMS ==========
#     print("\n" + "=" * 80)
#     print("RUNNING NETWORKX ALGORITHMS")
#     print("=" * 80)
    
#     nx_results = {}
    
#     path, cost, stats = run_single_algorithm_nx(G_nx, dijkstra_nx, source_nx, target_nx, "Dijkstra")
#     nx_results['Dijkstra'] = (path, cost, stats)
    
#     path, cost, stats = run_single_algorithm_nx(G_nx, astar_nx, source_nx, target_nx, "A*")
#     nx_results['A*'] = (path, cost, stats)
    
#     path, cost, stats = run_single_algorithm_nx(G_nx, bidirectional_astar_nx, source_nx, target_nx, "Bidirectional A*")
#     nx_results['Bidirectional A*'] = (path, cost, stats)
    
#     # ========== ADJACENCYLIST ALGORITHMS ==========
#     print("\n" + "=" * 80)
#     print("RUNNING ADJACENCYLIST ALGORITHMS")
#     print("=" * 80)
    
#     adj_results = {}
    
#     path, cost, stats = run_single_algorithm_adj(adj_list, dijkstra_adj, source_adj, target_adj, "Dijkstra")
#     adj_results['Dijkstra (Adj)'] = (path, cost, stats)
    
#     # path, cost, stats = run_single_algorithm_adj(adj_list, astar_adj, source_adj, target_adj, "A*")
#     # adj_results['A* (Adj)'] = (path, cost, stats)
    
#     # path, cost, stats = run_single_algorithm_adj(adj_list, bidirectional_astar_adj, source_adj, target_adj, "Bidirectional A*")
#     # adj_results['Bidirectional A* (Adj)'] = (path, cost, stats)
    
#     # ========== SUMMARY ==========
#     print("\n" + "=" * 80)
#     print("PERFORMANCE SUMMARY")
#     print("=" * 80)
#     print(f"\n{'Algorithm':<25} {'Nodes Visited':<15} {'Time (ms)':<12}")
#     print("-" * 60)
    
#     for name, (_, _, stats) in nx_results.items():
#         print(f"{name:<25} {stats['nodes_visited']:<15} {stats.get('time_ms', 'N/A'):<12}")
    
#     for name, (_, _, stats) in adj_results.items():
#         print(f"{name:<25} {stats['nodes_visited']:<15} {stats.get('time_ms', 'N/A'):<12}")
    
#     print("\n✅ Comparison complete!")


# if __name__ == "__main__":
#     main()

def find_adj_node_by_coords(adj_list, x, y, tolerance=0.1):
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
    
    # Path nodes are tuples (x, y)
    path_latlon = []
    for node in path:
        # Convert from UTM to lat/lon (assuming EPSG:25832)
        # You'll need to transform coordinates
        path_latlon.append((node[1], node[0]))  # Simple swap - may need proper conversion
    
    mid_lat = np.mean([p[0] for p in path_latlon])
    mid_lon = np.mean([p[1] for p in path_latlon])
    
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
    G_nx = load_nx_graph()
    adj_list, _, _ = load_adjacency_graph()
    
    # Get matching nodes
    nx_pair, adj_pair = select_matching_nodes(G_nx, adj_list)
    
    if nx_pair is None:
        print("❌ Could not find matching nodes!")
        return
    
    source_nx, target_nx = nx_pair
    source_adj, target_adj = adj_pair
    
    print(f"\n🎯 SAME test pair for both representations:")
    print(f"  NetworkX: node {source_nx} → node {target_nx}")
    print(f"    Coordinates: ({G_nx.nodes[source_nx]['x']:.2f}, {G_nx.nodes[source_nx]['y']:.2f}) → ({G_nx.nodes[target_nx]['x']:.2f}, {G_nx.nodes[target_nx]['y']:.2f})")
    print(f"  AdjacencyList: {source_adj} → {target_adj}")
    
    # ========== NETWORKX ALGORITHMS ==========
    print("\n" + "=" * 80)
    print("RUNNING NETWORKX ALGORITHMS")
    print("=" * 80)
    
    nx_results = {}
    
    path, cost, stats = run_single_algorithm_nx(G_nx, dijkstra_nx, source_nx, target_nx, "Dijkstra")
    nx_results['Dijkstra'] = (path, cost, stats)
    create_path_map(G_nx, path, cost, source_nx, target_nx, "maps/nx_dijkstra.html")
    
    path, cost, stats = run_single_algorithm_nx(G_nx, astar_nx, source_nx, target_nx, "A*")
    nx_results['A*'] = (path, cost, stats)
    create_path_map(G_nx, path, cost, source_nx, target_nx, "maps/nx_astar.html")
    
    path, cost, stats = run_single_algorithm_nx(G_nx, bidirectional_astar_nx, source_nx, target_nx, "Bidirectional A*")
    nx_results['Bidirectional A*'] = (path, cost, stats)
    create_path_map(G_nx, path, cost, source_nx, target_nx, "maps/nx_bidirectional.html")
    
    # ========== ADJACENCYLIST ALGORITHMS ==========
    print("\n" + "=" * 80)
    print("RUNNING ADJACENCYLIST ALGORITHMS")
    print("=" * 80)
    
    adj_results = {}
    
    path, cost, stats = run_single_algorithm_adj(adj_list, dijkstra_adj, source_adj, target_adj, "Dijkstra")
    adj_results['Dijkstra (Adj)'] = (path, cost, stats)
    create_adj_path_map(adj_list, path, cost, source_adj, target_adj, "maps/adj_dijkstra.html")
    
    # Uncomment when A* and Bidirectional A* are ready for adjacency list
    # path, cost, stats = run_single_algorithm_adj(adj_list, astar_adj, source_adj, target_adj, "A*")
    # adj_results['A* (Adj)'] = (path, cost, stats)
    # create_adj_path_map(adj_list, path, cost, source_adj, target_adj, "maps/adj_astar.html")
    
    # ========== SUMMARY ==========
    print("\n" + "=" * 80)
    print("PERFORMANCE SUMMARY")
    print("=" * 80)
    print(f"\n{'Algorithm':<30} {'Nodes Visited':<15} {'Time (ms)':<12} {'Distance (m)':<12}")
    print("-" * 70)
    
    for name, (path, cost, stats) in nx_results.items():
        print(f"{name:<30} {stats['nodes_visited']:<15} {stats.get('time_ms', 'N/A'):<12} {cost:<12.1f}")
    
    for name, (path, cost, stats) in adj_results.items():
        print(f"{name:<30} {stats['nodes_visited']:<15} {stats.get('time_ms', 'N/A'):<12} {cost:<12.1f}")
    
    print("\n✅ Comparison complete! Maps saved to 'maps/' folder")


if __name__ == "__main__":
    import networkx as nx
    # Create maps folder if it doesn't exist
    os.makedirs("maps", exist_ok=True)
    main()