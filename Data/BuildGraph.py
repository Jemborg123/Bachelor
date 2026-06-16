print("script started")
import sys
import os
import random

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import Data.Database_access.loadFromDb as loadFromDb
import Data.merging_techniques.dbscan_merge as dbscan_merge
from Data.merging_techniques.merge_types import MergeType
import Data.merging_techniques.grid_merge as grid_merge
import Data.KDtree as KDtree
import Data.Obstacle_algebra.spatial_intersection as spatial_intersection
from Data.utils import save_adjacency_list,load_adjacency_list,AdjacencyList,LinkedList, Heap, visualize_graph, savePointsDataToFile, euclideanDistance,Queue
from Database_access.loadFromDb import fetch_building_names
import Data.Obstacle_algebra.polygon_offset as polygon_offset



COMPARISON_GRAPHS = {
    "Walkable layers map":  "Data/Compare/walkable_layers.json",
    "Grid map":             "Data/Compare/grid.json",
    "Obstacle map":         "Data/Compare/obstacle.json",
    "Obstacle map + roads": "Data/Compare/obstacle_roads.json",
}


def showGraph(ADJACENCY_PATH="Data/Adjacency_list_DBSCANMERGED.json"):
    print("script started")
    adjacency_list,success = load_adjacency_list(ADJACENCY_PATH)
    if success:
        obstacles = loadFromDb.fetch_obstacle_gdfs()
        polygons = loadFromDb.geodataframe_to_polygon_lists(obstacles)
        filtered_polygons = loadFromDb.remove_near_zero_polygon_outliers(polygons)
        print("succes, showing graph")
        labels = fetch_building_names("llyn_bygning_dtu")
        tree = KDtree.buildKDtree(adjacency_list.keys())
        labeledpoints = assignPointsData(tree,labels)
        for x in labeledpoints.items():
            print(x)
        savePointsDataToFile(labeledpoints,"Data/LabeledPoints.json")
        
        visualize_graph(adjacency_list,filtered_polygons,labels)
    else:
        print("No adjacency list found at",ADJACENCY_PATH,", building graph from scratch...")
        obstacleBasedMap(ADJACENCY_PATH,10)
        # gridMap(ADJACENCY_PATH,5)
        # obstacleAwareGraph(MergeType.DBSCANMERGE)
        # obstacleIgnoringGraph(MergeType.SQUAREBUCKETMERGE)

def add_road_network(adjacency_list:AdjacencyList, polylines):
    for line in polylines:
        for a, b in zip(line, line[1:]):
            a, b = tuple(a), tuple(b)
            if a == b:
                continue
            adjacency_list.addPoint(a)
            adjacency_list.addPoint(b)
            distance = euclideanDistance(a, b)
            adjacency_list.insertNeighbour(a, (distance, b))
            adjacency_list.insertNeighbour(b, (distance, a))

