"""
Bidirectional A* algorithm implementation for AdjacencyList.
"""

import math
import heapq

def bidirectional_astar(adj_list, source, target, heuristic=None):
    """
    Bidirectional A* search using AdjacencyList.
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
            dx = u[0] - v[0]
            dy = u[1] - v[1]
            return math.sqrt(dx*dx + dy*dy)
    
    # Forward search
    g_f = {source: 0}
    f_f = {source: heuristic(source, target)}
    parent_f = {source: None}
    open_f = [(f_f[source], source)]
    closed_f = set()
    
    # Backward search
    g_b = {target: 0}
    f_b = {target: heuristic(target, source)}
    parent_b = {target: None}
    open_b = [(f_b[target], target)]
    closed_b = set()
    
    stats['heap_operations'] = 2
    
    best_distance = float('inf')
    best_node = None
    
    while open_f and open_b:
        # Forward step
        if open_f:
            f_val, u = heapq.heappop(open_f)
            stats['heap_operations'] += 1
            
            if u in closed_f:
                continue
            
            closed_f.add(u)
            stats['nodes_visited'] += 1
            
            if u in closed_b:
                dist = g_f[u] + g_b[u]
                if dist < best_distance:
                    best_distance = dist
                    best_node = u
                    break
            
            if best_node is not None and f_val >= best_distance:
                break
            
            # 👈 FIXED: Use .neighbors() instead of .get()
            neighbors_list = adj_list.neighbors(u)
            if neighbors_list:
                current = neighbors_list.head
                while current:
                    if hasattr(current, 'value'):
                        w, v = current.value
                    else:
                        w, v = current
                    
                    if v in closed_f:
                        current = current.next
                        continue
                    
                    stats['edges_relaxed'] += 1
                    new_g = g_f[u] + w
                    
                    if v not in g_f or new_g < g_f[v]:
                        g_f[v] = new_g
                        parent_f[v] = u
                        f_f[v] = new_g + heuristic(v, target)
                        heapq.heappush(open_f, (f_f[v], v))
                        stats['heap_operations'] += 1
                    
                    current = current.next
        
        # Backward step
        if open_b:
            f_val, u = heapq.heappop(open_b)
            stats['heap_operations'] += 1
            
            if u in closed_b:
                continue
            
            closed_b.add(u)
            stats['nodes_visited'] += 1
            
            if u in closed_f:
                dist = g_f[u] + g_b[u]
                if dist < best_distance:
                    best_distance = dist
                    best_node = u
                    break
            
            if best_node is not None and f_val >= best_distance:
                break
            
            # 👈 FIXED: Use .neighbors() instead of .get()
            neighbors_list = adj_list.neighbors(u)
            if neighbors_list:
                current = neighbors_list.head
                while current:
                    if hasattr(current, 'value'):
                        w, v = current.value
                    else:
                        w, v = current
                    
                    if v in closed_b:
                        current = current.next
                        continue
                    
                    stats['edges_relaxed'] += 1
                    new_g = g_b[u] + w
                    
                    if v not in g_b or new_g < g_b[v]:
                        g_b[v] = new_g
                        parent_b[v] = u
                        f_b[v] = new_g + heuristic(v, source)
                        heapq.heappush(open_b, (f_b[v], v))
                        stats['heap_operations'] += 1
                    
                    current = current.next
    
    # Reconstruct path
    path = []
    if best_node is not None:
        # Forward part
        forward_path = []
        node = best_node
        while node is not None:
            forward_path.append(node)
            node = parent_f.get(node)
        forward_path.reverse()
        
        # Backward part
        backward_path = []
        node = parent_b.get(best_node)
        while node is not None:
            backward_path.append(node)
            node = parent_b.get(node)
        
        path = forward_path + backward_path
    
    return path, best_distance, stats