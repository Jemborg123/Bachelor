import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import heapq
import math
from Data.utils import *
import Data.KDtree as KDtree
from Algorithms.ALT import * 

def results(mu,forwardPrev,backwardPrev,forwardVisited,backwardVisited):
    meetNodes = mu[1]
    dist = mu [0]
    path = build_path(meetNodes,forwardPrev,backwardPrev)
    visited = set()
    for v in forwardVisited: visited.add(v)
    for v in backwardVisited: visited.add(v)
    return dist, path, len(visited)

def build_path(meetNodes, forwardPrev, backwardPrev):
    u,v = meetNodes
    left = []; n = u
    while n is not None: left.append(n); n = forwardPrev[n]
    left.reverse()                       # s .. u
    right = []; n = v
    while n is not None: right.append(n); n = backwardPrev[n]
    return left + right  

def bi_dijk_new(graph,source,sink,cost_func,stopCondition=None):
    forwardCostMap = {node: float('inf') for node in graph.nodes()}
    forwardDistMap = {node: float('inf') for node in graph.nodes()}
    forwardPrev = {node: None for node in graph.nodes()}
    forwardCostMap[source] = cost_func(source,'forward')
    forwardDistMap[source] = 0

    queue = MinHeap()
    queue.add((forwardCostMap[source],forwardDistMap[source],source,'forward'))

    forwardVisited = set()
    forwardVisited.add(source)

    backwardCostMap = {node: float('inf') for node in graph.nodes()}
    backwardDistMap = {node: float('inf') for node in graph.nodes()}
    backwardPrev = {node: None for node in graph.nodes()}
    backwardCostMap[sink] = cost_func(sink,'backward')
    backwardDistMap[sink] = 0

    queue.add((backwardCostMap[sink],backwardDistMap[sink],sink,'backward'))

    backwardVisited = set()
    backwardVisited.add(sink)

    mu = (float('inf'),None)

    while len(queue)>0:
        cost,dist,node,direction = queue.extractMin()
        if direction == 'forward':
            costMap = forwardCostMap
            visited = forwardVisited
            distMap = forwardDistMap
            prev = forwardPrev
        elif direction == 'backward':
            visited = backwardVisited
            distMap = backwardDistMap
            costMap = backwardCostMap
            prev = backwardPrev

        if cost > costMap[node]: continue
        if cost >= mu[0] : 
            return results(mu,forwardPrev,backwardPrev,forwardVisited,backwardVisited)
        
        if node not in visited: visited.add(node)

        for neighbour in graph.neighbors(node):
            neighbour_cost = graph.neighborCost(node,neighbour)
            cumDist = dist + neighbour_cost
            cumCost = cumDist + cost_func(neighbour,direction)
            if direction == 'forward':
                if neighbour in backwardVisited:
                    if cumDist+backwardDistMap[neighbour]<mu[0]:
                        mu = cumDist+backwardDistMap[neighbour],(node,neighbour)
                    continue
            if direction == 'backward':
                if neighbour in forwardVisited:
                    if cumDist+forwardDistMap[neighbour]<mu[0]:
                        mu = cumDist+forwardDistMap[neighbour],(neighbour,node)
                    continue
            if cumCost < costMap[neighbour]:
                costMap[neighbour] = cumCost
                distMap[neighbour] = cumDist
                prev[neighbour] = node
                queue.add((cumCost,cumDist,neighbour,direction))
    return distMap, prev, visited

def bi_astar_new(graph,s,t,h):
    cost_func = lambda node,dir : h(node,t) if dir == 'forward' else h(node,s)
    return bi_dijk_new(graph,s,t,cost_func)


