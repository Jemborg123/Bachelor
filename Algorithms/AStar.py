import math
import heapq

def astar(graph, source, target, weight='weight', heuristic=None):
    """A* search algorithm from scratch."""
    stats = {
        'nodes_visited': 0,
        'edges_relaxed': 0,
        'heap_operations': 0,
        'algorithm': 'A*'
    }
    
    # Default heuristic: Euclidean distance
    if heuristic is None:
        def heuristic(node):
            if ('x' in graph.nodes[node] and 'x' in graph.nodes[target] and
                'y' in graph.nodes[node] and 'y' in graph.nodes[target]):
                dx = graph.nodes[node]['x'] - graph.nodes[target]['x']
                dy = graph.nodes[node]['y'] - graph.nodes[target]['y']
                return math.sqrt(dx*dx + dy*dy)
            return 0
    
    # Initialize
    g_score = {node: float('inf') for node in graph.nodes()}
    f_score = {node: float('inf') for node in graph.nodes()}
    came_from = {node: None for node in graph.nodes()}
    
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
        
        for neighbor in graph.neighbors(current):
            if neighbor in closed_set:
                continue
            
            edge_weight = graph[current][neighbor].get(weight, 1)
            stats['edges_relaxed'] += 1
            
            tentative_g = g_score[current] + edge_weight
            
            if tentative_g < g_score[neighbor]:
                came_from[neighbor] = current
                g_score[neighbor] = tentative_g
                f_score[neighbor] = tentative_g + heuristic(neighbor)
                heapq.heappush(open_set, (f_score[neighbor], neighbor))
                stats['heap_operations'] += 1
    
    # Reconstruct path
    path = []
    if g_score[target] < float('inf'):
        node = target
        while node is not None:
            path.append(node)
            node = came_from[node]
        path.reverse()
    
    return path, g_score[target], stats

def euclidean_heuristic(node, target, graph):
    """Euclidean distance heuristic."""
    if ('x' in graph.nodes[node] and 'x' in graph.nodes[target] and
        'y' in graph.nodes[node] and 'y' in graph.nodes[target]):
        dx = graph.nodes[node]['x'] - graph.nodes[target]['x']
        dy = graph.nodes[node]['y'] - graph.nodes[target]['y']
        return math.sqrt(dx*dx + dy*dy)
    return 0


def manhattan_heuristic(node, target, graph):
    """Manhattan distance heuristic."""
    if ('x' in graph.nodes[node] and 'x' in graph.nodes[target] and
        'y' in graph.nodes[node] and 'y' in graph.nodes[target]):
        dx = abs(graph.nodes[node]['x'] - graph.nodes[target]['x'])
        dy = abs(graph.nodes[node]['y'] - graph.nodes[target]['y'])
        return dx + dy
    return 0


def zero_heuristic(node, target, graph):
    """Zero heuristic - makes A* behave like Dijkstra."""
    return 0