def obstacleBasedMap(filepath, CELLSIZE, include_roads=True, visualize=False):
    obstacles = loadFromDb.fetch_obstacle_gdfs()
    obstacles = loadFromDb.geodataframe_to_polygon_lists(obstacles)
    polygons = loadFromDb.remove_near_zero_polygon_outliers(obstacles)
    polygon_bboxes = spatial_intersection.precompute_bboxes(polygons)
    spatial_index = spatial_intersection.build_spatial_index(polygons, cell_size=CELLSIZE)

    nodes = []
    for poly in polygons:
        nodes.extend(polygon_offset.offset_polygon_outward(poly, 1.5))
    nodes = mergePoints(nodes, MergeType.DBSCANMERGE)
    nodes = list(dict.fromkeys(tuple(p) for p in nodes))

    road_lines = []
    if include_roads:
        road = loadFromDb.fetch_gdfs_from_layer(
            ["mobilitetsnetvaerkfodgaengercykel", "mobilitetsnetvaerkdrift", "mobilitetsnetvaerkbil"])
        road_lines = loadFromDb.geodataframe_to_polyline_lists(road)
        road_lines = loadFromDb.remove_near_zero_polygon_outliers(road_lines)
        road_verts = loadFromDb.geodataframe_to_vertex_lists(road)
        road_verts_cleaned = loadFromDb.remove_near_zero_point_outliers(road_verts)
        nodes.extend(list(dict.fromkeys(tuple(p) for p in road_verts_cleaned)))

    graph = {tuple(p): set() for p in nodes}
    blockedPoints = {tuple(p): set() for p in nodes}
    tree = KDtree.buildKDtree(nodes)
    adjacency_list = AdjacencyList(nodes)
    neighbourFunc = lambda point: KDtree.KNN_KDtree_obstacles(
        tree=tree, point=point, k=32,
        polygons=polygons, spatial_index=spatial_index,
        polygon_bboxes=polygon_bboxes, cell_size=CELLSIZE,
        blockedPoints=blockedPoints, graph=graph)

    if include_roads:
        add_road_network(adjacency_list, road_lines)
    buildAdjacencyList(adjacency_list, nodes, neighbourFunc, graph)
    save_adjacency_list(adjacency_list=adjacency_list, filepath=filepath)
    if visualize:
        visualize_graph(adjacency_list, polygons)


def point_in_polygon(point, polygon):
    x, y = point
    inside = False
    n = len(polygon)
    j = n - 1
    for i in range(n):
        xi, yi = polygon[i]
        xj, yj = polygon[j]
        if ((yi > y) != (yj > y)) and \
           (x < (xj - xi) * (y - yi) / (yj - yi + 1e-12) + xi):
            inside = not inside
        j = i
    return inside


