from utils import (
    dot, add, scaled, length, normalized, perpendicular,
    is_clockwise, edge_vector,
    without_closing_duplicate, without_zero_length_edges,
)


def outward_unit_normals(ring):
    outward_sign = -1.0 if is_clockwise(ring) else 1.0
    return [
        scaled(normalized(perpendicular(edge_vector(ring, index))), outward_sign)
        for index in range(len(ring))
    ]

def mitre_vector(incoming_normal, outgoing_normal):
    bisector = add(incoming_normal, outgoing_normal)
    reach = dot(bisector, incoming_normal)
    if reach <= 1e-9:
        return None
    return scaled(bisector, 1.0 / reach)

def bevelled_corner(vertex, incoming_normal, outgoing_normal, distance):
    return [
        add(vertex, scaled(incoming_normal, distance)),
        add(vertex, scaled(outgoing_normal, distance)),
    ]

def offset_corner(vertex, incoming_normal, outgoing_normal, distance, max_mitre_ratio):
    mitre = mitre_vector(incoming_normal, outgoing_normal)
    if mitre is None or length(mitre) > max_mitre_ratio:
        return bevelled_corner(vertex, incoming_normal, outgoing_normal, distance)
    return [add(vertex, scaled(mitre, distance))]

def offset_polygon_outward(polygon, distance=0.1, max_mitre_ratio=2.0):
    """Push a polygon outward by `distance`. Accepts an open or closed ring,
    returns the offset vertices as a list of (x, y) tuples."""
    ring = without_zero_length_edges(without_closing_duplicate(polygon))
    if len(ring) < 3:
        return [tuple(point) for point in ring]

    edge_normals = outward_unit_normals(ring)
    offset_vertices = []
    for index, vertex in enumerate(ring):
        incoming_normal = edge_normals[index - 1]
        outgoing_normal = edge_normals[index]
        offset_vertices.extend(
            offset_corner(vertex, incoming_normal, outgoing_normal, distance, max_mitre_ratio)
        )
    return offset_vertices
