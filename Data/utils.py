from math import floor,sqrt
import os
import matplotlib.pyplot as plt
import json

def _are_equal(a, b):
    """Safely compare two values, handling NumPy arrays and other edge cases."""
    if a is b:
        return True
    
    try:
        # Try normal equality comparison
        return a == b
    except ValueError:
        # Handle NumPy arrays
        try:
            import numpy as np
            if isinstance(a, np.ndarray) and isinstance(b, np.ndarray):
                return np.array_equal(a, b)
        except:
            pass
        
        # Last resort: compare string representations
        try:
            return str(a) == str(b)
        except:
            return False

def euclideanDistance(p1, p2):
    x1, y1 = p1
    x2, y2 = p2
    return sqrt((x1-x2)**2 + (y1-y2)**2)

def minmaxxy(points):
    x0,y0 =points[0]
    min_x = max_x = x0
    min_y = max_y = y0
    
    # Loop through the remaining points
    for x, y in points[1:]:
        # Update min and max for x
        if x < min_x:
            min_x = x
        if x > max_x:
            max_x = x
        
        # Update min and max for y
        if y < min_y:
            min_y = y
        if y > max_y:
            max_y = y
    
    print(f"X: min = {min_x}, max = {max_x}")
    print(f"Y: min = {min_y}, max = {max_y}")

def point_to_square(point,buffer):
    square=[]
    for i in [-buffer,buffer]:
        for j in [-buffer,buffer]:
            x,y=point[0]+i,point[1]+j
            square.append([x,y])
    return square

def savePointsDataToFile(data,filepath):
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, 'w') as f:
        json.dump(data, f)
    print(f"Saved {len(data)} entries to {filepath}")

def loadPointsDataFromFile(filepath):
    if not os.path.exists(filepath):
        return None, False
    with open(filepath, 'r') as f:
        raw = json.load(f)
    return raw

def save_adjacency_list(adjacency_list, filepath):
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    serializable = {}
    for point, neighbours in adjacency_list.items():
        key = f"{point[0]},{point[1]}"
        llist = neighbours.asList()
        serializable[key] = [
            [distance, list(coords)] for (distance, coords) in llist
        ]
    with open(filepath, 'w') as f:
        json.dump(serializable, f)
    print(f"Saved {len(serializable)} nodes to {filepath}")


def load_adjacency_list(filepath):
    """Loads adjacency list from a JSON file. Returns (adjacency_list, success)."""
    import os
    if not os.path.exists(filepath):
        return None, False
    with open(filepath, 'r') as f:
        raw = json.load(f)

    keys = []
    for key, neighbours in raw.items():
        x, y = map(float, key.split(','))
        point = (x, y)
        keys.append(point)

    adjacency_list = AdjacencyList(keys)

    for key, neighbours in raw.items():
        x, y = map(float, key.split(','))
        point = (x, y)
        for distance, coords in neighbours:
            adjacency_list.insertNeighbour(point, (distance, tuple(coords)))
    print(f"Loaded {adjacency_list.length()} nodes from {filepath}")
    return adjacency_list, True

class Queue:
    def __init__(self, fromList=[],space = 1000):
        self.head = 0
        self.tail = 0
        self.size = space
        self.array = [None for _ in range(space)]
        for element in fromList:
            self.enqueue(element)

    def enqueue(self, x):
        self.array[self.tail] = x
        self.tail = self.tail+1
        if self.tail>=self.size and self.head>0:
            self.tail = 0
        if self.array[self.tail] is not None:
            raise Exception(f"Queue couldn't handle all elements given its size {self.space}") 
        
    def dequeue(self):
        x = self.array[self.head]
        if x is None:
            return
        self.array[self.head] = None
        self.head = self.head+1
        if self.head >= self.size:
            self.head = 0
        return x
    
    def isEmpty(self):
        return self.array[self.head] is None
    
    def __len__(self):
        return self.tail-self.head if self.tail>=self.head else self.size-self.head+self.tail+1

