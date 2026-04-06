from Data.utils import simpleDistance, Heap
from Data.Obstacle_algebra.spatial_intersection import check_edge_intersects

class KDtreeNode():
    def __init__(self,x,y,axis,leftChild=None,rightChild=None):
        self.coords = (x,y)
        self.leftChild = leftChild
        self.rightChild = rightChild
        self.leaf = leftChild is None and rightChild is None
        self.axis = axis
        

def buildKDtree(dataset,axis='x'):
    if dataset is None or len(dataset) == 0:
        return None
    axis_key = 0 if axis =='x' else 1 if axis == 'y' else None
    if axis_key is None:
        print("error bad axis lookup")
        return
    if is_leaf(dataset):
        x, y = dataset[0]
        return KDtreeNode(x, y,axis)
    
    sorted_on_axis = sorted(dataset, key=lambda p: p[axis_key])
    median_index = int(len(sorted_on_axis)/2)
    node_x, node_y = sorted_on_axis[median_index]
    
    leftBranch, rightBranch = splitTree(sorted_on_axis,median_index)
    changed_axis = 'y' if axis =='x' else 'x'
    
    return KDtreeNode(
        node_x,
        node_y,
        axis,
        buildKDtree(leftBranch,changed_axis),
        buildKDtree(rightBranch,changed_axis))

def is_leaf(points):
    return len(points) <= 1

def splitTree(dataset,median):
    left  = dataset[:median]
    right = dataset[median + 1:]
    return left,right

def KNN_KDtree(tree: KDtreeNode,point,k):
    KNN = Heap()
    KNNsearch(tree,point,KNN,k)
    return KNN

def KNNsearch(tree: KDtreeNode, point,KNN: Heap, k):
    if tree is None : return

    distance = simpleDistance(tree.coords,point)

    if len(KNN)<k:
        KNN.add((distance, tree.coords))
    else:
        if distance < KNN.peekMax()[0]:
            KNN.extractMax()
            KNN.add((distance, tree.coords))
    
    axis_idx = 0 if tree.axis == 'x' else 1
    diff = point[axis_idx] - tree.coords[axis_idx]

    closest = tree.leftChild if diff <0 else tree.rightChild
    furthest = tree.rightChild if diff < 0 else tree.leftChild
    KNNsearch(closest,point,KNN,k)

    worst = KNN.peekMax()[0] if len(KNN) == k else float('inf')
    if diff**2 < worst:
        KNNsearch(furthest,point,KNN,k)

def radiusSearch(tree: KDtreeNode, point, eps, result=None):
    if result is None: result = []
    if tree is None: return result

    dist = simpleDistance(tree.coords, point)
    if dist <= eps and tree.coords[0] != point[0] and tree.coords[1] != point[1]:
        result.append((tree.coords, dist))

    axis_idx = 0 if tree.axis == 'x' else 1
    diff = point[axis_idx] - tree.coords[axis_idx]

    closest  = tree.leftChild  if diff < 0 else tree.rightChild
    furthest = tree.rightChild if diff < 0 else tree.leftChild

    radiusSearch(closest, point, eps, result)
    if diff**2 <= eps:  
        radiusSearch(furthest, point, eps, result)

    return result

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
    return KNN

def KNNsearch_obstacles(tree: KDtreeNode, point, k, KNN: Heap, polygons, spatial_index, polygon_bboxes, cell_size, blockedPoints, graph,seed):
    if tree is None:
        return
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
    else:
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