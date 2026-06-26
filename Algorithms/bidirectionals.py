import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import heapq
import math
from Data.utils import *
import Data.KDtree as KDtree
from Algorithms.ALT import *


def results(mu, forwardPrev, backwardPrev, forwardVisited, backwardVisited):
    dist = mu[0]
    meetNodes = mu[1]
    visited = set(forwardVisited) | set(backwardVisited)
    if meetNodes is None:                       # no path found
        return dist, [], len(visited)           # dist is float('inf')
    path = build_path(meetNodes, forwardPrev, backwardPrev)
    return dist, path, len(visited)


def build_path(meetNodes, forwardPrev, backwardPrev):
    u, v = meetNodes
    left = []; n = u
    while n is not None:
        left.append(n); n = forwardPrev[n]
    left.reverse()                              # s .. u
    right = []; n = v
    while n is not None:
        right.append(n); n = backwardPrev[n]    # v .. t
    return left + right


def bi_dijk_new(graph, source, sink, cost_func, stopCondition=None):
    """
    Bidirectional Dijkstra / A*.

    cost_func(node, direction) is a *potential* added to the true distance to
    form the heap key. For plain Dijkstra it returns 0. For A* use bi_astar_new,
    which supplies balanced/consistent potentials so the stopping rule below is
    provably optimal.

    Returns: (cost, path, nodes_visited)  -- cost is always a scalar.
    """
    INF = float('inf')

    # ---- forward search state (rooted at source) ----
    forwardCostMap = {node: INF for node in graph.nodes()}
    forwardDistMap = {node: INF for node in graph.nodes()}
    forwardPrev    = {node: None for node in graph.nodes()}
    forwardCostMap[source] = cost_func(source, 'forward')
    forwardDistMap[source] = 0

    # ---- backward search state (rooted at sink) ----
    backwardCostMap = {node: INF for node in graph.nodes()}
    backwardDistMap = {node: INF for node in graph.nodes()}
    backwardPrev    = {node: None for node in graph.nodes()}
    backwardCostMap[sink] = cost_func(sink, 'backward')
    backwardDistMap[sink] = 0

    queue = MinHeap()
    queue.add((forwardCostMap[source], forwardDistMap[source], source, 'forward'))
    queue.add((backwardCostMap[sink],  backwardDistMap[sink],  sink,   'backward'))

    forwardVisited  = set()    # settled (popped) forward nodes
    backwardVisited = set()    # settled (popped) backward nodes

    # Frontier keys: lower bounds on what each side can still pop next.
    # Keys pop in non-decreasing order (consistent potentials), so the most
    # recently popped key per side is a valid lower bound on all future ones.
    topForward  = forwardCostMap[source]
    topBackward = backwardCostMap[sink]

    mu = (INF, None)           # (best path length found, (forwardNode, backwardNode))

    while len(queue) > 0:
        cost, dist, node, direction = queue.extractMin()

        if direction == 'forward':
            costMap, distMap, prev = forwardCostMap, forwardDistMap, forwardPrev
            settled, otherSettled  = forwardVisited, backwardVisited
            otherDistMap = backwardDistMap
        else:
            costMap, distMap, prev = backwardCostMap, backwardDistMap, backwardPrev
            settled, otherSettled  = backwardVisited, forwardVisited
            otherDistMap = forwardDistMap

        if cost > costMap[node]:                # stale heap entry
            continue

        # advance this side's frontier lower bound
        if direction == 'forward':
            topForward = cost
        else:
            topBackward = cost

        # Optimal-stop: nothing left on either frontier can beat the best
        # meeting found so far. With balanced potentials the sum of frontier
        # keys lower-bounds the length of any path still to be discovered.
        if topForward + topBackward >= mu[0]:
            break

        settled.add(node)

        for neighbour in graph.neighbors(node):
            neighbour_cost = graph.neighborCost(node, neighbour)
            cumDist = dist + neighbour_cost
            cumCost = cumDist + cost_func(neighbour, direction)

            if cumCost < costMap[neighbour]:
                costMap[neighbour] = cumCost
                distMap[neighbour] = cumDist
                prev[neighbour] = node
                queue.add((cumCost, cumDist, neighbour, direction))

            # crossing edge into the region the other search has settled
            if neighbour in otherSettled:
                total = cumDist + otherDistMap[neighbour]
                if total < mu[0]:
                    if direction == 'forward':
                        mu = (total, (node, neighbour))
                    else:
                        mu = (total, (neighbour, node))

    return results(mu, forwardPrev, backwardPrev, forwardVisited, backwardVisited)


def bi_astar_new(graph, s, t, h):
    # Balanced (consistent) potentials so the forward and backward searches stay
    # mutually compatible and  topForward + topBackward >= mu  is a sound
    # optimality stopping rule.
    #   forward  potential : (h(n,t) - h(n,s)) / 2
    #   backward potential : (h(n,s) - h(n,t)) / 2   ( = -forward potential )
    # Because the two potentials sum to 0 at every node, the heap keys of a node
    # from the two sides sum to the true length of the path through it.
    def potential(node, direction):
        to_t = h(node, t)
        to_s = h(node, s)
        if direction == 'forward':
            return (to_t - to_s) / 2
        else:
            return (to_s - to_t) / 2
    return bi_dijk_new(graph, s, t, potential)


