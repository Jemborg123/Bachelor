"""
ALT (A* with Landmarks and Triangle Inequality) algorithm implementation.
"""

import math
import heapq
import random
import time

def select_landmarks(graph, num_landmarks=16, strategy='farthest'):
    """
    Select landmarks using farthest-first strategy.
    
    Args:
        graph: NetworkX graph
        num_landmarks: Number of landmarks to select
        strategy: 'random', 'farthest', or 'perimeter'
    
    Returns:
        List of landmark node IDs
    """
    nodes = list(graph.nodes())
    
    if strategy == 'random':
        return random.sample(nodes, min(num_landmarks, len(nodes)))
    
    elif strategy == 'farthest':
        if len(nodes) == 0:
            return []
        
        # Start with random node
        landmarks = [random.choice(nodes)]
        
        while len(landmarks) < num_landmarks and len(landmarks) < len(nodes):
            max_min_dist = -1
            farthest_node = None
            
            # For each candidate node
            for node in nodes:
                if node in landmarks:
                    continue
                
                # Find minimum distance to any landmark
                min_dist = float('inf')
                for landmark in landmarks:
                    # Run Dijkstra to get exact distance
                    dist = _dijkstra_distance(graph, node, landmark)
                    if dist < min_dist:
                        min_dist = dist
                
                # Keep node with largest minimum distance
                if min_dist > max_min_dist:
                    max_min_dist = min_dist
                    farthest_node = node
            
            if farthest_node is not None:
                landmarks.append(farthest_node)
            else:
                break
        
        return landmarks
    
    elif strategy == 'perimeter':
        # Select nodes at extremes if coordinates available
        if 'x' not in graph.nodes[list(graph.nodes())[0]]:
            return select_landmarks(graph, num_landmarks, 'farthest')
        
        # Find min/max coordinates
        min_x = min_y = float('inf')
        max_x = max_y = float('-inf')
        
        for node in nodes:
            x = graph.nodes[node].get('x', 0)
            y = graph.nodes[node].get('y', 0)
            min_x = min(min_x, x)
            min_y = min(min_y, y)
            max_x = max(max_x, x)
            max_y = max(max_y, y)
        
        # Find nodes near corners
        landmarks = []
        targets = [(min_x, min_y), (min_x, max_y), (max_x, min_y), (max_x, max_y)]
        
        for tx, ty in targets:
            best_node = None
            best_dist = float('inf')
            for node in nodes:
                x = graph.nodes[node].get('x', 0)
                y = graph.nodes[node].get('y', 0)
                dist = math.sqrt((x - tx)**2 + (y - ty)**2)
                if dist < best_dist:
                    best_dist = dist
                    best_node = node
            if best_node and best_node not in landmarks:
                landmarks.append(best_node)
        
        # Fill remaining with farthest
        while len(landmarks) < num_landmarks:
            remaining = [n for n in nodes if n not in landmarks]
            if not remaining:
                break
            
            # Find farthest from current landmarks
            farthest = None
            max_dist = -1
            for node in remaining:
                min_dist = float('inf')
                for lm in landmarks:
                    dx = graph.nodes[node].get('x', 0) - graph.nodes[lm].get('x', 0)
                    dy = graph.nodes[node].get('y', 0) - graph.nodes[lm].get('y', 0)
                    dist = math.sqrt(dx*dx + dy*dy)
                    if dist < min_dist:
                        min_dist = dist
                if min_dist > max_dist:
                    max_dist = min_dist
                    farthest = node
            
            if farthest:
                landmarks.append(farthest)
            else:
                break
        
        return landmarks
    
    return []


def _dijkstra_distance(graph, source, target):
    """Simple Dijkstra to get exact distance between two nodes."""
    dist = {node: float('inf') for node in graph.nodes()}
    dist[source] = 0
    pq = [(0, source)]
    visited = set()
    
    while pq:
        d, current = heapq.heappop(pq)
        if current in visited:
            continue
        visited.add(current)
        
        if current == target:
            return d
        
        for neighbor in graph.neighbors(current):
            weight = graph[current][neighbor].get('weight', 1)
            new_d = d + weight
            if new_d < dist[neighbor]:
                dist[neighbor] = new_d
                heapq.heappush(pq, (new_d, neighbor))
    
    return dist[target]