class LinkedListNode:
        def __init__(self, value = None):
            self.value = value
            self.next = None

        def __str__(self):
            return str(self.value)

class LinkedList:
    def __init__(self, Inputlist: list = None):
        self.head = None
        self.n = 0
        if Inputlist is None: 
            return

        list = Inputlist.copy()

        if len(list) == 0: 
            return
        
        for element in list:
            self.append(element)
    
    def __str__(self):
        node = self.head
        if node is None: return None
        llString = "(HEAD)"+str(node)
        
        while(True):
            current = node.next
            if current is None: break
            llString = llString+", "+str(current)
            node = current

        return "Linked List: ("+llString+")"

    
    def append(self, value):
        newHead = LinkedListNode(value)
        newHead.next = self.head
        self.head = newHead
        self.n = self.n + 1

    def get(self, index):
        if self.head is None: return None
        node = self.head
        for _ in range(index):
            if node.next is None: return None
            node = node.next
        return node.value
    
    def isEmpty(self):
        return self.head is None
    
    def has(self, value):
        node = self.head
        while node is not None:
            if _are_equal(node.value,value): return True
            nextnode = node.next
            node = nextnode
        return False
    
    def pop(self):
        if self.head is None: return None

        value = self.head.value
        newHead = self.head.next
        self.head = newHead
        self.n = self.n - 1
        return value
        

    def popAt(self, index):
        if self.head is None: return None

        if index == 0:
            return self.pop()
        
        node = self.head

        for i in range (index-1):
            nextNode = node.next
            node = nextNode
            if node is None: 
                print("No element at index",index,"in linkedlist of size",i+1)
                return None

        nodeToDelete = node.next
        if nodeToDelete is None: 
            print("No element at ",index," in linkedlist of size",index)
            return None
        
        value = nodeToDelete.value
        
        node.next = nodeToDelete.next
        self.n = self.n - 1
        return value

    def popVal(self, value):
        node = self.head
        if node.value == value:
            return self.pop()
        
        while(node is not None):
            current = node.next
            if current is None: break

            if current.value == value:
                nextnode = current.next
                node.next = nextnode
                self.n = self.n - 1
                return value
            node = current

        return None
    
    def asList(self):
        out = []
        node = self.head
        while (node is not None):
            out.append(node.value)
            nextnode = node.next
            node = nextnode
        return out
    
    def asHeap(self):
        out = Heap()
        node = self.head
        while (node is not None):
            out.add(node.value)
            nextnode = node.next
            node = nextnode
        return out

    
    # OBS! Generates a reversed copy, ONLY use when order doesn't matter
    def copy(self):
        newCopy = LinkedList()
        node = self.head
        while (node is not None):
            newCopy.append(node.value)
            nextnode = node.next
            node = nextnode
        return newCopy
    
    def __len__(self):
        return self.n
    

class AdjacencyList:
    def __init__(self, vertices: list):
        self.keyVertices = vertices.copy()
        self.elements = {}
        self.numedges = 0
        for keyVertex in self.keyVertices:
            self.elements[keyVertex] = LinkedList()

    def addPoint(self, point):
        self.elements[point] = LinkedList()

    def popPoint(self, point):
        llist = self.elements.pop(point)
        self.numedges = self.numedges - len(llist)
        return llist

    def insertNeighbour(self, vertex, neighbour):
        llist: LinkedList = self.elements.get(vertex)
        self.numedges = self.numedges+1
        return llist.append(neighbour)

    def neighbors(self, vertex)->LinkedList:
        return self.elements.get(vertex)
    
    def hasNeighbour(self, vertex, neighbour):
        llist = self.neighbors(vertex)
        return llist.has(neighbour)

    def length(self):
        return len(self.keyVertices)
    
    def numEdges(self):
        return self.numedges
    
    def removeNeighbour(self, vertex, neighbour):
        llist: LinkedList = self.elements.get(vertex)
        self.numedges = self.numedges -1
        return llist.popVal(neighbour)
    
    def items(self):
        return self.elements.items()

    def keys(self):
        return self.elements.keys()
    
    def get_node_by_index(self, idx):
        return list(self.elements.keys())[idx]



