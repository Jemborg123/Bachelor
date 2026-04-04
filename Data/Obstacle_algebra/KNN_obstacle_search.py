from Data.KDtree import KDtreeNode, KNNsearch
from Data.utils import simpleDistance, Heap
from Data.Obstacle_algebra.spatial_intersection import check_edge_intersects


def KNN_KDtree_obstacles(tree: KDtreeNode, point, k, polygons, spatial_index, polygon_bboxes, cell_size, blockedPoints, graph):
    pre_found = graph.get(tuple(point))
    KNN: Heap  = Heap()
    for neighbour in pre_found:
        KNN.add(neighbour)

    #Skip if we've already found all the neighbours
    remaining = k - KNN.n  
    if remaining > 0:
        seed = Heap()
        KNNsearch(tree,point,seed,k)
        KNNsearch_obstacles(tree, point, remaining, KNN, polygons, spatial_index, polygon_bboxes, cell_size, blockedPoints, graph,seed)

    # print(f"\rCache hits: {cache_hits}, Intersection calls: {intersection_calls}", end="", flush=True)
    # print(f"\rRedundant: {redundant_calls}, Unique: {unique_calls}", end="", flush=True)
    return KNN

cache_hits = 0
intersection_calls = 0

checked_edges = set()
redundant_calls = 0
unique_calls = 0


def KNNsearch_obstacles(tree: KDtreeNode, point, k, KNN: Heap, polygons, spatial_index, polygon_bboxes, cell_size, blockedPoints, graph,seed):
    if tree is None:
        return
    global cache_hits, intersection_calls
    global checked_edges, redundant_calls, unique_calls
    #Helper function allows early exit, avoiding unneccesary checks and or calculations
    def checkNextNode():
        axis_idx = 0 if tree.axis == 'x' else 1
        diff = point[axis_idx] - tree.coords[axis_idx]
        closest  = tree.leftChild if diff < 0 else tree.rightChild
        furthest = tree.rightChild if diff < 0 else tree.leftChild

        KNNsearch_obstacles(closest, point, k, KNN, polygons, spatial_index, polygon_bboxes, cell_size, blockedPoints, graph, seed)

        # Pruning: only explore far side if it could contain a valid closer neighbour
        max_dist = 30**2 #cut-off value if we can't find 8 neighbours not even in seed
        worst = KNN.peekMax()[0] if len(KNN) == k else min(seed.peekMax()[0] if seed.n == k else float('inf'),max_dist)
        if diff**2 < worst:
            KNNsearch_obstacles(furthest, point, k, KNN, polygons, spatial_index, polygon_bboxes, cell_size, blockedPoints, graph, seed)

    distance = simpleDistance(tree.coords, point)
    p = tuple(point)
    neighbours: set = graph.get(p)
    already_found = (distance,tree.coords) in neighbours
    if already_found: 
        checkNextNode()
        return

    #Check if we already know that point is blocked
    
    block_neighbours: set = blockedPoints.get(p)
    already_blocked = (distance,tree.coords) in block_neighbours
    if already_blocked:
        blocked = True
        cache_hits += 1
    else:
        edge = (min(p, tree.coords), max(p, tree.coords))
        if edge in checked_edges:
            redundant_calls += 1
            blocked = True
        else:
            unique_calls += 1
            checked_edges.add(edge)
            intersection_calls += 1
            blocked = check_edge_intersects(
                point, tree.coords,
                polygons, spatial_index, cell_size, polygon_bboxes
            )
    if blocked: 
        blockedPoints[tree.coords].add((distance, point))
        checkNextNode()
        return

    if len(KNN) < k:
        KNN.add((distance,tree.coords))
    elif distance < KNN.peekMax()[0]:  # better than current worst
        KNN.extractMax()
        KNN.add((distance,tree.coords))

    checkNextNode()