from MapVisuals import *
def test_a_list():

    ADJACENCY_PATH = "Data/ObbyMap32_pruned.json"
    adjacency_list, success = load_adjacency_list(ADJACENCY_PATH)
    a_graph = adjGraph(adjacency_list)
    a_s, a_t = select_random_nodes_adj(adjacency_list)[0]
    cost_func = lambda x, d: 0
    biCost, biPath, bivisits = bi_dijk_new(a_graph, a_s, a_t, cost_func)
    print("BI")
    print(f"adj cost: {biCost},\n nodes visited: {bivisits},\n adj path: ")

    uniCost, uniPath, uniVisits = dijk_s_to_t(a_graph, a_s, a_t)
    print("UNI")
    print(f"adj cost: {uniCost},\n nodes visited: {uniVisits},\n adj path: ")

    h_adj = lambda p1, p2: adj_euclidean(p1, p2)
    biaCost, biaPath, biaVisits = bi_astar_new(a_graph, a_s, a_t, h_adj)

    print("BI astar")
    print(f"adj cost: {biaCost},\n nodes visited: {biaVisits},\n adj path: ")

    uniaCost, uniaPath, uniaVisits = new_astar(a_graph, a_s, a_t, h_adj)
    print("UNI astar")
    print(f"adj cost: {uniaCost},\n nodes visited: {uniaVisits},\n adj path: ")

    a_landmarks = new_select_landmarks(a_graph)
    a_pp = landmark_distances(a_graph, a_landmarks)
    h_adj = lambda p1, p2: landmark_h(p1, p2, a_pp, len(a_landmarks))
    bialtCost, bialtPath, bialtVisits = bi_astar_new(a_graph, a_s, a_t, h_adj)

    print("BI ALT")
    print(f"adj cost: {bialtCost},\n nodes visited: {bialtVisits},\n adj path: ")

    unialtCost, unialtPath, unialtVisits = new_astar(a_graph, a_s, a_t, h_adj)
    print("UNI ALT")
    print(f"adj cost: {unialtCost},\n nodes visited: {unialtVisits},\n adj path: ")

    # create_adj_path_map(adjacency_list, uniPath, uniCost, a_s, a_t, "Maps/adj_UNIdijkstra.html")
    # create_adj_path_map(adjacency_list, biPath, biCost, a_s, a_t, "Maps/adj_BIdijkstra.html")

    # create_adj_path_map(adjacency_list, uniaPath, uniaCost, a_s, a_t, "Maps/adj_UNIastar.html")
    # create_adj_path_map(adjacency_list, biaPath, biaCost, a_s, a_t, "Maps/adj_BIastar.html")

    # create_adj_path_map(adjacency_list, unialtPath, unialtCost, a_s, a_t, "Maps/adj_UNIALT.html")
    # create_adj_path_map(adjacency_list, bialtPath, bialtCost, a_s, a_t, "Maps/adj_BIALT.html")


def test_nx():
    import pickle
    GRAPH_FILE = 'Data/Old_Graph_data/walkability_graph.pkl'
    with open(GRAPH_FILE, 'rb') as f:
        G = pickle.load(f)
    nx_s, nx_t = select_random_nodes_nx(G)[0]
    nx_graph = nxGraph(G)
    cost_func = lambda x, d: 0
    biCost, biPath, bivisits = bi_dijk_new(nx_graph, nx_s, nx_t, cost_func)

    print("BI")
    print(f"nx cost: {biCost},\n nodes visited: {bivisits},\n nx path: {biPath}")

    h_nx = lambda p1, p2: nx_euclidean(p1, p2, G)
    biaCost, biaPath, biaVisits = bi_astar_new(nx_graph, nx_s, nx_t, h_nx)

    print("BI astar")
    print(f"nx cost: {biaCost},\n nodes visited: {biaVisits},\n nx path: {biaPath}")

    nx_landmarks = new_select_landmarks(nx_graph)
    nx_pp = landmark_distances(nx_graph, nx_landmarks)
    h_nx = lambda p1, p2: landmark_h(p1, p2, nx_pp, len(nx_landmarks))
    bialtCost, bialtPath, bialtVisits = bi_astar_new(nx_graph, nx_s, nx_t, h_nx)

    print("BI ALT")
    print(f"adj cost: {bialtCost},\n nodes visited: {bialtVisits},\n adj path: {bialtPath}")

    create_path_map(G, biPath, biCost, nx_s, nx_t, "nx_BIdijkstra.html")
    create_path_map(G, biaPath, biaCost, nx_s, nx_t, "nx_BIastar.html")
    create_path_map(G, bialtPath, bialtCost, nx_s, nx_t, "nx_BIalt.html")


if __name__ == "__main__":
    test_a_list()
    # test_nx()