class Heap:
    def __init__(self):
        self.heap = [None]
        self.n = 0
    
    def parent(self, x):
        return floor(x/2)
    
    def left(self, x):
        return 2*x
    
    def right(self, x):
        return (2*x)+1
    
    def swap(self, x1, x2):
        temp = self.heap[x1]
        self.heap[x1] = self.heap[x2]
        self.heap[x2] = temp
    
    def bubbleUp(self, x):
        if x <= 1: return
        key = self.heap[x]
        pIdx = self.parent(x)
        pKey = self.heap[pIdx]
        if key > pKey:
            self.swap(x,pIdx)
            self.bubbleUp(pIdx)

    def add(self, key):
        self.n = self.n + 1
        self.heap.append(key)
        self.bubbleUp(self.n)

    def bubbleDown(self, x):
        lIdx = self.left(x)
        rIdx = self.right(x)

        if lIdx > self.n: return

        if rIdx > self.n:
            if self.heap[x] < self.heap[lIdx]:
                self.swap(x, lIdx)
            return

        key = self.heap[x]
        lKey = self.heap[lIdx]
        rKey = self.heap[rIdx]

        if key >= lKey and key >= rKey: return

        largestChild = lIdx if lKey > rKey else rIdx
        self.swap(x,largestChild)
        self.bubbleDown(largestChild)

    def extractMax(self):
        if self.n == 0: return None
        r = self.heap[1]
        self.heap[1] = self.heap[self.n]
        self.heap.pop()
        self.n = self.n-1
        self.bubbleDown(1)
        return r
    
    def peekMax(self):
        return self.heap[1]
    
    def __len__(self):
        return self.n





#Test code, ignore if not main
if __name__ == "__main__":
    Test = LinkedList()
    print(Test.isEmpty)
    Test.append(1)
    Test.append(2)
    Test.append(3)
    for i in range(4):
        print(Test.get(i))

    print(str(Test))


    print(str(Test.isEmpty()))

    Test.append(10)
    for i in range(4):
        print(Test.get(i))

    print(str(Test))
    print(Test.popVal(2))
    Test.popAt(3)
    Test.pop()

    print(str(Test))
    l = Test.asList()
    print(l)

def visualize_graph(adjacency_list, polygons=None, labels=None):
    print("Visualizing graph with matplotlib")
    fig, ax = plt.subplots(figsize=(12, 12))
    # Draw obstacle polygons
    if polygons is not None:
        for polygon in polygons:
            xs = [p[0] for p in polygon]
            ys = [p[1] for p in polygon]
            # close the ring
            xs.append(xs[0])
            ys.append(ys[0])
            ax.plot(xs, ys, 'r-', linewidth=1, alpha=0.7)
    # Draw edges
    drawn_edges = set()
    for point, neighbours in adjacency_list.items():
        for distance, coords in neighbours.asList():
            edge = (min(point, coords), max(point, coords))
            if edge not in drawn_edges:
                drawn_edges.add(edge)
                ax.plot(
                    [point[0], coords[0]],
                    [point[1], coords[1]],
                    'gray', linewidth=0.5, alpha=0.5
                )

    # Draw nodes
    xs = [p[0] for p in adjacency_list.keys()]
    ys = [p[1] for p in adjacency_list.keys()]
    ax.scatter(xs, ys, c='blue', s=0.1, zorder=2)


    if labels is not None:
        draw_labels(ax,labels)

    ax.set_aspect('equal')
    ax.set_title(f"Graph — {adjacency_list.length()} nodes, {len(drawn_edges)} edges")
    plt.tight_layout()
    plt.show()

def draw_labels(ax,labels):
    labelPoints = labels
    for (x, y), name in labelPoints:
        ax.text(
            x, y, str(name),
            fontsize=6,
            ha='center', va='center',
            color='black',
            zorder=3,                       # above the nodes (zorder=2)
            bbox=dict(boxstyle='round,pad=0.2',
                      fc='white', ec='none', alpha=0.7),
        )