
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
    

    print(f"new cost: {newCost},new path: {newPath}\n nodes visited: {visits}")
    

    ADJACENCY_PATH = "Data/ObbyMap32_pruned.json"
    adjacency_list, success = load_adjacency_list(ADJACENCY_PATH)
    a_graph = adjGraph(adjacency_list)
    a_s,a_t = select_random_nodes_adj(adjacency_list)[0]
    newCost, newPath,visits = new_astar(a_graph,a_s,a_t,h_adj)
    
    print(f"adj cost: {newCost},\n nodes visited: {visits},\n adj path: {newPath}")