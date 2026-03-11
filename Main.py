"""
Main controller for DTU pathfinding project.
Runs different algorithms and visualizes results.
"""

import pickle
import random
import time
import os

# Import your modules
from MapVisuals import create_path_map, create_comparison_map
# from Algorithms.Dijkstra import dijkstra, analyze_complexity 
from Algorithms import (
    dijkstra, 
    astar,
    bidirectional_astar, 
    alt,
    select_landmarks,          
    precompute_landmark_distances,
    analyze_complexity,
)

# Configuration
GRAPH_FILE = 'data/walkability_graph.pkl'

def load_graph():
    """Load the pre-built graph."""
    print(f"\n📂 Loading graph from {GRAPH_FILE}...")
    with open(GRAPH_FILE, 'rb') as f:
        G = pickle.load(f)
    print(f"  ✅ Graph loaded: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges")
    return G


def select_random_nodes(G, num_pairs=1):
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


def run_single_algorithm(G, algorithm_func, source, target, algo_name):
    """Run a single algorithm and return results."""
    print(f"\n🔍 Running {algo_name}...")
    
    V = G.number_of_nodes()
    E = G.number_of_edges()
    
    start_time = time.time()
    path, cost, stats = algorithm_func(G, source, target)
    elapsed = time.time() - start_time
    
    print(f"  ✅ Path found: {len(path)} nodes, {cost:.1f} m")
    
    # Analyze complexity
    analyze_complexity(V, E, stats, elapsed)
    
    return path, cost, stats


def run_all_algorithms(G, source, target):
    """Run all algorithms on the same source-target pair."""
    results = {}

    # Preprocess for ALT (do once)
    print("\n🔧 Preprocessing for ALT...")
    all_nodes = list(G.nodes())
    num_landmarks = min(16, len(all_nodes))
    landmarks = random.sample(all_nodes, num_landmarks)
    print(f"  Selected {len(landmarks)} random landmarks")
    dist_to, dist_from = precompute_landmark_distances(G, landmarks, max_distance=1500)

    # Dictionary of algorithms to test
    algorithms = {
        'Dijkstra': lambda g,s,t: dijkstra(g, s, t),
        'A*': lambda g,s,t: astar(g, s, t),
        'Bidirectional A*': lambda g,s,t: bidirectional_astar(g, s, t),
        'ALT': lambda g,s,t: alt(g, s, t, 
                               landmarks=landmarks, dist_to=dist_to, dist_from=dist_from),
    }
    
    for name, func in algorithms.items():
        path, cost, stats = run_single_algorithm(G, func, source, target, name)
        results[name] = (path, cost, stats)
    
    return results


def main():
    print("=" * 60)
    print("DTU PATHFINDING PROJECT")
    print("=" * 60)
    
    # Load graph
    G = load_graph()
    
    # Select random source-target pair
    pairs = select_random_nodes(G, num_pairs=1)
    source, target = pairs[0]
    
    print(f"\n🎯 Testing on:")
    print(f"  Source: node {source} @ ({G.nodes[source]['x']:.2f}, {G.nodes[source]['y']:.2f})")
    print(f"  Target: node {target} @ ({G.nodes[target]['x']:.2f}, {G.nodes[target]['y']:.2f})")
    
    # Run all algorithms
    results = run_all_algorithms(G, source, target)
    
    # Create individual maps for each algorithm
    # for name, (path, cost, _) in results.items():
    #     filename = f"{name.lower()}_path.html"
    #     create_path_map(G, path, cost, source, target, filename)
    
    for name, (path, cost, _) in results.items():
        # Clean filename (remove spaces and special chars)
        clean_name = name.lower().replace(' ', '_').replace('*', 'star').replace('(', '').replace(')', '')
        filename = f"{clean_name}_path.html"
        create_path_map(G, path, cost, source, target, filename)

    # Create comparison map
    comparison_results = {name: (path, cost) for name, (path, cost, _) in results.items()}
    create_comparison_map(G, comparison_results, "algorithm_comparison.html")
    
    print("\n✅ All done!")


if __name__ == "__main__":
    # You might need this import for largest component
    import networkx as nx
    main()