def precompute_landmark_distances(graph, landmarks, max_distance=2000):
    """
    Precompute distances with radius limit for speed.
    """
    print(f"  Precomputing distances for {len(landmarks)} landmarks (radius: {max_distance}m)...")
    start_time = time.time()
    
    try:
        # Initialize with infinity for all nodes
        print("    Initializing data structures...")
        dist_to = {node: {lm: float('inf') for lm in landmarks} for node in graph.nodes()}
        dist_from = {lm: {node: float('inf') for node in graph.nodes()} for lm in landmarks}
        print(f"    Initialized {len(dist_to)} nodes and {len(dist_from)} landmarks")
        
        for i, landmark in enumerate(landmarks):
            print(f"    Processing landmark {i+1}/{len(landmarks)} (node {landmark})...")
            
            # Limited Dijkstra from landmark
            dist = {node: float('inf') for node in graph.nodes()}
            dist[landmark] = 0
            pq = [(0, landmark)]
            nodes_processed = 0
            
            while pq:
                d, current = heapq.heappop(pq)
                
                # Stop if beyond radius
                if d > max_distance:
                    continue
                    
                # Skip if we already have a better distance
                if d > dist[current]:
                    continue
                
                # Store distance
                dist_from[landmark][current] = d
                dist_to[current][landmark] = d
                nodes_processed += 1
                
                # Explore neighbors
                for neighbor in graph.neighbors(current):
                    try:
                        weight = graph[current][neighbor].get('weight', 1)
                        new_d = d + weight
                        
                        # Only enqueue if within radius and better than current best
                        if new_d <= max_distance and new_d < dist.get(neighbor, float('inf')):
                            dist[neighbor] = new_d
                            heapq.heappush(pq, (new_d, neighbor))
                    except Exception as e:
                        print(f"      Error at neighbor {neighbor}: {e}")
                        raise
            
            print(f"      Processed {nodes_processed} nodes for landmark {landmark}")
            
            if i % 4 == 3:  # Progress update every 4 landmarks
                elapsed = time.time() - start_time
                print(f"    Progress: {i+1}/{len(landmarks)} landmarks ({elapsed:.1f}s elapsed)")
        
        total_time = time.time() - start_time
        print(f"  ✅ Preprocessing completed in {total_time:.1f} seconds")
        
        return dist_to, dist_from
        
    except Exception as e:
        print(f"  ❌ Error during preprocessing: {e}")
        import traceback
        traceback.print_exc()
        raise
    

def alt_heuristic(node, target, landmarks, dist_to, dist_from):
    """
    ALT heuristic using triangle inequality.
    
    h(v) = max over landmarks L of:
        |dist(v, L) - dist(t, L)|
        |dist(L, t) - dist(L, v)|
    """
    h_max = 0
    
    for lm in landmarks:
        # Forward triangle: |d(v,L) - d(t,L)|
        if lm in dist_to[node] and lm in dist_to[target]:
            h1 = abs(dist_to[node][lm] - dist_to[target][lm])
            if h1 > h_max:
                h_max = h1
        
        # Backward triangle: |d(L,t) - d(L,v)|
        if lm in dist_from and node in dist_from[lm] and target in dist_from[lm]:
            h2 = abs(dist_from[lm][target] - dist_from[lm][node])
            if h2 > h_max:
                h_max = h2
    
    return h_max


def alt(graph, source, target, weight='weight', landmarks=None, dist_to=None, dist_from=None):
    """
    ALT algorithm: A* with landmark heuristic.
    
    If landmarks/distances not provided, will compute on-the-fly (not recommended).
    """
    stats = {
        'nodes_visited': 0,
        'edges_relaxed': 0,
        'heap_operations': 0,
        'algorithm': 'ALT'
    }
    
    # If no precomputed data, compute now (slow - for testing only)
    if landmarks is None or dist_to is None or dist_from is None:
        print("  ⚠️  No precomputed landmarks - selecting 16 on-the-fly")
        landmarks = select_landmarks(graph, num_landmarks=16)
        dist_to, dist_from = precompute_landmark_distances(graph, landmarks)
        stats['preprocessing_done'] = True
    
    # Heuristic function using landmarks
    def heuristic(node):
        return alt_heuristic(node, target, landmarks, dist_to, dist_from)
    
    # Standard A* with custom heuristic
    g_score = {node: float('inf') for node in graph.nodes()}
    f_score = {node: float('inf') for node in graph.nodes()}
    came_from = {node: None for node in graph.nodes()}
    
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


def alt_with_preprocessing(graph, source, target, num_landmarks=16, strategy='farthest'):
    """
    ALT with full preprocessing (recommended for multiple queries).
    """
    # Select landmarks
    landmarks = select_landmarks(graph, num_landmarks, strategy)
    print(f"  Selected {len(landmarks)} landmarks using '{strategy}' strategy")
    
    # Precompute distances
    dist_to, dist_from = precompute_landmark_distances(graph, landmarks)
    
    # Run ALT
    return alt(graph, source, target, landmarks=landmarks, dist_to=dist_to, dist_from=dist_from)