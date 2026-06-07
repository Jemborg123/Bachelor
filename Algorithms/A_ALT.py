"""
ALT (A* with Landmarks and Triangle Inequality) for AdjacencyList.
Reuses A* from A_AStar for the actual search.
"""

import math
import heapq
import random
import time
from .A_AStar import astar

def select_landmarks_adj(adj_list, num_landmarks=16, strategy='perimeter'):
    """
    Select landmarks evenly spaced around the perimeter of DTU campus.
    """
    nodes = list(adj_list.keys())
    num_landmarks = min(num_landmarks, len(nodes))
    
    # Find bounding box
    min_x = min_y = float('inf')
    max_x = max_y = float('-inf')
    
    for node in nodes:
        x, y = node[0], node[1]
        min_x = min(min_x, x)
        min_y = min(min_y, y)
        max_x = max(max_x, x)
        max_y = max(max_y, y)
    
    print(f"  Campus bounding box: x=[{min_x:.0f}, {max_x:.0f}], y=[{min_y:.0f}, {max_y:.0f}]")
    
    # Generate perimeter points
    perimeter_points = []
    points_per_side = max(1, num_landmarks // 4)
    
    # Top edge
    for i in range(points_per_side):
        t = i / (points_per_side - 1) if points_per_side > 1 else 0.5
        x = min_x + t * (max_x - min_x)
        perimeter_points.append((x, max_y))
    
    # Right edge
    for i in range(1, points_per_side):
        t = i / (points_per_side - 1) if points_per_side > 1 else 0.5
        y = max_y - t * (max_y - min_y)
        perimeter_points.append((max_x, y))
    
    # Bottom edge
    for i in range(1, points_per_side):
        t = i / (points_per_side - 1) if points_per_side > 1 else 0.5
        x = max_x - t * (max_x - min_x)
        perimeter_points.append((x, min_y))
    
    # Left edge
    for i in range(1, points_per_side - 1):
        t = i / (points_per_side - 1) if points_per_side > 1 else 0.5
        y = min_y + t * (max_y - min_y)
        perimeter_points.append((min_x, y))
    
    perimeter_points = perimeter_points[:num_landmarks]
    
    # Find closest actual nodes
    landmark_nodes = []
    for px, py in perimeter_points:
        closest = min(nodes, key=lambda n: (n[0] - px)**2 + (n[1] - py)**2)
        if closest not in landmark_nodes:
            landmark_nodes.append(closest)
    
    print(f"  Selected {len(landmark_nodes)} perimeter landmarks")
    return landmark_nodes[:num_landmarks]


def precompute_landmark_distances_adj(adj_list, landmarks, max_distance=5000):
    """
    Precompute distances from all nodes to/from all landmarks.
    """
    print(f"  Precomputing distances for {len(landmarks)} landmarks (radius: {max_distance}m)...")
    start_time = time.time()
    
    dist_to = {}
    dist_from = {lm: {} for lm in landmarks}
    
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
            
            dist_from[landmark][current] = d
            dist_to[current][landmark] = d
            
            neighbors = adj_list.neighbors(current)
            if neighbors:
                curr = neighbors.head
                while curr:
                    weight, neighbor = curr.value if hasattr(curr, 'value') else curr
                    new_d = d + weight
                    
                    if new_d <= max_distance and new_d < dist.get(neighbor, float('inf')):
                        dist[neighbor] = new_d
                        heapq.heappush(pq, (new_d, neighbor))
                    curr = curr.next
    
    total_time = time.time() - start_time
    print(f"  ✅ Preprocessing completed in {total_time:.1f} seconds")
    
    return dist_to, dist_from


def alt_heuristic(node, target, landmarks, dist_to, dist_from):
    """
    ALT heuristic using triangle inequality.
    """
    h_max = 0
    
    for lm in landmarks:
        # Forward triangle
        d_v_lm = dist_to.get(node, {}).get(lm)
        d_t_lm = dist_to.get(target, {}).get(lm)
        if d_v_lm is not None and d_t_lm is not None:
            h1 = abs(d_v_lm - d_t_lm)
            if h1 > h_max:
                h_max = h1
        
        # Backward triangle
        d_lm_v = dist_from.get(lm, {}).get(node)
        d_lm_t = dist_from.get(lm, {}).get(target)
        if d_lm_v is not None and d_lm_t is not None:
            h2 = abs(d_lm_t - d_lm_v)
            if h2 > h_max:
                h_max = h2
    
    return h_max


def alt(adj_list, source, target, landmarks=None, dist_to=None, dist_from=None, 
        num_landmarks=16, strategy='perimeter', max_distance=5000):
    """
    ALT algorithm: A* with landmark heuristic.
    Reuses A* from A_AStar.
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

    debug_count = 0
    
    # Create ALT heuristic function for A*
    def heuristic(node):
        # return alt_heuristic(node, target, landmarks, dist_to, dist_from)
        nonlocal debug_count
        h = alt_heuristic(node, target, landmarks, dist_to, dist_from)
        
        if debug_count < 5:
            print(f"    [DEBUG ALT] Heuristic for node {node[:2]}...: {h:.1f}")
            debug_count += 1
        
        return h
    # 👈 REUSE A* from A_AStar!
    print(f"  Running A* with ALT heuristic...")
    path, cost, stats_astar = astar(adj_list, source, target, heuristic=heuristic)
    
    # Merge stats
    stats['nodes_visited'] = stats_astar['nodes_visited']
    stats['edges_relaxed'] = stats_astar['edges_relaxed']
    stats['heap_operations'] = stats_astar['heap_operations']
    
    return path, cost, stats