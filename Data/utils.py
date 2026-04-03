import os

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

def simpleDistance(p1, p2):
    x1, y1 = p1
    x2, y2 = p2
    return (x1-x2)**2 + (y1-y2)**2

def minmaxxy(points):
    min_x = max_x = points[0][0]
    min_y = max_y = points[0][1]
    
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

import json

def save_adjacency_list(adjacency_list, filepath):
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    serializable = {}
    for point, neighbours in adjacency_list.items():
        key = f"{point[0]},{point[1]}"
        llist = neighbours.asList()
        serializable[key] = [
            [list(coords), distance] for (coords, distance) in llist
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
        for coords, distance in neighbours:
            adjacency_list.insertNeighbour(point, (tuple(coords), distance))
    print(f"Loaded {adjacency_list.length} nodes from {filepath}")
    return adjacency_list, True

class AdjacencyList:
    def __init__(self, vertices: list):
        self.keyVertices = vertices.copy()
        self.elements = {}
        for keyVertex in self.keyVertices:
            self.elements[keyVertex] = LinkedList()

    def insertNeighbour(self, vertex, neighbour):
        llist: LinkedList = self.elements.get(vertex)
        return llist.append(neighbour)

    def neighbors(self, vertex):
        return self.elements.get(vertex)
    
    def hasNeighbour(self, vertex):
        llist = self.neighbors(vertex)

    def length(self):
        return len(self.keyVertices)
    
    def removeNeighbour(self, vertex, neighbour):
        llist: LinkedList = self.elements.get(vertex)
        return llist.popVal(neighbour)
    
    def items(self):
        return self.elements.items()

    def keys(self):
        return self.elements.keys()

class LinkedListNode:
        def __init__(self, value = None):
            self.value = value
            self.next = None

        def __str__(self):
            return str(self.value)

class LinkedList:
    def __init__(self, Inputlist: list = None):
        self.head = None
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
            if _are_equal(node,value): return True
            nextnode = node.next
            node = nextnode
        return False
    
    def pop(self):
        if self.head is None: return None

        value = self.head.value
        newHead = self.head.next
        self.head = newHead
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
    
    # OBS! Generates a reversed copy, ONLY use when order doesn't matter
    def copy(self):
        newCopy = LinkedList()
        node = self.head
        while (node is not None):
            newCopy.append(node.value)
            nextnode = node.next
            node = nextnode
        return newCopy

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