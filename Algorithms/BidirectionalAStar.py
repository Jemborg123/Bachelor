"""
Bidirectional A* algorithm implementation from scratch.
"""

import math
import heapq

def bidirectional_astar(graph, source, target, weight='weight', heuristic=None):
    """
    Bidirectional A* search algorithm.
    
    Runs A* simultaneously from both source and target.
    Stops when the two searches meet.
    """
    stats = {
        'nodes_visited': 0,
        'edges_relaxed': 0,
        'heap_operations': 0,
        'algorithm': 'Bidirectional A*'
    }
    
    # Default heuristic: Euclidean distance
    if heuristic is None:
        def heuristic(u, v):
            if ('x' in graph.nodes[u] and 'x' in graph.nodes[v] and
                'y' in graph.nodes[u] and 'y' in graph.nodes[v]):
                dx = graph.nodes[u]['x'] - graph.nodes[v]['x']
                dy = graph.nodes[u]['y'] - graph.nodes[v]['y']
                return math.sqrt(dx*dx + dy*dy)
            return 0
    
    # Forward search (source -> target)
    g_f = {source: 0}
    f_f = {source: heuristic(source, target)}
    parent_f = {source: None}
    open_f = [(f_f[source], source)]
    closed_f = set()
    
    # Backward search (target -> source)
    g_b = {target: 0}
    f_b = {target: heuristic(target, source)}
    parent_b = {target: None}
    open_b = [(f_b[target], target)]
    closed_b = set()
    
    stats['heap_operations'] = 2
    
    best_distance = float('inf')
    best_node = None
    
    while open_f and open_b:
        # ========== FORWARD STEP ==========
        if open_f:
            f_val, u = heapq.heappop(open_f)
            stats['heap_operations'] += 1
            
            if u in closed_f:
                continue
            
            closed_f.add(u)
            stats['nodes_visited'] += 1
            
            # Check if u is in backward closed set
            if u in closed_b:
                dist = g_f[u] + g_b[u]
                if dist < best_distance:
                    best_distance = dist
                    best_node = u
                    break
            
            # Early termination condition
            if best_node is not None and f_val >= best_distance:
                break
            
            # Explore neighbors
            for v in graph.neighbors(u):
                if v in closed_f:
                    continue
                
                weight_uv = graph[u][v].get(weight, 1)
                stats['edges_relaxed'] += 1
                
                new_g = g_f[u] + weight_uv
                
                if v not in g_f or new_g < g_f[v]:
                    g_f[v] = new_g
                    parent_f[v] = u
                    f_f[v] = new_g + heuristic(v, target)
                    heapq.heappush(open_f, (f_f[v], v))
                    stats['heap_operations'] += 1
        
        # ========== BACKWARD STEP ==========
        if open_b:
            f_val, u = heapq.heappop(open_b)
            stats['heap_operations'] += 1
            
            if u in closed_b:
                continue
            
            closed_b.add(u)
            stats['nodes_visited'] += 1
            
            # Check if u is in forward closed set
            if u in closed_f:
                dist = g_f[u] + g_b[u]
                if dist < best_distance:
                    best_distance = dist
                    best_node = u
                    break
            
            # Early termination condition
            if best_node is not None and f_val >= best_distance:
                break
            
            # Explore neighbors
            for v in graph.neighbors(u):
                if v in closed_b:
                    continue
                
                weight_uv = graph[u][v].get(weight, 1)
                stats['edges_relaxed'] += 1
                
                new_g = g_b[u] + weight_uv
                
                if v not in g_b or new_g < g_b[v]:
                    g_b[v] = new_g
                    parent_b[v] = u
                    f_b[v] = new_g + heuristic(v, source)
                    heapq.heappush(open_b, (f_b[v], v))
                    stats['heap_operations'] += 1
    
    # ========== PATH RECONSTRUCTION ==========
    path = []
    if best_node is not None:
        # Forward path from source to best_node
        forward_path = []
        node = best_node
        while node is not None:
            forward_path.append(node)
            node = parent_f.get(node)
        forward_path.reverse()
        
        # Backward path from best_node to target (excluding best_node)
        backward_path = []
        node = parent_b.get(best_node)
        while node is not None:
            backward_path.append(node)
            node = parent_b.get(node)
        
        path = forward_path + backward_path
    
    return path, best_distance, stats


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