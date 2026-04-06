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
from Data.utils import save_adjacency_list,load_adjacency_list,AdjacencyList,LinkedList, Heap, visualize_graph


def showGraph(ADJACENCY_PATH="Data/Adjacency_list_ObstacleIgnoringGraph.json"):
    print("script started")
    adjacency_list,success = load_adjacency_list(ADJACENCY_PATH)
    if success:
        obstacles = loadFromDb.fetch_obstacle_gdfs()
        polygons = loadFromDb.geodataframe_to_polygon_lists(obstacles)
        filtered_polygons = loadFromDb.remove_near_zero_polygon_outliers(polygons)
        print("succes, showing graph")
        visualize_graph(adjacency_list,filtered_polygons)
    else:
        print("No adjacency list found at",ADJACENCY_PATH,", building graph from scratch...")
        obstacleAwareGraph(MergeType.SQUAREBUCKETMERGE)
        # obstacleIgnoringGraph(MergeType.SQUAREBUCKETMERGE)

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
    visualize_graph(adjacency_list,polygons)

def obstacleIgnoringGraph(
        mergeType: MergeType, 
        ADJACENCY_PATH = "Data/Adjacency_list_ObstacleIgnoringGraph.json"
    ):
    
    walk_points, polygons = loadFromDb.fetch_points()

    merged_points = mergePoints(walk_points,mergeType)
    
    tree = KDtree.buildKDtree(merged_points)
    adjacency_list = AdjacencyList(merged_points)
    neighbourFunc = lambda point: KDtree.KNN_KDtree(tree = tree,point = point,k=8)

    buildAdjacencyList(
        adjacency_list,
        merged_points,
        neighbourFunc
    )

    save_adjacency_list(adjacency_list=adjacency_list, filepath=ADJACENCY_PATH)
    visualize_graph(adjacency_list,polygons)

def mergePoints(points,mergeType):
    match mergeType:
        case MergeType.SQUAREBUCKETMERGE:
            squares = grid_merge.intoGrid(points, 10)
            return grid_merge.findCentroid(squares)
        case MergeType.DBSCANMERGE:
            return dbscan_merge.merge_points_simpleDbscan(points, eps=5, min_samples=1)
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
        showGraph()
    
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