def segments_intersect(p1, p2, p3, p4):
    """Check if segment p1-p2 intersects segment p3-p4 using cross products."""
    d1x = p2[0] - p1[0]
    d1y = p2[1] - p1[1]
    d2x = p4[0] - p3[0]
    d2y = p4[1] - p3[1]

    cross = d1x * d2y - d1y * d2x
    if cross == 0:
        return False  # parallel / collinear

    dx = p3[0] - p1[0]
    dy = p3[1] - p1[1]

    t = (dx * d2y - dy * d2x) / cross
    u = (dx * d1y - dy * d1x) / cross

    return 0.0 <= t <= 1.0 and 0.0 <= u <= 1.0


def line_intersects_polygon(a, b, polygon):
    """
    Returns True if segment a-b intersects any edge of the polygon.
    polygon: list of [x, y] points (open or closed ring)
    """
    n = len(polygon)
    if n < 2:
        return False

    # Check each edge of the polygon
    for i in range(n - 1):
        if segments_intersect(a, b, polygon[i], polygon[i + 1]):
            return True

    # Close the ring if not already closed
    if polygon[0] != polygon[-1]:
        if segments_intersect(a, b, polygon[-1], polygon[0]):
            return True

    return False