print("script started")
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
import matplotlib.pyplot as plt
import numpy as np
import Data.Obstacle_algebra.fetch_obstacles as fetch_obstacles
from Data.Obstacle_algebra.KNN_obstacle_search import KNN_KDtree_obstacles
import Data.merging_techniques.loadFromDb as loadFromDb
import Data.merging_techniques.dbscan_merge as dbscan_merge

import Data.merging_techniques.grid_merge as grid_merge
import Data.merging_techniques.KDtree as KDtree
import Data.Obstacle_algebra.spatial_intersection as spatial_intersection
from Data.utils import save_adjacency_list,load_adjacency_list,AdjacencyList,LinkedList

def main():
    print("script started")
    ADJACENCY_PATH = "Data/Adjacency_list_IGNOREOBSTACLES.json"
    adjacency_list,success = load_adjacency_list(ADJACENCY_PATH)
    if success:
        
        obstacles = fetch_obstacles.fetch_layer_data()
        
        polygons = fetch_obstacles.geodataframe_to_polygon_lists(obstacles)
        polygons = fetch_obstacles.remove_near_zero_polygon_outliers(polygons)
        print("succes, showing graph")
        visualize_graph(adjacency_list,polygons)
    else:
        print("No adjacency list found, building from scratch...")

        walk_points, obstacles = loadFromDb.fetch_points()
        filtered_points = loadFromDb.remove_near_zero_outliers(walk_points)

        polygons = fetch_obstacles.geodataframe_to_polygon_lists(obstacles)
        polygons = fetch_obstacles.remove_near_zero_polygon_outliers(polygons)

        polygon_bboxes = spatial_intersection.precompute_bboxes(polygons)
        spatial_index = spatial_intersection.build_spatial_index(polygons, cell_size=10.0)

        squares = grid_merge.intoGrid(filtered_points,10)
        merged_points = grid_merge.findCentroid(squares)
        # simple_dbscan_merged_points5 = dbscan_merge.merge_points_simpleDbscan(filtered_points, eps=5, min_samples=1)

        tree = KDtree.buildKDtree(merged_points)

        adjacency_list = AdjacencyList(merged_points)
        buildAdjacencyList(
            adjacency_list,
            merged_points,
            tree,
            polygons, 
            spatial_index, 
            polygon_bboxes
        )

        save_adjacency_list(adjacency_list=adjacency_list, filepath=ADJACENCY_PATH)
        visualize_graph(adjacency_list,polygons)

def buildAdjacencyList(
        adjacency_list: AdjacencyList, 
        merged_points, 
        tree, 
        polygons, 
        spatial_index, 
        polygon_bboxes
    ):
    print("Looking for neighbours")
    n=len(merged_points)
    for i,point in enumerate(merged_points):
        print(f"\rProgress: {i}/{n}", end="", flush=True)
        # KNN = KNN_KDtree_obstacles(
        #     tree=tree, point=point, k=16,
        #     polygons=polygons, spatial_index=spatial_index,
        #     polygon_bboxes=polygon_bboxes, cell_size=10,
        #     adjacency_list=adjacency_list
        # )
        KNN = [None for _ in range(8)]
        KDtree.KNNsearch(tree, point, KNN)

        #Add neighbours to point
        p = tuple(point)
        neighbours = list(KNN)
        for coords, distance in neighbours:
            adjacency_list.insertNeighbour(p, (tuple(coords), distance))

        #pre append point to neighbours
        for  neighbour in KNN:
            key = tuple(neighbour[0])
            dist = neighbour[1]
            neighbourList = adjacency_list.neighbors(p)
            if not neighbourList.has(key):
                adjacency_list.insertNeighbour(key,(p,dist))

def visualize_graph(adjacency_list, polygons=None):
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
        for coords, distance in neighbours.asList():
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

    ax.set_aspect('equal')
    ax.set_title(f"Graph — {adjacency_list.length()} nodes, {len(drawn_edges)} edges")
    plt.tight_layout()
    plt.show()


if __name__ == "__main__":
    main()