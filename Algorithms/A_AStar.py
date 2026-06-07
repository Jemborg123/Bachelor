"""
A* algorithm for AdjacencyList - extends A_Dijkstra with heuristic priority.
"""

import math
import heapq
from .A_Dijkstra import dijkstra

# Debug counter
_heuristic_call_count = 0
_debug_printed = False

def astar(adj_list, source, target, heuristic=None):
    """
    A* search for AdjacencyList: Dijkstra with f_score = g_score + heuristic as priority.
    
    Args:
        adj_list: AdjacencyList object
        source: source node (tuple of coordinates)
        target: target node (tuple of coordinates)
        heuristic: optional heuristic function(node) -> estimated distance to target
    
    Returns:
        tuple: (path list, distance, stats dictionary)
    """
    global _heuristic_call_count, _debug_printed

    # Default heuristic: Euclidean distance
    if heuristic is None:
        def heuristic(node):
            global _heuristic_call_count, _debug_printed
            _heuristic_call_count += 1

            dx = node[0] - target[0]
            dy = node[1] - target[1]
            h = dx*dx + dy*dy

            # Print first 5 heuristic values
            if _heuristic_call_count <= 5 and not _debug_printed:
                print(f"    [DEBUG] Heuristic for node {node[:2]}...: {h:.1f}")
            
            return h
    
    # Priority function for A*
    def get_priority(node, g_score):
        return g_score[node] + heuristic(node)
    
    # Early stop: reached target
    def early_stop(current, target, g_score):
        return current == target
    
    print(f"  [DEBUG] Running A* with heuristic")
    _heuristic_call_count = 0
    _debug_printed = True

    # Reuse A_Dijkstra with custom priority
    path, cost, stats = dijkstra(
        adj_list, source, target,
        get_priority=get_priority,
        early_stop_condition=early_stop
    )
    stats['algorithm'] = 'A*'
    
    return path, cost, stats


def euclidean_heuristic(node, target, adj_list):
    """Euclidean distance heuristic for adjacency list."""
    dx = node[0] - target[0]
    dy = node[1] - target[1]
    return math.sqrt(dx*dx + dy*dy)


def manhattan_heuristic(node, target, adj_list):
    """Manhattan distance heuristic for adjacency list."""
    dx = abs(node[0] - target[0])
    dy = abs(node[1] - target[1])
    return dx + dy


def zero_heuristic(node, target, adj_list):
    """Zero heuristic - makes A* behave like Dijkstra."""
    return 0

# In A_AStar.py - add this helper function

def astar_search(adj_list, source, target, heuristic, stats=None):
    """
    Core A* search that returns (g_score, parent, closed_set, open_set, stats).
    Used by bidirectional A*.
    """
    if stats is None:
        stats = {'nodes_visited': 0, 'edges_relaxed': 0, 'heap_operations': 0}
    
    g_score = {source: 0}
    parent = {source: None}
    open_set = [(heuristic(source, target), source)]
    closed_set = set()
    
    stats['heap_operations'] += 1
    
    while open_set:
        _, current = heapq.heappop(open_set)
        stats['heap_operations'] += 1
        
        if current in closed_set:
            continue
        
        closed_set.add(current)
        stats['nodes_visited'] += 1
        
        if current == target:
            break
        
        neighbors_list = adj_list.neighbors(current)
        if neighbors_list:
            current_node = neighbors_list.head
            while current_node:
                if hasattr(current_node, 'value'):
                    weight, neighbor = current_node.value
                else:
                    weight, neighbor = current_node
                
                if neighbor in closed_set:
                    current_node = current_node.next
                    continue
                
                stats['edges_relaxed'] += 1
                tentative_g = g_score[current] + weight
                
                if neighbor not in g_score or tentative_g < g_score[neighbor]:
                    parent[neighbor] = current
                    g_score[neighbor] = tentative_g
                    heapq.heappush(open_set, (tentative_g + heuristic(neighbor, target), neighbor))
                    stats['heap_operations'] += 1
                
                current_node = current_node.next
    
    return g_score, parent, closed_set, open_set, stats