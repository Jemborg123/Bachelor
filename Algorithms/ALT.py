"""
ALT (A* with Landmarks and Triangle Inequality) algorithm implementation.
"""
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import math
import heapq
import random
import time
from Algorithms.AStar import *
import Data.KDtree as KDtree

def landmark_distances(graph, landmarks):
    
    print("Calculating landmark distances for"+str(graph))
    l_distances = {node:[] for node in graph.nodes()}
    for landmark in landmarks:
        cost_func = lambda node: dijk_cost(node)
        distMap,_,_= dijk_new(graph,landmark,cost_func)
        for node, dist in distMap.items():
            l_distances.get(node).append(dist)
    return l_distances

def landmark_h(p1,p2,landmark_dists,num_landmarks=16):
    maxDist = 0
    for i in range(num_landmarks):
        p1_dist = landmark_dists.get(p1)[i]
        p2_dist = landmark_dists.get(p2)[i]
        triangle_dist = abs(p1_dist-p2_dist)
        if triangle_dist>maxDist: maxDist = triangle_dist
    return maxDist

def new_select_landmarks(graph, num_landmarks=16):
    print("Generating landmarks for"+str(graph))
    nodes = graph.nodes()
    
    min_x = min_y = float('inf')
    max_x = max_y = float('-inf')

    for node in nodes:
        x = graph.getX(node)
        y = graph.getY(node)
        min_x = min(min_x, x)
        min_y = min(min_y, y)
        max_x = max(max_x, x)
        max_y = max(max_y, y)
    
    # Generate perimeter points (corners + evenly spaced along edges)
    perimeter_points = []
    
    # Top edge (y = max_y)
    for i in range(num_landmarks // 4 + 1):
        t = i / (num_landmarks // 4)
        x = min_x + t * (max_x - min_x)
        perimeter_points.append((x, max_y))

    # Right edge (x = max_x)
    for i in range(1, num_landmarks // 4 + 1):
        t = i / (num_landmarks // 4)
        y = max_y - t * (max_y - min_y)
        perimeter_points.append((max_x, y))
    
    # Bottom edge (y = min_y)
    for i in range(1, num_landmarks // 4 + 1):
        t = i / (num_landmarks // 4)
        x = max_x - t * (max_x - min_x)
        perimeter_points.append((x, min_y))
    
    # Left edge (x = min_x)
    for i in range(1, num_landmarks // 4):
        t = i / (num_landmarks // 4)
        y = min_y + t * (max_y - min_y)
        perimeter_points.append((min_x, y))
    
    # Trim to exact number
    perimeter_points = perimeter_points[:num_landmarks]
    
    # Find closest actual nodes
    landmark_nodes = []
    tree = KDtree.buildKDtree(graph.getPoints())

    for point in perimeter_points:
        closest = graph.closest(tree,point)
        if closest not in landmark_nodes:
            landmark_nodes.append(closest)
    return landmark_nodes

if __name__ == "__main__":
    import pickle
    GRAPH_FILE = 'Data/Old_Graph_data/walkability_graph.pkl'
    with open(GRAPH_FILE, 'rb') as f:
        G = pickle.load(f)
    nx_s,nx_t = select_random_nodes_nx(G)[0]
    nx_graph = nxGraph(G)
    nx_landmarks = new_select_landmarks(nx_graph)
    nx_pp = landmark_distances(nx_graph,nx_landmarks)
    savePointsDataToFile(nx_pp, "Data/nx_graph_landmark_distances.json")

    ADJACENCY_PATH = "Data/ObbyMap32_pruned.json"
    adjacency_list, success = load_adjacency_list(ADJACENCY_PATH)
    a_s,a_t = select_random_nodes_adj(adjacency_list)[0]
    a_graph = adjGraph(adjacency_list)
    a_landmarks = new_select_landmarks(a_graph)
    a_pp = landmark_distances(a_graph,a_landmarks)
    save_a_pp = {}
    for i, (key, val) in enumerate(a_pp.items()):
        save_a_pp[i] = key,val
    savePointsDataToFile(save_a_pp, "Data/ObbyMap32_pruned_graph_landmark_distances.json")



    h_nx  = lambda p1, p2: landmark_h(p1,p2, nx_pp, len(nx_landmarks))
    h_adj = lambda p1, p2: landmark_h(p1,p2, a_pp, len(a_landmarks))

    newCost, newPath,visits = new_astar(nx_graph,nx_s,nx_t,h_nx)

    print(f"new cost: {newCost}")
    
    print(f"new path: {newPath},\n nodes visited: {visits}")

    
    newCost, newPath,visits = new_astar(a_graph,a_s,a_t,h_adj)
    
    print(f"adj cost: {newCost},\n nodes visited: {visits},\n adj path: {newPath}")

def select_landmarks(graph, num_landmarks=16, strategy='perimeter'):
    """
    Select landmarks evenly spaced around the perimeter of DTU campus.
    """
    nodes = list(graph.nodes())
    
    # Check if coordinates are available
    if 'x' not in graph.nodes[nodes[0]]:
        print("  ⚠️ No coordinates found, using random selection")
        return random.sample(nodes, min(num_landmarks, len(nodes)))
    
    # Find bounding box
    min_x = min_y = float('inf')
    max_x = max_y = float('-inf')
    
    for node in nodes:
        x = graph.nodes[node].get('x', 0)
        y = graph.nodes[node].get('y', 0)
        min_x = min(min_x, x)
        min_y = min(min_y, y)
        max_x = max(max_x, x)
        max_y = max(max_y, y)
    
    print(f"  Campus bounding box: ({min_x:.0f}, {min_y:.0f}) to ({max_x:.0f}, {max_y:.0f})")
    
    # Generate perimeter points (corners + evenly spaced along edges)
    perimeter_points = []
    
    # Top edge (y = max_y)
    for i in range(num_landmarks // 4 + 1):
        t = i / (num_landmarks // 4)
        x = min_x + t * (max_x - min_x)
        perimeter_points.append((x, max_y))
    
    # Right edge (x = max_x)
    for i in range(1, num_landmarks // 4 + 1):
        t = i / (num_landmarks // 4)
        y = max_y - t * (max_y - min_y)
        perimeter_points.append((max_x, y))
    
    # Bottom edge (y = min_y)
    for i in range(1, num_landmarks // 4 + 1):
        t = i / (num_landmarks // 4)
        x = max_x - t * (max_x - min_x)
        perimeter_points.append((x, min_y))
    
    # Left edge (x = min_x)
    for i in range(1, num_landmarks // 4):
        t = i / (num_landmarks // 4)
        y = min_y + t * (max_y - min_y)
        perimeter_points.append((min_x, y))
    
    # Trim to exact number
    perimeter_points = perimeter_points[:num_landmarks]
    
    # Find closest actual nodes
    landmark_nodes = []
    for px, py in perimeter_points:
        closest = min(nodes, key=lambda n: (graph.nodes[n]['x'] - px)**2 + (graph.nodes[n]['y'] - py)**2)
        if closest not in landmark_nodes:
            landmark_nodes.append(closest)
    
    print(f"  Selected {len(landmark_nodes)} perimeter landmarks")
    return landmark_nodes[:num_landmarks]


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