def point_in_any_obstacle(point, polygons, spatial_index, cell_size):
    cx = int(point[0] // cell_size)
    cy = int(point[1] // cell_size)
    for i in spatial_index.get((cx, cy), []):
        if point_in_polygon(point, polygons[i]):
            return True
    return False


def gridMapObstacleAware(filepath, tileSize, CELLSIZE=10):
    obstacles = loadFromDb.fetch_obstacle_gdfs()
    polygons = loadFromDb.geodataframe_to_polygon_lists(obstacles)
    polygons = loadFromDb.remove_near_zero_polygon_outliers(polygons)
    bboxes = spatial_intersection.precompute_bboxes(polygons)
    index = spatial_intersection.build_spatial_index(polygons, cell_size=CELLSIZE)

    xs, ys = [], []
    for poly in polygons:
        xs.extend(p[0] for p in poly)
        ys.extend(p[1] for p in poly)
    min_x, min_y = min(xs), min(ys)
    max_x, max_y = max(xs), max(ys)
    dx, dy = int(max_x - min_x), int(max_y - min_y)

    rows = range(0, dy, tileSize)
    n_rows = len(rows)
    total_cells = n_rows * len(range(0, dx, tileSize))
    print(f"Grid map: filtering {total_cells} candidate nodes against obstacles ...")

    grid = {}
    for row, i in enumerate(rows):
        for col, j in enumerate(range(0, dx, tileSize)):
            pt = (min_x + j, min_y + i)
            if not point_in_any_obstacle(pt, polygons, index, CELLSIZE):
                grid[(row, col)] = pt
        print(f"\r  nodes: row {row + 1}/{n_rows}, kept {len(grid)}", end="", flush=True)
    print(f"\n  kept {len(grid)} of {total_cells} nodes (removed {total_cells - len(grid)} inside obstacles)")

    nodes = list(grid.values())
    adjacency_list = AdjacencyList(nodes)
    SQRT2 = 2 ** 0.5
    offsets = [((-1, -1), SQRT2), ((-1, 0), 1.0), ((-1, 1), SQRT2),
               ((0, -1), 1.0),                    ((0, 1), 1.0),
               ((1, -1), SQRT2), ((1, 0), 1.0), ((1, 1), SQRT2)]

    n = len(grid)
    edges_kept = 0
    print(f"Grid map: building edges for {n} nodes ...")
    for processed, ((row, col), p) in enumerate(grid.items()):
        for (dr, dc), w in offsets:
            q = grid.get((row + dr, col + dc))
            if q is None:
                continue
            if spatial_intersection.check_edge_intersects(
                    p, q, polygons, index, CELLSIZE, bboxes):
                continue
            adjacency_list.insertNeighbour(p, (w * tileSize, q))
            edges_kept += 1
        if processed % 500 == 0:
            print(f"\r  edges: {processed}/{n} nodes, {edges_kept} directed edges",
                  end="", flush=True)
    print(f"\r  edges: {n}/{n} nodes, {edges_kept} directed edges")

    save_adjacency_list(adjacency_list=adjacency_list, filepath=filepath)
    print(f"Grid map (obstacle-aware): {len(nodes)} nodes saved to {filepath}")

def _component_from(adj_list, start):
    visited = set()
    frontier = Queue()
    frontier.enqueue(start)
    while len(frontier) > 0:
        node = frontier.dequeue()
        if node in visited:
            continue
        visited.add(node)
        for _, nb in adj_list.neighbors(node).asList():
            if nb not in visited:
                frontier.enqueue(nb)
    return visited


def largest_component(adj_list, attempts=8, seed=0):
    nodes = list(adj_list.keys())
    rng = random.Random(seed)
    seen_global = set()
    best = set()
    for _ in range(attempts):
        candidates = [n for n in nodes if n not in seen_global
                      and len(adj_list.neighbors(n)) > 1]
        if not candidates:
            break
        comp = _component_from(adj_list, rng.choice(candidates))
        seen_global.update(comp)
        if len(comp) > len(best):
            best = comp
    return best


def generate_comparison_graphs(grid_tile=5):
    os.makedirs("Data/Compare", exist_ok=True)
    obstacleAwareGraph(MergeType.DBSCANMERGE,
                       ADJACENCY_PATH=COMPARISON_GRAPHS["Walkable layers map"],
                       CELLSIZE=10, visualize=False)
    gridMapObstacleAware(COMPARISON_GRAPHS["Grid map"], grid_tile, CELLSIZE=10)
    obstacleBasedMap(COMPARISON_GRAPHS["Obstacle map"], CELLSIZE=10,
                     include_roads=False, visualize=False)
    obstacleBasedMap(COMPARISON_GRAPHS["Obstacle map + roads"], CELLSIZE=10,
                     include_roads=True, visualize=False)
    print("All four comparison graphs generated under Data/Compare/")

def gridNeighbours(idx:int, nodes:list,n:int,debug=False)->Heap:
    neighbours = Heap()
    neighboursPositions = [ idx-n-1, idx-n, idx-n+1,
                            idx -1,         idx+1,
                            idx+n-1, idx+n, idx+n+1]
    straightNeighbours = [1,3,4,6]
    leftNeighbours = [0,3,5]
    rightNeighbours = [2,4,7]
    sqrt2 = 1.414
    # debug = True if idx <2*n else False
    if debug : print(f"finding neighbours for {idx}")
    for j,i in enumerate(neighboursPositions):
        if i<0: 
            if debug :print(f"out of top bound at index {i}")
            continue
        if idx%n==0 and j in leftNeighbours: 
            if debug :print(f"out of left bound at index {i}")
            continue
        if idx%n==n-1 and j in rightNeighbours: 
            if debug :print(f"out of right bound at index {i}")
            continue
        if i>=len(nodes): 
            if debug :print(f"out of bottom bound at index {i}")
            continue
        neighbour = nodes[i]
        if debug :    print(f"neighbour found {neighbour}, position {i}, in relation to index {idx}, it's {j}")
        if j in straightNeighbours: neighbours.add((1,neighbour))
        else: neighbours.add((sqrt2,neighbour))

    return neighbours

def gridMap(filepath, tileSize:int):
    obstacles = loadFromDb.fetch_obstacle_gdfs()
    obstacles = loadFromDb.geodataframe_to_polygon_lists(obstacles)
    obstacles = loadFromDb.remove_near_zero_polygon_outliers(obstacles)
    xs,ys = [],[]
    for polygon in obstacles:
        xs.extend( [p[0] for p in polygon])
        ys.extend( [p[1] for p in polygon])
    minPoint = (min(xs),min(ys))
    maxPoint = (max(xs),max(ys))
    dx,dy = int(maxPoint[0]-minPoint[0]),int(maxPoint[1]-minPoint[1])
    nodes =[]
    print(f"{dx}/{tileSize}={dx/tileSize}")
    print(f"{dy}/{tileSize}={dy/tileSize}")
    print(f"dx: {dx}, dy:{dy}")
    for i in range(0,dy,tileSize):
        for j in range(0,dx,tileSize):
            node = (minPoint[0]+j,minPoint[1]+i)
            nodes.append(node)
    print(f"THERE ARE {len(nodes)} NODES")
    adjacency_list = AdjacencyList(nodes)
    
    neighbourFunc = lambda point: gridNeighbours(
            nodes.index(point),nodes,1+int(dx/tileSize)
        )
    
    buildAdjacencyList(adjacency_list,nodes,neighbourFunc)
    save_adjacency_list(adjacency_list=adjacency_list, filepath=filepath)
    
    tree = KDtree.buildKDtree(nodes)
    labels = fetch_building_names("llyn_bygning_dtu")
    labeledpoints = assignPointsData(tree,labels)
    savePointsDataToFile(labeledpoints,"Data/GridLabeledPoints.json")
    # visualize_graph(adjacency_list,obstacles)

def obstacleAwareGraph(
        mergeType: MergeType, 
        ADJACENCY_PATH = "Data/Adjacency_list_ObstacleAwareGraph.json",
        CELLSIZE = 10,
        visualize=False
    ):
    
    walk_points, polygons = loadFromDb.fetch_points()

    polygon_bboxes = spatial_intersection.precompute_bboxes(polygons)
    spatial_index = spatial_intersection.build_spatial_index(polygons, cell_size=CELLSIZE)

    merged_points = mergePoints(walk_points,mergeType)

    
    graph = {tuple(p): set() for p in merged_points}
    blockedPoints = {tuple(p): set() for p in merged_points} #Use this to track if we already know that a point is blocked (avoid checking twice)
    
    tree = KDtree.buildKDtree(merged_points)
    adjacency_list = AdjacencyList(merged_points)
    neighbourFunc = lambda point: KDtree.KNN_KDtree_obstacles(
            tree=tree, point=point, k=8,
            polygons=polygons, spatial_index=spatial_index,
            polygon_bboxes=polygon_bboxes, cell_size=CELLSIZE,blockedPoints = blockedPoints,
            graph=graph
        )
    
    buildAdjacencyList(
        adjacency_list,
        merged_points,
        neighbourFunc,
        graph
    )

    save_adjacency_list(adjacency_list=adjacency_list, filepath=ADJACENCY_PATH)
    labels = fetch_building_names("llyn_bygning_dtu")
    labeledpoints = assignPointsData(tree,labels)
    for x in labeledpoints.items():
        print(x)
    savePointsDataToFile(labeledpoints,"Data/LabeledPoints.json")
    if visualize:
        visualize_graph(adjacency_list,polygons,labels)

def obstacleIgnoringGraph(
        mergeType: MergeType, 
        ADJACENCY_PATH = "Data/Adjacency_list_ObstacleIgnoringGraph.json"
    ):
    
    walk_points, polygons = loadFromDb.fetch_points()

    merged_points = mergePoints(walk_points,mergeType)
    
    tree = KDtree.buildKDtree(merged_points)
    adjacency_list = AdjacencyList(merged_points)
    neighbourFunc = lambda point: KDtree.KNN_KDtree(tree = tree,point = point,k=32)

    buildAdjacencyList(
        adjacency_list,
        merged_points,
        neighbourFunc
    )

    save_adjacency_list(adjacency_list=adjacency_list, filepath=ADJACENCY_PATH)
    visualize_graph(adjacency_list,polygons)

def assignPointsData(tree,data):
    labeled = {}
    for p,d in data:
        hits = KDtree.KNN_KDtree(tree,p,5)
        labeled[d] = []
        while True:
            hit = hits.extractMax()
            if hit is None: break
            _,p = hit
            labeled.get(d).append(p)
    return labeled



def mergePoints(points,mergeType):
    match mergeType:
        case MergeType.SQUAREBUCKETMERGE:
            squares = grid_merge.intoGrid(points, 10)
            return grid_merge.findCentroid(squares)
        case MergeType.DBSCANMERGE:
            merged = dbscan_merge.merge_points_simpleDbscan(points, eps=3.5, min_samples=1)
            return [tuple(p) for p in merged]
        case MergeType.NOMERGING:
            return [tuple(p) for p in points]
        case _:
            valid = [e.name for e in MergeType if e is not MergeType.DEFAULT]
            raise ValueError(f"Invalid mergeType: {mergeType}. Must be one of: {valid}")

def buildAdjacencyList(
        adjacency_list: AdjacencyList, 
        merged_points, 
        neighbourFunc,
        graph = None
    ):

    print("Looking for neighbours")
    n=len(merged_points)
    if graph is None:
        graph = {tuple(p): set() for p in merged_points}

    for i,point in enumerate(merged_points):
        print(f"\rProgress: {i}/{n}", end="", flush=True)
        
        p = tuple(point)
        KNN = neighbourFunc(point)

        #Add neighbours to point, and point to neighbours
        for distance, coords in KNN.heap[1:]:
            coords = tuple(coords)
            graph[p].add((distance, coords))
            graph[coords].add((distance, p))
    
    # Dump into AdjacencyList at the end
    print("\nConverting to adjacency list...")
    for point, neighbours in graph.items():
        for neighbour in neighbours:
            adjacency_list.insertNeighbour(point, neighbour)

def generate_comparison_graphs(grid_tile=5):
    """Build all four candidate graphs used in the Section 5.1 comparison."""
    os.makedirs("Data/Compare", exist_ok=True)
 
    # 1. Walkable-layer points, obstacle-aware KNN
    obstacleAwareGraph(MergeType.DBSCANMERGE,
                       ADJACENCY_PATH=COMPARISON_GRAPHS["Walkable layers map"],
                       CELLSIZE=10)
    # 2. Grid map
    gridMapObstacleAware(COMPARISON_GRAPHS["Grid map"], grid_tile)
    # 3. Obstacle-offset points, no roads
    obstacleBasedMap(COMPARISON_GRAPHS["Obstacle map"], CELLSIZE=10,
                     include_roads=False, visualize=False)
    # 4. Obstacle-offset points + road network
    obstacleBasedMap(COMPARISON_GRAPHS["Obstacle map + roads"], CELLSIZE=10,
                     include_roads=True, visualize=False)
    print("All four comparison graphs generated under Data/Compare/")


import cProfile
import pstats
import io

if __name__ == "__main__":
    with cProfile.Profile() as pr:
        # showGraph("Data/Data/Adjacency_list_ObstacleAwareGraph.json")
        # showGraph("Data/Data/ObbyMap32.json")
        # generate_comparison_graphs()
        gridMapObstacleAware("Data/Compare/grid.json", tileSize=1, CELLSIZE=10)
    
    stream = io.StringIO()
    stats = pstats.Stats(pr, stream=stream)
    stats.sort_stats(pstats.SortKey.CUMULATIVE)
    stats.print_stats(500)

    lines = stream.getvalue().splitlines()
    
    ALLOWLIST = ["buildadjacencylist", "kdtree", "spatial_intersection", "dbscan_merge", "grid_merge", "heap"]
    
    filtered = [
        line for line in lines
        if any(term in line.lower() for term in ALLOWLIST)
    ]
    
    # Re-attach the header for readability
    header = [l for l in lines if "cumtime" in l.lower() or "ncalls" in l.lower()]
    print("\n".join(header + filtered))