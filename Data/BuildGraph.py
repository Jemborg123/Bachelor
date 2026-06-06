print("script started")
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import Data.Database_access.loadFromDb as loadFromDb
import Data.merging_techniques.dbscan_merge as dbscan_merge
from Data.merging_techniques.merge_types import MergeType
import Data.merging_techniques.grid_merge as grid_merge
import Data.KDtree as KDtree
import Data.Obstacle_algebra.spatial_intersection as spatial_intersection
from Data.utils import save_adjacency_list,load_adjacency_list,AdjacencyList,LinkedList, Heap, visualize_graph, savePointsDataToFile, euclideanDistance
from Database_access.loadFromDb import fetch_building_names
import Data.Obstacle_algebra.polygon_offset as polygon_offset

def showGraph(ADJACENCY_PATH="Data/Adjacency_list_DBSCANMERGED.json"):
    print("script started")
    adjacency_list,success = load_adjacency_list(ADJACENCY_PATH)
    if success:
        obstacles = loadFromDb.fetch_obstacle_gdfs()
        polygons = loadFromDb.geodataframe_to_polygon_lists(obstacles)
        filtered_polygons = loadFromDb.remove_near_zero_polygon_outliers(polygons)
        print("succes, showing graph")
        labels = fetch_building_names("llyn_bygning_dtu")
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

def obstacleBasedMap(filepath,CELLSIZE):
    obstacles = loadFromDb.fetch_obstacle_gdfs()
    obstacles = loadFromDb.geodataframe_to_polygon_lists(obstacles)
    polygons = loadFromDb.remove_near_zero_polygon_outliers(obstacles)
    polygon_bboxes = spatial_intersection.precompute_bboxes(polygons)
    spatial_index = spatial_intersection.build_spatial_index(polygons, cell_size=CELLSIZE)

    nodes = []
    for poly in polygons:
        nodes.extend(polygon_offset.offset_polygon_outward(poly, 1))
    
    nodes = mergePoints(nodes, MergeType.DBSCANMERGE)

    road = loadFromDb.fetch_gdfs_from_layer(["mobilitetsnetvaerkfodgaengercykel", "mobilitetsnetvaerkdrift", "mobilitetsnetvaerkbil"])
    road_lines = loadFromDb.geodataframe_to_polyline_lists(road)
    road_lines = loadFromDb.remove_near_zero_polygon_outliers(road_lines)

    road_verts = loadFromDb.geodataframe_to_vertex_lists(road)
    road_verts_cleaned =loadFromDb.remove_near_zero_point_outliers(road_verts)
    
    nodes = list(dict.fromkeys(tuple(p) for p in nodes))
    
    nodes.extend( list(dict.fromkeys(tuple(p) for p in road_verts_cleaned)))
    
    graph = {tuple(p): set() for p in nodes}
    blockedPoints = {tuple(p): set() for p in nodes} #Use this to track if we already know that a point is blocked (avoid checking twice)
    
    tree = KDtree.buildKDtree(nodes)
    adjacency_list = AdjacencyList(nodes)
    neighbourFunc = lambda point: KDtree.KNN_KDtree_obstacles(
            tree=tree, point=point, k=8,
            polygons=polygons, spatial_index=spatial_index,
            polygon_bboxes=polygon_bboxes, cell_size=CELLSIZE,blockedPoints = blockedPoints,
            graph=graph
        )
    
    add_road_network(adjacency_list, road_lines) 
    buildAdjacencyList(
        adjacency_list,
        nodes,
        neighbourFunc,
        graph
    )
    
    save_adjacency_list(adjacency_list=adjacency_list, filepath=filepath)
    visualize_graph(adjacency_list,polygons)


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
        CELLSIZE = 10
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
            merged = dbscan_merge.merge_points_simpleDbscan(points, eps=3, min_samples=1)
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



import cProfile
import pstats
import io

if __name__ == "__main__":
    with cProfile.Profile() as pr:
        # showGraph("Data/Data/Adjacency_list_ObstacleAwareGraph.json")
        showGraph("Data/Data/ObbyMap.json")
    
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