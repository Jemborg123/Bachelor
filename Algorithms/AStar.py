
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import math
import heapq
from Algorithms.Dijkstra import *


def adj_euclidean(p1,p2):
    h_adj = euclideanDistance(p1, p2)
    return h_adj

def nx_euclidean(p1,p2,G):
    h_nx  =  euclideanDistance(G.nodes[p1]['pos'], G.nodes[p2]['pos'])
    return h_nx

def new_astar(graph,s,t,h):
    cost_func = lambda node : h(node,t)
    stopCondition = lambda node : target_reached(node,t)
    distMap, prev, visited = dijk_new(graph,s,cost_func,stopCondition)
    return distMap[t], path_to_target(prev,t,[]), len(visited)




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

if __name__ == "__main__":
    import pickle
    GRAPH_FILE = 'Data/Old_Graph_data/walkability_graph.pkl'
    with open(GRAPH_FILE, 'rb') as f:
        G = pickle.load(f)
    nx_s,nx_t = select_random_nodes_nx(G)[0]
    nx_graph = nxGraph(G)
    h_nx  = lambda p1, p2: nx_euclidean(p1,p2,G)
    h_adj = lambda p1, p2: adj_euclidean(p1,p2)
    newCost, newPath,visits = new_astar(nx_graph,nx_s,nx_t,h_nx)
    oldPath, oldCost,_ = astar(G,nx_s,nx_t)

    print(f"new cost: {newCost}, old cost: {oldCost}")
    
    print(f"new path: {newPath},\n old path: {oldPath}\n nodes visited: {visits}")

    ADJACENCY_PATH = "Data/ObbyMap32_pruned.json"
    adjacency_list, success = load_adjacency_list(ADJACENCY_PATH)
    a_graph = adjGraph(adjacency_list)
    a_s,a_t = select_random_nodes_adj(adjacency_list)[0]
    newCost, newPath,visits = new_astar(a_graph,a_s,a_t,h_adj)
    
    print(f"adj cost: {newCost},\n nodes visited: {visits},\n adj path: {newPath}")