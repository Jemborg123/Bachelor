"""
Dijkstra's algorithm implementation with complexity analysis.
"""
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import heapq
import math
from Data.utils import *
import Data.KDtree as KDtree

class nxGraph:
    def __init__(self,G):
        self.G = G
        self.pos_to_node = {data['pos']: n for n, data in G.nodes(data=True)}

    def __str__(self):
        return "NX GRAPH"
    
    def nodes(self):
        return self.G.nodes()
    
    def neighbors(self,node):
        return self.G.neighbors(node)
    
    def neighborCost(self,node,neighbor):
        return self.G[node][neighbor].get('weight', 1)
    
    def getX(self,node):
        x = self.G.nodes[node].get('x', 0)
        return x

    def getY(self,node):
        y = self.G.nodes[node].get('y', 0)
        return y
    
    def getPoints(self):
        points = [data['pos'] for _, data in self.G.nodes(data=True)]
        return points
    
    def closest(self,tree,point):
        heap = KDtree.KNN_KDtree(tree,point,1)
        _,closest = heap.extractMax()
        return self.pos_to_node[closest]

    
class adjGraph:
    def __init__(self,adj_list:AdjacencyList):
        self.adj_list = adj_list

    def __str__(self):
        return "ADJACENCY LIST GRAPH"

    def nodes(self):
        return self.adj_list.keys()

    def neighbors(self,node):
        neighbors = [n for _,n in self.adj_list.neighbors(node).asList()]
        return neighbors
    
    def neighborCost(self,node,neighbor):
        neighbors = self.adj_list.neighbors(node)
        for i in range(len(neighbors)):
            cost,NodeNeighbor =neighbors.get(i)
            if neighbor == NodeNeighbor: return cost

    def getX(self,node):
        return node[0]
    
    def getY(self,node):
        return node[1]
    
    def getPoints(self):
        return self.adj_list.keys()
    
    def closest(self,tree,point):
        heap = KDtree.KNN_KDtree(tree,point,1)
        _,closest = heap.extractMax()
        return closest

def test_astar(graph,s,t,h):
    cost_func = lambda node : h(node,t)
    stopCondition = lambda node : target_reached(node,t)
    costMap, prevArr, visited = dijk_new(graph,s,cost_func,stopCondition)
    return costMap[t], path_to_target(prevArr,t,[]), len(visited)

def dijk_cost(_):
        return 0
def target_reached(node,t):
    return node == t
def dijk_s_to_t(graph,s,t):
    cost_func = lambda node: dijk_cost(node)
    stopCondition = lambda node: target_reached(node,t)
    costMap, prevArr,visited = dijk_new(graph,s,cost_func,stopCondition)
    return costMap[t], path_to_target(prevArr,t,[]), len(visited)

def path_to_target(prev, x,path=[]):
    path.append(x)
    y = prev[x]
    if y is None: 
        path.reverse()
        return path
    return path_to_target(prev,y,path)


def dijk_new(graph,source,cost_func,stopCondition=None):
    costMap = {node: float('inf') for node in graph.nodes()}
    distMap = {node: float('inf') for node in graph.nodes()}
    prev = {node: None for node in graph.nodes()}
    costMap[source] = cost_func(source)
    distMap[source] = 0

    queue = MinHeap()
    queue.add((costMap[source],distMap[source],source))

    visited = set()
    visited.add(source)

    while len(queue)>0:
        cost,dist,node = queue.extractMin()

        if cost > costMap[node]: continue
        
        if node not in visited: visited.add(node)

        if stopCondition is not None and stopCondition(node): break

        for neighbour in graph.neighbors(node):
            neighbour_cost = graph.neighborCost(node,neighbour)
            cumDist = dist + neighbour_cost
            cumCost = cumDist + cost_func(neighbour)
            if cumCost < costMap[neighbour]:
                costMap[neighbour] = cumCost
                distMap[neighbour] = cumDist
                prev[neighbour] = node
                queue.add((cumCost,cumDist,neighbour))
    return distMap, prev, visited


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
    theoretical_ops = (V + E) * math.log2(V)
    actual_ops = stats['edges_relaxed'] + stats['heap_operations']
    ratio = actual_ops / theoretical_ops if theoretical_ops > 0 else 0
    print(f"\n  Complexity verification:")
    print(f"    Theoretical ops ~ {theoretical_ops:.0f}")
    print(f"    Actual ops: {actual_ops}")
    print(f"    Ratio: {ratio:.3f} (should be ~1 for average case)")

def select_random_nodes_nx(G, num_pairs=1):
    """Select random source-target pairs from largest component."""
    from MapVisuals import filter_outliers
    import random
    import networkx as nx
    
    # Filter outliers and get largest component
    kept_nodes = filter_outliers(G)
    subgraph = G.subgraph(kept_nodes)
    components = list(nx.connected_components(subgraph))
    largest = list(max(components, key=len))
    
    pairs = []
    for _ in range(num_pairs):
        source, target = random.sample(largest, 2)
        pairs.append((source, target))
    
    return pairs

def select_random_nodes_adj(adjacency_list, num_pairs=1):
    """Select random source-target pairs from adjacency list."""
    import random
    all_nodes = list(adjacency_list.keys())
    pairs = []
    for _ in range(num_pairs):
        source, target = random.sample(all_nodes, 2)
        pairs.append((source, target))
    
    return pairs

if __name__ == "__main__":
    import pickle
    GRAPH_FILE = 'Data/Old_Graph_data/walkability_graph.pkl'
    with open(GRAPH_FILE, 'rb') as f:
        G = pickle.load(f)
    nx_s,nx_t = select_random_nodes_nx(G)[0]
    nx_graph = nxGraph(G)
    newCost, newPath,visits = dijk_s_to_t(nx_graph,nx_s,nx_t)

    print(f"new cost: {newCost}, new path: {newPath},\n nodes visited: {visits}")
    

    ADJACENCY_PATH = "Data/ObbyMap32_pruned.json"
    adjacency_list, success = load_adjacency_list(ADJACENCY_PATH)
    a_graph = adjGraph(adjacency_list)
    a_s,a_t = select_random_nodes_adj(adjacency_list)[0]
    newCost, newPath,visits = dijk_s_to_t(a_graph,a_s,a_t)
    
    print(f"adj cost: {newCost},\n nodes visited: {visits},\n adj path: {newPath}")
    h_nx  = lambda p1, p2: euclideanDistance(G.nodes[p1]['pos'], G.nodes[p2]['pos'])
    h_adj = lambda p1, p2: euclideanDistance(p1, p2)
    nx_astarCost, nx_astarPath, nxvisits = test_astar(nx_graph, nx_s, nx_t, h_nx)
    a_astarCost,  a_astarPath,  avisits  = test_astar(a_graph,  a_s,  a_t,  h_adj)

    print(f"Astar:\nnx nodes visited: {nxvisits}, a nodes visited: {avisits}\n nx cost: {nx_astarCost}, adj cost: {a_astarCost}")
    print(f"nx path: {nx_astarPath}")
    print(f"a path: {a_astarPath}")

