import sys
import os
import random
import argparse

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
sys.setrecursionlimit(10**6)

from Data.utils import load_adjacency_list, euclideanDistance
from Data.Database_access.loadFromDb import (
    fetch_obstacle_gdfs, geodataframe_to_polygon_lists,
    remove_near_zero_polygon_outliers, fetch_building_names,
)
import Data.KDtree as KDtree
import Data.Obstacle_algebra.spatial_intersection as spatial_intersection
from Data.routeToPath import build_continuous_path
from Algorithms.ALT import *
from Data.BuildGraph import largest_component, point_in_polygon

COMPARISON_GRAPHS = {
    "Walkable layers map":  "Data/Compare/walkable_layers.json",
    "Grid map":             "Data/Compare/grid.json",
    "Obstacle map":         "Data/Compare/obstacle.json",
    "Obstacle map + roads": "Data/Compare/obstacle_roads.json",
}
CELL_SIZE = 10


def load_obstacles():
    obstacles = fetch_obstacle_gdfs()
    polygons = geodataframe_to_polygon_lists(obstacles)
    polygons = remove_near_zero_polygon_outliers(polygons)
    bboxes = spatial_intersection.precompute_bboxes(polygons)
    index = spatial_intersection.build_spatial_index(polygons, cell_size=CELL_SIZE)
    return polygons, bboxes, index


def first_invalid_edge(path, polygons, index, bboxes):
    for a, b in zip(path, path[1:]):
        if spatial_intersection.check_edge_intersects(
                a, b, polygons, index, CELL_SIZE, bboxes):
            return (a, b)
    return None


def endpoint_inside_obstacle(point, polygons, index):
    cx = int(point[0] // CELL_SIZE)
    cy = int(point[1] // CELL_SIZE)
    for i in index.get((cx, cy), []):
        if point_in_polygon(point, polygons[i]):
            return True
    return False


def count_edges(graph):
    return sum(len(list(graph.neighbors(n))) for n in graph.nodes()) // 2


def prune_graph(adjacency_list):
    keep = largest_component(adjacency_list)
    for node in list(adjacency_list.keys()):
        if node not in keep:
            adjacency_list.popPoint(node)
    return adjacency_list


def analyse_graph(name, path, queries, polygons, bboxes, index, diag=0):
    adjacency_list, ok = load_adjacency_list(path)
    if not ok:
        print(f"  ! could not load {path}")
        return None

    prune_graph(adjacency_list)
    graph = adjGraph(adjacency_list)
    nodes = list(graph.nodes())
    tree = KDtree.buildKDtree(graph.getPoints())

    n_vertices = len(nodes)
    n_edges = count_edges(graph)
    mem_kb = os.path.getsize(path) / 1024.0

    found, valid, lengths, snap = 0, 0, [], []
    shown = 0
    for (src_xy, dst_xy) in queries:
        s = graph.closest(tree, tuple(src_xy))
        t = graph.closest(tree, tuple(dst_xy))
        if s is None or t is None:
            continue
        snap.append(euclideanDistance(src_xy, s))
        snap.append(euclideanDistance(dst_xy, t))
        
        h_adj = lambda p1, p2: adj_euclidean(p1,p2)
        cost, route, _ = new_astar(graph, s, t,h_adj)
        if route is None or cost == float('inf'):
            continue
        found += 1

        bad = first_invalid_edge(route, polygons, index, bboxes)
        full, total = build_continuous_path(
            src_xy, dst_xy, route, polygons, index, CELL_SIZE, bboxes)
        if bad is None:
            valid += 1
            lengths.append(total)
        elif shown < diag:
            shown += 1
            a, b = bad
            print(f"    [diag] {name}: invalid edge {a} -> {b}")
            print(f"           src inside obstacle: "
                  f"{endpoint_inside_obstacle(src_xy, polygons, index)}, "
                  f"dst inside: {endpoint_inside_obstacle(dst_xy, polygons, index)}")

    q = len(queries)
    return {
        "name": name,
        "vertices": n_vertices,
        "edges": n_edges,
        "memory_kb": mem_kb,
        "connectivity": found / q if q else 0.0,
        "validity": valid / found if found else 0.0,
        "avg_length": sum(lengths) / len(lengths) if lengths else float('nan'),
        "avg_snap": sum(snap) / len(snap) if snap else float('nan'),
        "decided": len(lengths),
    }


def make_queries(n_pairs, seed=0):
    labels = fetch_building_names("llyn_bygning_dtu")
    pts = [tuple(p) for p, _ in labels]
    rng = random.Random(seed)
    return [tuple(rng.sample(pts, 2)) for _ in range(n_pairs)]


def latex_row(r):
    avg = f"{r['avg_length']:.1f}" if r['avg_length'] == r['avg_length'] else "---"
    return (f"    {r['name']:<21}& {r['vertices']:>6} & {r['edges']:>7} & "
            f"{r['memory_kb']:>6.0f} & {r['connectivity']*100:>3.0f}\\% & "
            f"{r['validity']*100:>3.0f}\\% & {avg:>7} \\\\")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--queries", type=int, default=200)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--diag", type=int, default=0)
    args = ap.parse_args()

    print("Loading obstacles ...")
    polygons, bboxes, index = load_obstacles()
    print(f"Building {args.queries} shared queries ...")
    queries = make_queries(args.queries, args.seed)

    results = []
    for name, path in COMPARISON_GRAPHS.items():
        print(f"Analysing {name} ...")
        r = analyse_graph(name, path, queries, polygons, bboxes, index, args.diag)
        if r:
            results.append(r)

    print("\n=== Summary ===")
    for r in results:
        print(f"{r['name']:<22} V={r['vertices']:>6} E={r['edges']:>7} "
              f"mem={r['memory_kb']:>6.0f}KB conn={r['connectivity']*100:4.0f}% "
              f"valid={r['validity']*100:4.0f}% avglen={r['avg_length']:7.1f} "
              f"snap={r['avg_snap']:5.1f}m (n={r['decided']})")

    print("\n=== LaTeX table rows ===")
    for r in results:
        print(latex_row(r))


if __name__ == "__main__":
    main()