from MapVisuals import *
def test_a_list():
    
    ADJACENCY_PATH = "Data/ObbyMap32_pruned.json"
    adjacency_list, success = load_adjacency_list(ADJACENCY_PATH)
    a_graph = adjGraph(adjacency_list)
    a_s,a_t = select_random_nodes_adj(adjacency_list)[0]
    cost_func = lambda x,d :  0
    biCost, biPath,bivisits = bi_dijk_new(a_graph,a_s,a_t,cost_func)
    print("BI")
    print(f"adj cost: {biCost},\n nodes visited: {bivisits},\n adj path: {biPath}")

    uniCost, uniPath, uniVisits = dijk_s_to_t(a_graph,a_s,a_t)
    print("UNI")
    print(f"adj cost: {uniCost},\n nodes visited: {uniVisits},\n adj path: {uniPath}")

    h_adj = lambda p1, p2: adj_euclidean(p1,p2)
    biaCost, biaPath, biaVisits = bi_astar_new(a_graph,a_s,a_t,h_adj)
    
    print("BI astar")
    print(f"adj cost: {biaCost},\n nodes visited: {biaVisits},\n adj path: {biaPath}")

    
    uniaCost, uniaPath, uniaVisits = new_astar(a_graph,a_s,a_t,h_adj)
    print("UNI astar")
    print(f"adj cost: {uniaCost},\n nodes visited: {uniaVisits},\n adj path: {uniaPath}")

    
    a_landmarks = new_select_landmarks(a_graph)
    a_pp = landmark_distances(a_graph,a_landmarks)
    h_adj = lambda p1, p2: landmark_h(p1,p2, a_pp, len(a_landmarks))
    bialtCost, bialtPath, bialtVisits = bi_astar_new(a_graph,a_s,a_t,h_adj)
    
    print("BI ALT")
    print(f"adj cost: {bialtCost},\n nodes visited: {bialtVisits},\n adj path: {bialtPath}")

    
    unialtCost, unialtPath, unialtVisits = new_astar(a_graph,a_s,a_t,h_adj)
    print("UNI ALT")
    print(f"adj cost: {unialtCost},\n nodes visited: {unialtVisits},\n adj path: {uniaPath}")


    create_adj_path_map(adjacency_list, uniPath, uniCost, a_s, a_t, "Maps/adj_UNIdijkstra.html")
    create_adj_path_map(adjacency_list, biPath, biCost, a_s, a_t, "Maps/adj_BIdijkstra.html")
    
    create_adj_path_map(adjacency_list, uniaPath, uniaCost, a_s, a_t, "Maps/adj_UNIastar.html")
    create_adj_path_map(adjacency_list, biaPath, biaCost, a_s, a_t, "Maps/adj_BIastar.html")
    
    create_adj_path_map(adjacency_list, unialtPath, unialtCost, a_s, a_t, "Maps/adj_UNIALT.html")
    create_adj_path_map(adjacency_list, bialtPath, bialtCost, a_s, a_t, "Maps/adj_BIALT.html")

def test_nx():
    import pickle
    GRAPH_FILE = 'Data/Old_Graph_data/walkability_graph.pkl'
    with open(GRAPH_FILE, 'rb') as f:
        G = pickle.load(f)
    nx_s,nx_t = select_random_nodes_nx(G)[0]
    nx_graph = nxGraph(G)
    cost_func = lambda x,d :  0
    biCost, biPath,bivisits = bi_dijk_new(nx_graph,nx_s,nx_t,cost_func)
    
    print("BI")
    print(f"nx cost: {biCost},\n nodes visited: {bivisits},\n nx path: {biPath}")

    
    h_nx = lambda p1, p2: nx_euclidean(p1,p2,G)
    biaCost, biaPath, biaVisits = bi_astar_new(nx_graph,nx_s,nx_t,h_nx)
    
    print("BI astar")
    print(f"nx cost: {biaCost},\n nodes visited: {biaVisits},\n nx path: {biaPath}")

    nx_landmarks = new_select_landmarks(nx_graph)
    nx_pp = landmark_distances(nx_graph,nx_landmarks)
    h_nx = lambda p1, p2: landmark_h(p1,p2, nx_pp, len(nx_landmarks))
    bialtCost, bialtPath, bialtVisits = bi_astar_new(nx_graph,nx_s,nx_t,h_nx)
    
    print("BI ALT")
    print(f"adj cost: {bialtCost},\n nodes visited: {bialtVisits},\n adj path: {bialtPath}")

    create_path_map(G,biPath,biCost,nx_s,nx_t,"nx_BIdijkstra.html")
    create_path_map(G,biaPath,biaCost,nx_s,nx_t,"nx_BIastar.html")
    create_path_map(G,bialtPath,bialtCost,nx_s,nx_t,"nx_BIalt.html")




if __name__ == "__main__":
    # test_a_list()
    test_nx()
