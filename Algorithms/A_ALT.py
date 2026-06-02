"""
ALT (A* with Landmarks and Triangle Inequality) for AdjacencyList.
No external libraries except math and heapq.
"""

import math
import heapq
import random
import time

def select_landmarks_adj(adj_list, num_landmarks=16, strategy='perimeter'):
    """
    Select landmarks evenly spaced around the perimeter of DTU campus.
    
    Args:
        adj_list: AdjacencyList object
        num_landmarks: Number of landmarks to select
        strategy: 'perimeter' (ignored, kept for compatibility)
    
    Returns:
        List of landmark nodes (tuples of coordinates)
    """
    nodes = list(adj_list.keys())
    num_landmarks = min(num_landmarks, len(nodes))
    
    # Find bounding box of all nodes
    min_x = min_y = float('inf')
    max_x = max_y = float('-inf')
    
    for node in nodes:
        x, y = node[0], node[1]
        min_x = min(min_x, x)
        min_y = min(min_y, y)
        max_x = max(max_x, x)
        max_y = max(max_y, y)
    
    print(f"  Campus bounding box: x=[{min_x:.0f}, {max_x:.0f}], y=[{min_y:.0f}, {max_y:.0f}]")
    
    # Generate perimeter points (corners + evenly spaced along edges)
    perimeter_points = []
    
    # Number of points per side (roughly equal distribution)
    points_per_side = max(1, num_landmarks // 4)
    
    # Top edge (y = max_y)
    for i in range(points_per_side):
        t = i / (points_per_side - 1) if points_per_side > 1 else 0.5
        x = min_x + t * (max_x - min_x)
        perimeter_points.append((x, max_y))
    
    # Right edge (x = max_x) - skip first point (top-right corner already added)
    for i in range(1, points_per_side):
        t = i / (points_per_side - 1) if points_per_side > 1 else 0.5
        y = max_y - t * (max_y - min_y)
        perimeter_points.append((max_x, y))
    
    # Bottom edge (y = min_y) - skip first point (bottom-right corner already added)
    for i in range(1, points_per_side):
        t = i / (points_per_side - 1) if points_per_side > 1 else 0.5
        x = max_x - t * (max_x - min_x)
        perimeter_points.append((x, min_y))
    
    # Left edge (x = min_x) - skip first and last points (corners already added)
    for i in range(1, points_per_side - 1):
        t = i / (points_per_side - 1) if points_per_side > 1 else 0.5
        y = min_y + t * (max_y - min_y)
        perimeter_points.append((min_x, y))
    
    # Trim to exact number
    perimeter_points = perimeter_points[:num_landmarks]
    
    # Find closest actual nodes to these perimeter points
    landmark_nodes = []
    for px, py in perimeter_points:
        # Find node with minimum Euclidean distance to target point
        closest_node = min(nodes, key=lambda n: (n[0] - px)**2 + (n[1] - py)**2)
        if closest_node not in landmark_nodes:
            landmark_nodes.append(closest_node)
    
    # If we need more landmarks, add the farthest nodes from existing landmarks
    if len(landmark_nodes) < num_landmarks:
        remaining = [n for n in nodes if n not in landmark_nodes]
        # Add remaining nodes in order of distance from existing landmarks
        while len(landmark_nodes) < num_landmarks and remaining:
            farthest = max(remaining, key=lambda n: min((n[0] - lm[0])**2 + (n[1] - lm[1])**2 for lm in landmark_nodes))
            landmark_nodes.append(farthest)
            remaining.remove(farthest)
    
    print(f"  Selected {len(landmark_nodes)} perimeter landmarks")
    return landmark_nodes[:num_landmarks]


def precompute_landmark_distances_adj(adj_list, landmarks, max_distance=2000):
    """
    Precompute distances from all nodes to/from all landmarks.
    Uses limited Dijkstra with radius limit.
    
    Returns:
        dist_to: dict[node][landmark] = distance
        dist_from: dict[landmark][node] = distance
    """
    print(f"  Precomputing distances for {len(landmarks)} landmarks (radius: {max_distance}m)...")
    start_time = time.time()
    
    # Initialize dictionaries
    dist_to = {}
    dist_from = {lm: {} for lm in landmarks}
    
    # For all nodes, create empty dict
    for node in adj_list.keys():
        dist_to[node] = {}
    
    for i, landmark in enumerate(landmarks):
        if i % 4 == 0 and i > 0:
            elapsed = time.time() - start_time
            print(f"    Progress: {i}/{len(landmarks)} landmarks ({elapsed:.1f}s elapsed)")
        
        # Limited Dijkstra from landmark
        dist = {node: float('inf') for node in adj_list.keys()}
        dist[landmark] = 0
        pq = [(0, landmark)]
        
        while pq:
            d, current = heapq.heappop(pq)
            
            if d > max_distance:
                continue
            if d > dist[current]:
                continue
            
            # Store distance
            dist_from[landmark][current] = d
            dist_to[current][landmark] = d
            
            # Explore neighbors
            neighbors_list = adj_list.neighbors(current)
            if neighbors_list:
                current_node = neighbors_list.head
                while current_node:
                    if hasattr(current_node, 'value'):
                        weight, neighbor = current_node.value
                    else:
                        weight, neighbor = current_node
                    
                    new_d = d + weight
                    
                    if new_d <= max_distance and new_d < dist.get(neighbor, float('inf')):
                        dist[neighbor] = new_d
                        heapq.heappush(pq, (new_d, neighbor))
                    
                    current_node = current_node.next
    
    total_time = time.time() - start_time
    print(f"  ✅ Preprocessing completed in {total_time:.1f} seconds")
    
    return dist_to, dist_from


def alt_heuristic(node, target, landmarks, dist_to, dist_from):
    """
    ALT heuristic using triangle inequality.
    """
    h_max = 0
    
    for lm in landmarks:
        # Forward triangle: |d(v,L) - d(t,L)|
        if lm in dist_to.get(node, {}) and lm in dist_to.get(target, {}):
            h1 = abs(dist_to[node][lm] - dist_to[target][lm])
            if h1 > h_max:
                h_max = h1
        
        # Backward triangle: |d(L,t) - d(L,v)|
        if lm in dist_from and node in dist_from[lm] and target in dist_from[lm]:
            h2 = abs(dist_from[lm][target] - dist_from[lm][node])
            if h2 > h_max:
                h_max = h2
    
    return h_max


def alt(adj_list, source, target, landmarks=None, dist_to=None, dist_from=None, 
        num_landmarks=16, strategy='random', max_distance=2000):
    """
    ALT algorithm: A* with landmark heuristic.
    
    If landmarks/distances not provided, will compute them.
    """
    stats = {
        'nodes_visited': 0,
        'edges_relaxed': 0,
        'heap_operations': 0,
        'algorithm': 'ALT'
    }
    
    # Preprocess if needed
    if landmarks is None or dist_to is None or dist_from is None:
        print("  🔧 Preprocessing landmarks...")
        landmarks = select_landmarks_adj(adj_list, num_landmarks, strategy)
        print(f"  Selected {len(landmarks)} landmarks using '{strategy}' strategy")
        dist_to, dist_from = precompute_landmark_distances_adj(adj_list, landmarks, max_distance)
        stats['preprocessing_done'] = True
    
    # Heuristic function using landmarks
    def heuristic(node):
        return alt_heuristic(node, target, landmarks, dist_to, dist_from)
    
    # A* search
    all_nodes = list(adj_list.keys())
    
    g_score = {node: float('inf') for node in all_nodes}
    f_score = {node: float('inf') for node in all_nodes}
    came_from = {node: None for node in all_nodes}
    
    g_score[source] = 0
    f_score[source] = heuristic(source)
    
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
        
        # Explore neighbors
        neighbors_list = adj_list.neighbors(current)
        if neighbors_list is None:
            continue
        
        current_node = neighbors_list.head
        while current_node:
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