"""
Core Dijkstra for AdjacencyList - pure Python, no external libraries.
"""

import heapq
import math

def dijkstra(adj_list, source, target, get_priority=None, early_stop_condition=None):
    """
    Generic Dijkstra for AdjacencyList.
    """
    stats = {
        'nodes_visited': 0,
        'edges_relaxed': 0,
        'heap_operations': 0,
        'algorithm': 'Dijkstra'
    }
    
    if get_priority is None:
        def get_priority(node, g_score):
            return g_score[node]
    
    if early_stop_condition is None:
        def early_stop_condition(current, target, g_score):
            return current == target
    
    # Debug: print first 5 nodes popped
    debug_count = 0

    # Initialize - AdjacencyList uses keys() not nodes()
    all_nodes = list(adj_list.keys())
    g_score = {node: float('inf') for node in all_nodes}
    came_from = {node: None for node in all_nodes}
    g_score[source] = 0
    
    pq = [(get_priority(source, g_score), source)]
    stats['heap_operations'] += 1
    closed_set = set()
    
    while pq:
        current_priority, current = heapq.heappop(pq)
        stats['heap_operations'] += 1

        # Debug first 5 nodes popped
        if debug_count < 5:
            print(f"    [DEBUG] Popped node {current[:2]}... with priority {current_priority:.1f}, g={g_score[current]:.1f}")
            debug_count += 1
        
        if current in closed_set:
            continue
        
        closed_set.add(current)
        stats['nodes_visited'] += 1
        
        if early_stop_condition(current, target, g_score):
            break
        
        # AdjacencyList uses neighbors() method
        neighbors_list = adj_list.neighbors(current)
        if neighbors_list is None:
            continue
        
        current_node = neighbors_list.head
        while current_node:
            # Get edge weight and neighbor from linked list node
            if hasattr(current_node, 'value'):
                edge_weight, neighbor = current_node.value
            else:
                edge_weight, neighbor = current_node
            
            stats['edges_relaxed'] += 1
            
            tentative_g = g_score[current] + edge_weight
            
            if tentative_g < g_score[neighbor]:
                came_from[neighbor] = current
                g_score[neighbor] = tentative_g
                heapq.heappush(pq, (get_priority(neighbor, g_score), neighbor))
                stats['heap_operations'] += 1
            
            current_node = current_node.next

    
    print(f"  Dijkstra g_score[{target[:10]}...] = {g_score[target]:.1f}")
    
    # Reconstruct path
    path = []
    if g_score[target] < float('inf'):
        node = target
        while node is not None:
            path.append(node)
            node = came_from[node]
        path.reverse()

        # Print path walking verification (only if path exists)
        actual_length = 0
        for i in range(len(path)-1):
            # Find edge weight between path[i] and path[i+1]
            neighbors = adj_list.neighbors(path[i])
            if neighbors:
                curr = neighbors.head
                while curr:
                    weight, neighbor = curr.value if hasattr(curr, 'value') else curr
                    if neighbor == path[i+1]:
                        actual_length += weight
                        break
                    curr = curr.next
        print(f"  Path walking sum (squared): {actual_length:.1f}")
        print(f"  Path walking sum (actual): {math.sqrt(actual_length):.1f}")
    
    return path, g_score[target], stats