from intersections import line_intersects_polygon

def build_spatial_index(polygons, cell_size):
    """
    Bucket each polygon into all grid cells its bounding box overlaps.
    Returns a dict: (cell_x, cell_y) -> [polygon_indices]
    """
    index = {}
    for i, polygon in enumerate(polygons):
        xs = [p[0] for p in polygon]
        ys = [p[1] for p in polygon]
        min_cx = int(min(xs) // cell_size)
        max_cx = int(max(xs) // cell_size)
        min_cy = int(min(ys) // cell_size)
        max_cy = int(max(ys) // cell_size)

        for cx in range(min_cx, max_cx + 1):
            for cy in range(min_cy, max_cy + 1):
                key = (cx, cy)
                if key not in index:
                    index[key] = []
                index[key].append(i)
    return index


def get_cells_along_segment(a, b, cell_size):
    """
    Returns all grid cells a segment a-b passes through
    using a grid traversal algorithm.
    """
    cells = set()

    x0, y0 = a[0] / cell_size, a[1] / cell_size
    x1, y1 = b[0] / cell_size, b[1] / cell_size

    cx, cy = int(x0), int(y0)
    end_cx, end_cy = int(x1), int(y1)

    dx = x1 - x0
    dy = y1 - y0

    step_x = 1 if dx > 0 else -1
    step_y = 1 if dy > 0 else -1

    # How far along the segment to cross a vertical/horizontal boundary
    t_max_x = ((cx + (1 if step_x > 0 else 0)) - x0) / dx if dx != 0 else float('inf')
    t_max_y = ((cy + (1 if step_y > 0 else 0)) - y0) / dy if dy != 0 else float('inf')

    t_delta_x = abs(1.0 / dx) if dx != 0 else float('inf')
    t_delta_y = abs(1.0 / dy) if dy != 0 else float('inf')

    while True:
        cells.add((cx, cy))
        if cx == end_cx and cy == end_cy:
            break
        if t_max_x < t_max_y:
            t_max_x += t_delta_x
            cx += step_x
        else:
            t_max_y += t_delta_y
            cy += step_y

    return cells


def check_edge_intersects(a, b, polygons, spatial_index, cell_size, polygon_bboxes):
    """Check if segment a-b intersects any polygon, using spatial index."""
    cells = get_cells_along_segment(a, b, cell_size)

    candidate_indices = set()
    for cell in cells:
        if cell in spatial_index:
            candidate_indices.update(spatial_index[cell])

    for num,i in enumerate(candidate_indices):
        # Bbox check first (precomputed)
        min_px, max_px, min_py, max_py = polygon_bboxes[i]
        min_ax = min(a[0], b[0]);  max_ax = max(a[0], b[0])
        min_ay = min(a[1], b[1]);  max_ay = max(a[1], b[1])
        if (max_ax < min_px or min_ax > max_px or
            max_ay < min_py or min_ay > max_py):
            continue
        if line_intersects_polygon(a, b, polygons[i]):
            # print("intersection found after, compared",num+1,"polygons, found in",len(cells),"cells")
            # input("Press Enter to continue...")
            return True
    return False


def precompute_bboxes(polygons):
    bboxes = []
    for polygon in polygons:
        xs = [p[0] for p in polygon]
        ys = [p[1] for p in polygon]
        bboxes.append((min(xs), max(xs), min(ys), max(ys)))
    return bboxes