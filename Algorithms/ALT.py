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
