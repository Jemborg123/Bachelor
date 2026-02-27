"""
Dijkstra's algorithm implementation with complexity analysis.
"""

import heapq
import math

def dijkstra(graph, source, target, weight='weight'):
    """
    Custom implementation of Dijkstra's algorithm.
    
    Time Complexity: O((V + E) log V) with binary heap
    Space Complexity: O(V)
    
    Args:
        graph: NetworkX graph object
        source: source node
        target: target node
        weight: edge attribute to use as weight
    
    Returns:
        tuple: (path list, distance, stats dictionary)
    """
    stats = {
        'nodes_visited': 0,
        'edges_relaxed': 0,
        'heap_operations': 0,
        'algorithm': 'Dijkstra'
    }
    
    # Initialize distances and predecessors
    dist = {node: float('inf') for node in graph.nodes()}
    prev = {node: None for node in graph.nodes()}
    dist[source] = 0
    
    # Priority queue: (distance, node)
    pq = [(0, source)]
    stats['heap_operations'] += 1
    
    # Visited set
    visited = set()
    
    while pq:
        # Extract min
        current_dist, current = heapq.heappop(pq)
        stats['heap_operations'] += 1
        
        # Skip if we've already found a better path
        if current_dist > dist[current]:
            continue
        
        # Mark as visited
        if current not in visited:
            visited.add(current)
            stats['nodes_visited'] += 1
        
        # Early termination if we reached target
        if current == target:
            break
        
        # Relax all neighbors
        for neighbor in graph.neighbors(current):
            edge_weight = graph[current][neighbor].get(weight, 1)
            stats['edges_relaxed'] += 1
            
            new_dist = current_dist + edge_weight
            
            if new_dist < dist[neighbor]:
                dist[neighbor] = new_dist
                prev[neighbor] = current
                heapq.heappush(pq, (new_dist, neighbor))
                stats['heap_operations'] += 1
    
    # Reconstruct path
    path = []
    if dist[target] < float('inf'):
        node = target
        while node is not None:
            path.append(node)
            node = prev[node]
        path.reverse()
    
    return path, dist[target], stats


def analyze_complexity(V, E, stats, elapsed_time):
    """
    Analyze and print complexity information.
    """
    print(f"\n📊 {stats['algorithm']} COMPLEXITY ANALYSIS:")
    print(f"  Graph size: |V| = {V}, |E| = {E}")
    print(f"  Theoretical: O((|V| + |E|) log |V|) = O(({V} + {E}) log {V})")
    print(f"  ≈ {((V + E) * math.log2(V)):.0f} operations (estimate)")
    print(f"\n  Actual performance:")
    print(f"    Nodes visited: {stats['nodes_visited']} ({stats['nodes_visited']/V*100:.1f}% of |V|)")
    print(f"    Edges relaxed: {stats['edges_relaxed']} ({stats['edges_relaxed']/E*100:.1f}% of |E|)")
    print(f"    Heap ops: {stats['heap_operations']}")
    print(f"    Time: {elapsed_time*1000:.2f} ms")
    
    # Empirical complexity verification
    theoretical_ops = (V + E) * math.log2(V)
    actual_ops = stats['edges_relaxed'] + stats['heap_operations']
    ratio = actual_ops / theoretical_ops if theoretical_ops > 0 else 0
    print(f"\n  Complexity verification:")
    print(f"    Theoretical ops ~ {theoretical_ops:.0f}")
    print(f"    Actual ops: {actual_ops}")
    print(f"    Ratio: {ratio:.3f} (should be ~1 for average case)")