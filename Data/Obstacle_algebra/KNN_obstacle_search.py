from Data.merging_techniques.KDtree import KDtreeNode
from Data.utils import simpleDistance
from Data.Obstacle_algebra.spatial_intersection import check_edge_intersects

def KNN_KDtree_obstacles(tree: KDtreeNode, point, k, polygons, spatial_index, polygon_bboxes, cell_size,adjacency_list):
    pre_found = adjacency_list.get(tuple(point), [])
    KNN = list(pre_found)  
    remaining = k - len(KNN)  
    if remaining > 0:
        KNNsearch_obstacles(tree, point, remaining, KNN, polygons, spatial_index, polygon_bboxes, cell_size, adjacency_list)
    return KNN

def KNNsearch_obstacles(tree: KDtreeNode, point, k, KNN, polygons, spatial_index, polygon_bboxes, cell_size,adjacency_list,depth=0):
    if depth > 10000:
        print("MAX DEPTH EXCEEDED - infinite recursion detected")
        return
    if tree is None:
        return

    distance = simpleDistance(tree.coords, point)
    
    blocked = check_edge_intersects(
        point, tree.coords,
        polygons, spatial_index, cell_size, polygon_bboxes
    )
    already_found = any(coords == tree.coords for coords, distance in adjacency_list[tuple(point)]) if tuple(point) in adjacency_list else False
    if not blocked and not already_found:
        if len(KNN) < k:
            KNN.append((tree.coords, distance))
            KNN.sort(key=lambda n: n[1])
        elif distance < KNN[-1][1]:  # better than current worst
            KNN[-1] = (tree.coords, distance)
            KNN.sort(key=lambda n: n[1])

    axis_idx = 0 if tree.axis == 'x' else 1
    diff = point[axis_idx] - tree.coords[axis_idx]
    closest  = tree.leftChild if diff < 0 else tree.rightChild
    furthest = tree.rightChild if diff < 0 else tree.leftChild

    KNNsearch_obstacles(closest, point, k, KNN, polygons, spatial_index, polygon_bboxes, cell_size,adjacency_list,depth+1)

    # Pruning: only explore far side if it could contain a valid closer neighbour
    worst = KNN[-1][1] if len(KNN) == k else float('inf')
    if abs(diff) < worst:
        KNNsearch_obstacles(furthest, point, k, KNN, polygons, spatial_index, polygon_bboxes, cell_size,adjacency_list,depth+1)