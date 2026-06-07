"""
Bidirectional A* algorithm for AdjacencyList.
Reuses A* helper from A_AStar.
"""

import math
import heapq
from .A_AStar import astar_search

def bidirectional_astar(adj_list, source, target, heuristic=None):
    """Bidirectional A* search."""
    stats = {
        'nodes_visited': 0,
        'edges_relaxed': 0,
        'heap_operations': 0,
        'algorithm': 'Bidirectional A*'
    }
    
    if heuristic is None:
        def heuristic(u, v):
            dx = u[0] - v[0]
            dy = u[1] - v[1]
            return dx*dx + dy*dy
    
    # Forward search
    g_f, parent_f, closed_f, _, _ = astar_search(
        adj_list, source, target, heuristic, 
        stats={'nodes_visited': 0, 'edges_relaxed': 0, 'heap_operations': 0}
    )
    
    # Backward search
    g_b, parent_b, closed_b, _, _ = astar_search(
        adj_list, target, source, heuristic,
        stats={'nodes_visited': 0, 'edges_relaxed': 0, 'heap_operations': 0}
    )
    
    # Find meeting point
    meeting_node = None
    best_distance = float('inf')
    
    for node in closed_f.intersection(closed_b):
        dist = g_f[node] + g_b[node]
        if dist < best_distance:
            best_distance = dist
            meeting_node = node
    
    # Reconstruct path
    path = []
    if meeting_node is not None:
        forward_path = []
        node = meeting_node
        while node is not None:
            forward_path.append(node)
            node = parent_f.get(node)
        forward_path.reverse()
        
        backward_path = []
        node = parent_b.get(meeting_node)
        while node is not None:
            backward_path.append(node)
            node = parent_b.get(node)
        
        path = forward_path + backward_path
    
    # Aggregate stats
    # (You'd need to combine stats from both searches)
    
    if best_distance != float('inf'):
        best_distance = math.sqrt(best_distance)
    
    return path, best_distance, stats