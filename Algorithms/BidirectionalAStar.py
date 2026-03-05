"""
Bidirectional A* algorithm implementation from scratch.
"""

import math
import heapq

def bidirectional_astar(graph, source, target, weight='weight', heuristic=None):
    """
    Bidirectional A* search algorithm from scratch.
    
    Runs A* simultaneously from both source and target.
    Returns when the two searches meet.
    """
    stats = {
        'nodes_visited': 0,
        'edges_relaxed': 0,
        'heap_operations': 0,
        'algorithm': 'Bidirectional A*'
    }
    
    # Default heuristic
    if heuristic is None:
        def heuristic(u, v):
            if ('x' in graph.nodes[u] and 'x' in graph.nodes[v] and
                'y' in graph.nodes[u] and 'y' in graph.nodes[v]):
                dx = graph.nodes[u]['x'] - graph.nodes[v]['x']
                dy = graph.nodes[u]['y'] - graph.nodes[v]['y']
                return math.sqrt(dx*dx + dy*dy)
            return 0
    
    # Forward search (from source to target)
    g_forward = {node: float('inf') for node in graph.nodes()}
    f_forward = {node: float('inf') for node in graph.nodes()}
    parent_forward = {node: None for node in graph.nodes()}
    g_forward[source] = 0
    f_forward[source] = heuristic(source, target)
    
    # Backward search (from target to source)
    g_backward = {node: float('inf') for node in graph.nodes()}
    f_backward = {node: float('inf') for node in graph.nodes()}
    parent_backward = {node: None for node in graph.nodes()}
    g_backward[target] = 0
    f_backward[target] = heuristic(target, source)
    
    # Priority queues
    open_forward = [(f_forward[source], source)]
    open_backward = [(f_backward[target], target)]
    stats['heap_operations'] += 2
    
    closed_forward = set()
    closed_backward = set()
    
    best_path_length = float('inf')
    meeting_node = None
    
    while open_forward and open_backward:
        # Forward step
        if open_forward:
            current_f, current = heapq.heappop(open_forward)
            stats['heap_operations'] += 1
            
            if current in closed_forward:
                continue
                
            closed_forward.add(current)
            stats['nodes_visited'] += 1
            
            # Check if current node was reached by backward search
            if current in g_backward and g_backward[current] < float('inf'):
                path_length = g_forward[current] + g_backward[current]
                if path_length < best_path_length:
                    best_path_length = path_length
                    meeting_node = current
            
            # Early termination if we've found a path and forward's best f-score is >= best_path_length
            if meeting_node is not None and open_forward and open_forward[0][0] >= best_path_length:
                break
            
            # Explore forward neighbors
            for neighbor in graph.neighbors(current):
                if neighbor in closed_forward:
                    continue
                    
                edge_weight = graph[current][neighbor].get(weight, 1)
                stats['edges_relaxed'] += 1
                
                tentative_g = g_forward[current] + edge_weight
                
                if tentative_g < g_forward[neighbor]:
                    parent_forward[neighbor] = current
                    g_forward[neighbor] = tentative_g
                    f_forward[neighbor] = tentative_g + heuristic(neighbor, target)
                    heapq.heappush(open_forward, (f_forward[neighbor], neighbor))
                    stats['heap_operations'] += 1
        
        # Backward step
        if open_backward:
            current_f, current = heapq.heappop(open_backward)
            stats['heap_operations'] += 1
            
            if current in closed_backward:
                continue
                
            closed_backward.add(current)
            stats['nodes_visited'] += 1
            
            # Check if current node was reached by forward search
            if current in g_forward and g_forward[current] < float('inf'):
                path_length = g_forward[current] + g_backward[current]
                if path_length < best_path_length:
                    best_path_length = path_length
                    meeting_node = current
            
            # Early termination
            if meeting_node is not None and open_backward and open_backward[0][0] >= best_path_length:
                break
            
            # Explore backward neighbors
            for neighbor in graph.neighbors(current):
                if neighbor in closed_backward:
                    continue
                    
                edge_weight = graph[current][neighbor].get(weight, 1)
                stats['edges_relaxed'] += 1
                
                tentative_g = g_backward[current] + edge_weight
                
                if tentative_g < g_backward[neighbor]:
                    parent_backward[neighbor] = current
                    g_backward[neighbor] = tentative_g
                    f_backward[neighbor] = tentative_g + heuristic(neighbor, source)
                    heapq.heappush(open_backward, (f_backward[neighbor], neighbor))
                    stats['heap_operations'] += 1
    
    # Reconstruct path
    path = []
    if meeting_node is not None:
        # Build path from source to meeting node
        path_forward = []
        node = meeting_node
        while node is not None:
            path_forward.append(node)
            node = parent_forward[node]
        path_forward.reverse()
        
        # Build path from meeting node to target (excluding meeting node)
        path_backward = []
        node = parent_backward[meeting_node]
        while node is not None:
            path_backward.append(node)
            node = parent_backward[node]
        
        path = path_forward + path_backward
    
    return path, best_path_length, stats


def euclidean_heuristic(u, v, graph):
    """Euclidean distance heuristic."""
    if ('x' in graph.nodes[u] and 'x' in graph.nodes[v] and
        'y' in graph.nodes[u] and 'y' in graph.nodes[v]):
        dx = graph.nodes[u]['x'] - graph.nodes[v]['x']
        dy = graph.nodes[u]['y'] - graph.nodes[v]['y']
        return math.sqrt(dx*dx + dy*dy)
    return 0


def manhattan_heuristic(u, v, graph):
    """Manhattan distance heuristic."""
    if ('x' in graph.nodes[u] and 'x' in graph.nodes[v] and
        'y' in graph.nodes[u] and 'y' in graph.nodes[v]):
        dx = abs(graph.nodes[u]['x'] - graph.nodes[v]['x'])
        dy = abs(graph.nodes[u]['y'] - graph.nodes[v]['y'])
        return dx + dy
    return 0