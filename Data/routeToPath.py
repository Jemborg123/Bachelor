# Sometimes a point is chosen which lies outside the calculated route
# Idea for this script is to locate a valid smaller path onto the route
# Ideally we also route to the best point in the route, that is to say sometimes the route starts at a bad node compared to the chosen starting point


import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from Data.utils import *
from Data.Obstacle_algebra.spatial_intersection import check_edge_intersects

def connect_to_path(point, main_path, polygons, spatial_index, cell_size,
                    polygon_bboxes, max_attach_radius=40.0):
    """Attach `point` to the path vertex that minimises the total journey and
    has a clear line of sight to the click. Returns (connector, attach_index)."""
    point = tuple(point)
    n = len(main_path)

    # prefix[k] = path distance from main_path[0] to main_path[k]
    prefix = [0.0] * n
    for k in range(1, n):
        prefix[k] = prefix[k - 1] + euclideanDistance(main_path[k - 1], main_path[k])

    # only attach within local reach (keep it a short connector, not a shortcut)
    near = [k for k in range(n)
            if euclideanDistance(point, main_path[k]) <= max_attach_radius]
    if not near:                                     # click far from the route
        k = min(range(n), key=lambda k: euclideanDistance(point, main_path[k]))
        return [point, tuple(main_path[k])], k

    # rank by hop-minus-progress, then take the best with a clear straight line
    near.sort(key=lambda k: euclideanDistance(point, main_path[k]) - prefix[k])
    for k in near:
        v = tuple(main_path[k])
        if not check_edge_intersects(point, v, polygons, spatial_index,
                                     cell_size, polygon_bboxes):
            return [point, v], k

    # nothing nearby is visible (boxed in) -> nearest reachable vertex
    k = min(near, key=lambda k: euclideanDistance(point, main_path[k]))
    return [point, tuple(main_path[k])], k

def build_continuous_path(source_grid, target_grid, main_path, polygons,
                          spatial_index, cell_size, polygon_bboxes,
                          max_attach_radius=40.0):
    """source -> connector -> middle of the A* path -> connector -> target."""
    if not main_path:
        return ([tuple(source_grid), tuple(target_grid)],
                euclideanDistance(source_grid, target_grid))

    src_conn, i_s = connect_to_path(source_grid, main_path, polygons, spatial_index,
                                    cell_size, polygon_bboxes, max_attach_radius)
    rev = list(reversed(main_path))
    tgt_conn, j = connect_to_path(target_grid, rev, polygons, spatial_index,
                                  cell_size, polygon_bboxes, max_attach_radius)
    i_t = len(main_path) - 1 - j

    middle = (list(main_path[i_s:i_t + 1]) if i_s <= i_t
              else list(reversed(main_path[i_t:i_s + 1])))
    full = list(src_conn) + [tuple(p) for p in middle] + list(reversed(tgt_conn))

    cleaned = [full[0]]
    for p in full[1:]:
        if p != cleaned[-1]:
            cleaned.append(p)
    total = sum(euclideanDistance(cleaned[k], cleaned[k + 1])
                for k in range(len(cleaned) - 1))
    return cleaned, total

def project_point_onto_segment(p, a, b):
    """Closest point to p on segment a->b, plus t in [0, 1].
    Uses the utils vector ops so the math matches the rest of the project."""
    ab = subtract(b, a)
    seg_len_sq = dot(ab, ab)
    if seg_len_sq == 0.0:
        return a, 0.0
    t = dot(subtract(p, a), ab) / seg_len_sq
    t = max(0.0, min(1.0, t))
    return add(a, scaled(ab, t)), t

def project_point_onto_path(point, path):
    """Nearest point on polyline `path` to `point`.
    Returns (closest_xy, distance, seg_index, t); distance in grid units ≈ metres."""
    best = None  # (closest_xy, distance, seg_index, t)
    for i in range(len(path) - 1):
        cp, t = project_point_onto_segment(point, path[i], path[i + 1])
        d = euclideanDistance(point, cp)
        if best is None or d < best[1]:
            best = (cp, d, i, t)
    return best