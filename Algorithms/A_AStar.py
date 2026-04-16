"""
A* algorithm implementation for AdjacencyList.
"""

import math
import heapq

def astar(adj_list, source, target, heuristic=None):
    """
    A* search algorithm using AdjacencyList.
    """
    stats = {
        'nodes_visited': 0,
        'edges_relaxed': 0,
        'heap_operations': 0,
        'algorithm': 'A*'
    }
    
    # Default heuristic: Euclidean distance
    if heuristic is None:
        def heuristic(node):
            dx = node[0] - target[0]
            dy = node[1] - target[1]
            return math.sqrt(dx*dx + dy*dy)
    
    # Get all nodes from adjacency list
    all_nodes = list(adj_list.keys())
    
    # Initialize
    g_score = {node: float('inf') for node in all_nodes}
    f_score = {node: float('inf') for node in all_nodes}
    came_from = {node: None for node in all_nodes}
    
    g_score[source] = 0
    f_score[source] = heuristic(source)
    
    # Priority queue
    open_set = [(f_score[source], source)]
    stats['heap_operations'] += 1
    closed_set = set()
    
    while open_set:
        current_f, current = heapq.heappop(open_set)
        stats['heap_operations'] += 1
        
        if current in closed_set:
            continue
        
        closed_set.add(current)
        stats['nodes_visited'] += 1
        
        if current == target:
            break
        
        # 👈 FIXED: Use .neighbors() instead of .get()
        neighbors_list = adj_list.neighbors(current)
        if neighbors_list is None:
            continue
        
        # Iterate through linked list of neighbors
        current_node = neighbors_list.head
        while current_node is not None:
            # Get edge weight and neighbor from the node
            if hasattr(current_node, 'value'):
                edge_weight, neighbor = current_node.value
            else:
                edge_weight, neighbor = current_node
            
            if neighbor in closed_set:
                current_node = current_node.next
                continue
            
            stats['edges_relaxed'] += 1
            
            tentative_g = g_score[current] + edge_weight
            
            if tentative_g < g_score[neighbor]:
                came_from[neighbor] = current
                g_score[neighbor] = tentative_g
                f_score[neighbor] = tentative_g + heuristic(neighbor)
                heapq.heappush(open_set, (f_score[neighbor], neighbor))
                stats['heap_operations'] += 1
            
            current_node = current_node.next
    
    # Reconstruct path
    path = []
    if g_score[target] < float('inf'):
        node = target
        while node is not None:
            path.append(node)
            node = came_from[node]
        path.reverse()
    
    return path, g_score[target], stats