import os
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
        serializable[key] = [
            [list(coords), distance] for coords, distance in neighbours
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
    adjacency_list = {}
    for key, neighbours in raw.items():
        x, y = map(float, key.split(','))
        point = (x, y)
        adjacency_list[point] = [
            (tuple(coords), distance) for coords, distance in neighbours
        ]
    print(f"Loaded {len(adjacency_list)} nodes from {filepath}")
    return adjacency_list, True