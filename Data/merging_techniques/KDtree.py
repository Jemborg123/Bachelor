from Data.utils import simpleDistance
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
    KNN = [None]*k
    KNNsearch(tree,point,KNN)
    return KNN

def KNNsearch(tree: KDtreeNode, point,KNN):
    if tree is None : return

    distance = simpleDistance(tree.coords,point)

    if None in KNN:
        KNN[KNN.index(None)] = (tree.coords, distance)
    else:
        worst_idx = KNN.index(max(KNN, key=lambda n: n[1]))
        if distance < KNN[worst_idx][1]:
            KNN[worst_idx] = (tree.coords, distance)
    
    axis_idx = 0 if tree.axis == 'x' else 1
    diff = point[axis_idx] - tree.coords[axis_idx]

    closest = tree.leftChild if diff <0 else tree.rightChild
    furthest = tree.rightChild if diff < 0 else tree.leftChild
    KNNsearch(closest,point,KNN)

    worst = max(KNN, key=lambda n: n[1])[1] if None not in KNN else float('inf')
    if abs(diff) < worst:
        KNNsearch(furthest,point,KNN)

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

