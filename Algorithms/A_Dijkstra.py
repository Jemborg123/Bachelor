"""
Dijkstra's algorithm implementation with complexity analysis.
Uses custom AdjacencyList structure and custom heap implementation.
No external libraries allowed.
"""

import math

# ============================================================================
# CUSTOM MIN HEAP IMPLEMENTATION
# ============================================================================

class MinHeap:
    """
    Custom min-heap implementation for Dijkstra's algorithm.
    Stores elements as (priority, value) tuples.
    """
    
    def __init__(self):
        self.heap = []
        self.size = 0
    
    def push(self, priority, value):
        """Insert a new element into the heap."""
        self.heap.append((priority, value))
        self.size += 1
        self._sift_up(self.size - 1)
    
    def pop(self):
        """Remove and return the element with smallest priority."""
        if self.size == 0:
            return None
        
        # Swap root with last element
        self._swap(0, self.size - 1)
        priority, value = self.heap.pop()
        self.size -= 1
        
        # Restore heap property
        if self.size > 0:
            self._sift_down(0)
        
        return priority, value
    
    def peek(self):
        """Return the smallest element without removing it."""
        if self.size == 0:
            return None
        return self.heap[0]
    
    def is_empty(self):
        """Check if heap is empty."""
        return self.size == 0
    
    def _sift_up(self, index):
        """Move element up to maintain heap property."""
        while index > 0:
            parent = (index - 1) // 2
            if self.heap[parent][0] <= self.heap[index][0]:
                break
            self._swap(parent, index)
            index = parent
    
    def _sift_down(self, index):
        """Move element down to maintain heap property."""
        while True:
            left = 2 * index + 1
            right = 2 * index + 2
            smallest = index
            
            if left < self.size and self.heap[left][0] < self.heap[smallest][0]:
                smallest = left
            if right < self.size and self.heap[right][0] < self.heap[smallest][0]:
                smallest = right
            
            if smallest == index:
                break
            
            self._swap(index, smallest)
            index = smallest
    
    def _swap(self, i, j):
        """Swap two elements in the heap."""
        self.heap[i], self.heap[j] = self.heap[j], self.heap[i]


# ============================================================================
# DIJKSTRA ALGORITHM
# ============================================================================

def dijkstra(adjacency_list, source, target):
    """
    Custom implementation of Dijkstra's algorithm using AdjacencyList.
    Uses custom min-heap (no external libraries).
    
    Time Complexity: O((V + E) log V) with binary heap
    Space Complexity: O(V)
    
    Args:
        adjacency_list: AdjacencyList object where each node maps to LinkedList of (distance, neighbor)
        source: source node
        target: target node
    
    Returns:
        tuple: (path list, distance, stats dictionary)
    """
    stats = {
        'nodes_visited': 0,
        'edges_relaxed': 0,
        'heap_operations': 0,
        'algorithm': 'Dijkstra'
    }
    
    # Get all nodes from adjacency list
    all_nodes = list(adjacency_list.keys())
    
    # Initialize distances and predecessors
    dist = {node: float('inf') for node in all_nodes}
    prev = {node: None for node in all_nodes}
    dist[source] = 0
    
    # Custom priority queue
    pq = MinHeap()
    pq.push(0, source)
    stats['heap_operations'] += 1
    
    # Visited set
    visited = set()
    
    while not pq.is_empty():
        # Extract min
        current_dist, current = pq.pop()
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
        
        # Get neighbors from adjacency list (LinkedList)
        neighbors_list = adjacency_list.get(current)
        if neighbors_list is None:
            continue
        
        # Iterate through linked list of neighbors
        current_node = neighbors_list.head
        while current_node is not None:
            # Get the value from the node (adjust attribute name as needed)
            # Try different attribute names based on your LinkedList implementation
            if hasattr(current_node, 'value'):
                edge_weight, neighbor = current_node.value
            elif hasattr(current_node, 'data'):
                edge_weight, neighbor = current_node.data
            else:
                # If neither, assume the node itself is the tuple
                edge_weight, neighbor = current_node
            
            stats['edges_relaxed'] += 1
            
            new_dist = current_dist + edge_weight
            
            if new_dist < dist[neighbor]:
                dist[neighbor] = new_dist
                prev[neighbor] = current
                pq.push(new_dist, neighbor)
                stats['heap_operations'] += 1
            
            current_node = current_node.next
    
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
    if V > 0:
        theoretical_ops = (V + E) * math.log2(V)
        actual_ops = stats['edges_relaxed'] + stats['heap_operations']
        ratio = actual_ops / theoretical_ops if theoretical_ops > 0 else 0
        print(f"\n  Complexity verification:")
        print(f"    Theoretical ops ~ {theoretical_ops:.0f}")
        print(f"    Actual ops: {actual_ops}")
        print(f"    Ratio: {ratio:.3f} (should be ~1 for average case)")