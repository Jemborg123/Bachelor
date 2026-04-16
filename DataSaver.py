"""
Module for saving path data and statistics to files.
"""

import json
import csv
import os
import numpy as np


def convert_to_serializable(obj):
    """Convert NumPy types to Python native types for JSON serialization."""
    if isinstance(obj, np.integer):
        return int(obj)
    elif isinstance(obj, np.floating):
        return float(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, dict):
        return {key: convert_to_serializable(value) for key, value in obj.items()}
    elif isinstance(obj, (list, tuple)):
        return [convert_to_serializable(item) for item in obj]
    return obj


def save_path_data_to_files(G_nx, nx_results, adj_results, source_nx, target_nx, source_adj, target_adj):
    """
    Save all path coordinates and statistics to JSON and CSV files.
    """
    print("\n💾 Saving path data to files...")
    
    # Create data directory if it doesn't exist
    os.makedirs("Data/PathData", exist_ok=True)
    
    # ========== JSON FILE (Complete data) ==========
    json_data = {
        'source_target': {
            'networkx': {
                'source': convert_to_serializable(source_nx),
                'target': convert_to_serializable(target_nx),
                'source_coords': None,
                'target_coords': None
            },
            'adjacencylist': {
                'source': list(source_adj) if source_adj else None,
                'target': list(target_adj) if target_adj else None
            }
        },
        'graph_statistics': {
            'networkx': {
                'nodes': int(G_nx.number_of_nodes()),
                'edges': int(G_nx.number_of_edges())
            }
        },
        'algorithms': {}
    }
    
    # Get NetworkX source/target coordinates
    if source_nx is not None and 'x' in G_nx.nodes[source_nx]:
        json_data['source_target']['networkx']['source_coords'] = [
            float(G_nx.nodes[source_nx]['x']),
            float(G_nx.nodes[source_nx]['y'])
        ]
    if target_nx is not None and 'x' in G_nx.nodes[target_nx]:
        json_data['source_target']['networkx']['target_coords'] = [
            float(G_nx.nodes[target_nx]['x']),
            float(G_nx.nodes[target_nx]['y'])
        ]
    
    # Add NetworkX results
    for name, (path, cost, stats) in nx_results.items():
        # Convert path nodes to coordinates
        coords = []
        for node in path:
            if 'x' in G_nx.nodes[node] and 'y' in G_nx.nodes[node]:
                coords.append([
                    float(G_nx.nodes[node]['x']),
                    float(G_nx.nodes[node]['y'])
                ])
        
        json_data['algorithms'][f'NetworkX_{name}'] = {
            'path_nodes': convert_to_serializable(path),
            'path_coordinates': coords,
            'cost': float(cost) if cost != float('inf') else None,
            'nodes_visited': int(stats['nodes_visited']),
            'edges_relaxed': int(stats['edges_relaxed']),
            'heap_operations': int(stats['heap_operations']),
            'time_ms': float(stats.get('time_ms', 0))
        }
    
    # Add AdjacencyList results
    for name, (path, cost, stats) in adj_results.items():
        # Path nodes are already coordinates
        coords = [[float(node[0]), float(node[1])] for node in path] if path else []
        
        json_data['algorithms'][f'AdjacencyList_{name}'] = {
            'path_coordinates': coords,
            'cost': float(cost) if cost != float('inf') else None,
            'nodes_visited': int(stats['nodes_visited']),
            'edges_relaxed': int(stats['edges_relaxed']),
            'heap_operations': int(stats['heap_operations']),
            'time_ms': float(stats.get('time_ms', 0))
        }
    
    # Save JSON
    json_path = "Data/PathData/path_data.json"
    with open(json_path, 'w') as f:
        json.dump(json_data, f, indent=2)
    print(f"  ✅ JSON data saved to '{json_path}'")
    
    # ========== CSV FILE (Summary statistics) ==========
    csv_path = "Data/PathData/algorithm_summary.csv"
    with open(csv_path, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['Algorithm', 'Type', 'Path Length (nodes)', 'Distance (m)', 
                        'Nodes Visited', 'Edges Relaxed', 'Heap Operations', 'Time (ms)'])
        
        for name, (path, cost, stats) in nx_results.items():
            writer.writerow([
                name, 'NetworkX', len(path), f"{cost:.2f}" if cost != float('inf') else 'inf',
                stats['nodes_visited'], stats['edges_relaxed'],
                stats['heap_operations'], f"{stats.get('time_ms', 0):.3f}"
            ])
        
        for name, (path, cost, stats) in adj_results.items():
            writer.writerow([
                name, 'AdjacencyList', len(path), f"{cost:.2f}" if cost != float('inf') else 'inf',
                stats['nodes_visited'], stats['edges_relaxed'],
                stats['heap_operations'], f"{stats.get('time_ms', 0):.3f}"
            ])
    
    print(f"  ✅ CSV summary saved to '{csv_path}'")
    
    # ========== CSV FILE (Detailed path coordinates) ==========
    csv_path_detailed = "Data/PathData/path_coordinates.csv"
    with open(csv_path_detailed, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['Algorithm', 'Type', 'Point_Index', 'X', 'Y'])
        
        # NetworkX paths
        for name, (path, cost, stats) in nx_results.items():
            for i, node in enumerate(path):
                if 'x' in G_nx.nodes[node] and 'y' in G_nx.nodes[node]:
                    writer.writerow([
                        name, 'NetworkX', i,
                        f"{G_nx.nodes[node]['x']:.2f}",
                        f"{G_nx.nodes[node]['y']:.2f}"
                    ])
        
        # AdjacencyList paths
        for name, (path, cost, stats) in adj_results.items():
            if path:
                for i, node in enumerate(path):
                    writer.writerow([
                        name, 'AdjacencyList', i,
                        f"{node[0]:.2f}",
                        f"{node[1]:.2f}"
                    ])
    
    print(f"  ✅ Detailed coordinates saved to '{csv_path_detailed}'")
    
    print("\n📁 Data saved to 'Data/PathData/' folder")
    print("   - path_data.json (complete data)")
    print("   - algorithm_summary.csv (performance summary)")
    print("   - path_coordinates.csv (all path points)")


def save_graph_statistics(G_nx, adj_list, nx_nodes, nx_edges, adj_nodes, adj_edges):
    """
    Save graph statistics to a separate JSON file.
    """
    os.makedirs("Data/PathData", exist_ok=True)
    
    stats = {
        'networkx': {
            'nodes': int(nx_nodes),
            'edges': int(nx_edges)
        },
        'adjacencylist': {
            'nodes': int(adj_nodes),
            'edges': int(adj_edges)
        },
        'edge_ratio': float(adj_edges / nx_edges) if nx_edges > 0 else 0
    }
    
    filepath = "Data/PathData/graph_statistics.json"
    with open(filepath, 'w') as f:
        json.dump(stats, f, indent=2)
    
    print(f"  ✅ Graph statistics saved to '{filepath}'")