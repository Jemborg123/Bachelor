import requests
import numpy as np
import geopandas as gpd
from geopandas import GeoDataFrame as GDF
from utils import point_to_square

WFS_URL   = "https://casgis.azurewebsites.net/geoserver/dtu/wfs"
WMS_URL   = "https://casgis.azurewebsites.net/geoserver/dtu/wms"
WORKSPACE = "dtu"

WALKABLE_LAYERS = [
    "eksisterende_haver", "eksisterende_torve", "forareal",
    "ldtu_parkering_sensade", "llyn_andre_arealer", "llyn_bro",
    "llyn_graes", "llyn_invasivearter", "llyn_parkering_areal",
    "llyn_torv_plads", "llyn_vejkant", "mellemareal", "parker",
    "fortove", "llyn_adgangsvej", "llyn_brandvej",
    "mobilitetsnetvaerkfodgaengercykel", "mobilitetsnetvaerkdrift",
    "mobilitetsnetvaerkbil"
]

OBSTACLE_LAYERS = [
    "llyn_byggefelt_construction",  "llyn_byggefelt_east", 
    "llyn_bygning_andre", "llyn_bygning_dtu", "llyn_stoettemur"#, "llyn_trae"
]

# Tuning parameters
MERGE_DISTANCE  = 5.0    # metres — vertices closer than this are merged
OBSTACLE_BUFFER = 0.5    # metres — edges must stay this far from obstacles
K_NEIGHBOURS    = 8      # nearest walkable neighbours to consider per vertex
OUTLIER_RADIUS  = 500    # metres — for outlier filtering in visualisation
OUTLIER_MIN_NBR = 5      # minimum neighbours within OUTLIER_RADIUS to keep node

# CRS of the GeoServer data — adjust if path appears in wrong location
SOURCE_CRS = "EPSG:25832"

# ---------------------------------------------------------------------------
# GeoServer fetch layer data
# ---------------------------------------------------------------------------

def fetch_wfs_layer(layer_name):
    """Fetch a single WFS layer as a GeoDataFrame."""
    params = {
        'service':      'WFS',
        'version':      '1.0.0',
        'request':      'GetFeature',
        'typeName':     f'{WORKSPACE}:{layer_name}',
        'outputFormat': 'application/json'
    }
    try:
        response = requests.get(WFS_URL, params=params, timeout=60)
        response.raise_for_status()
        gdf = gpd.read_file(response.content)
        print(f"  ✓ {layer_name}: {len(gdf)} features")
        print(gdf)
        return gdf
    except Exception as e:
        print(f"  ✗ {layer_name}: {e}")
        return None

def fetch_points():
    walkable_gdfs = fetch_walkable_gdfs()
    obstacle_gdfs = fetch_obstacle_gdfs()

    raw_vertices = geodataframe_to_vertex_lists(walkable_gdfs)
    raw_obstacles = geodataframe_to_polygon_lists(obstacle_gdfs)

    filtered_vertices = remove_near_zero_point_outliers(raw_vertices)
    filtered_obstacles = remove_near_zero_polygon_outliers(raw_obstacles)

    return (filtered_vertices,filtered_obstacles)

def fetch_walkable_gdfs():
    print("\n📥 Fetching WALKABLE layers …")
    return fetch_gdfs_from_layer(WALKABLE_LAYERS)

def fetch_obstacle_gdfs():
    print("\n📥 Fetching OBSTACLE layers …")
    return fetch_gdfs_from_layer(OBSTACLE_LAYERS)

def fetch_gdfs_from_layer(layer):
    gdfs = []
    for name in layer:
        gdf = fetch_wfs_layer(name)
        if gdf is not None:
            gdfs.append(gdf)
    return gdfs

# ---------------------------------------------------------------------------
# Data cleaning
# ---------------------------------------------------------------------------

def remove_near_zero_point_outliers(points, x_threshold=10000, y_threshold=10000):
    """
    Remove points near zero (outliers) and keep the main cluster.
    
    Args:
        points: List of (x, y) points
        x_threshold: Minimum x value to keep (points with x < threshold are removed)
        y_threshold: Minimum y value to keep (points with y < threshold are removed)
    
    Returns:
        Filtered points without near-zero outliers
    """
    points = np.array(points)
    
    # Keep points that are above thresholds in both dimensions
    mask = (points[:, 0] > x_threshold) & (points[:, 1] > y_threshold)
    
    filtered_points = points[mask]
    
    print(f"Original points: {len(points)}")
    print(f"Removed {len(points) - len(filtered_points)} near-zero outliers")
    print(f"Kept {len(filtered_points)} points in main cluster")
    print(f"X range: [{filtered_points[:, 0].min():.0f}, {filtered_points[:, 0].max():.0f}]")
    print(f"Y range: [{filtered_points[:, 1].min():.0f}, {filtered_points[:, 1].max():.0f}]")
    
    return filtered_points

def remove_near_zero_polygon_outliers(polygons, x_threshold=10000, y_threshold=10000):
    """
    Remove polygons near zero (outliers) and keep the main cluster.
    A polygon is removed if any of its points are below the thresholds.

    Args:
        polygons: List of polygons, where each polygon is a list of [x, y] points
        x_threshold: Minimum x value to keep
        y_threshold: Minimum y value to keep

    Returns:
        Filtered polygons without near-zero outliers
    """
    filtered = []
    for polygon in polygons:
        xs = [p[0] for p in polygon]
        ys = [p[1] for p in polygon]
        if min(xs) > x_threshold and min(ys) > y_threshold:
            filtered.append(polygon)

    print(f"Original polygons: {len(polygons)}")
    print(f"Removed {len(polygons) - len(filtered)} near-zero outlier polygons")
    print(f"Kept {len(filtered)} polygons in main cluster")

    return filtered

# ---------------------------------------------------------------------------
# Vertex extraction
# ---------------------------------------------------------------------------

def extract_vertices_from_gdf(gdf):
    """
    Return an (N, 2) numpy array of all unique XY coordinate pairs.
    Z coordinates are stripped if present.
    """
    coords = set()

    def _collect(geom):
        if geom is None or geom.is_empty:
            return
        if hasattr(geom, 'exterior'):       # Polygon
            coords.update((x, y) for x, y, *_ in geom.exterior.coords)
            for interior in geom.interiors:
                coords.update((x, y) for x, y, *_ in interior.coords)
        elif hasattr(geom, 'geoms'):        # Multi* / GeometryCollection
            for part in geom.geoms:
                _collect(part)
        elif hasattr(geom, 'coords'):       # LineString / Point
            coords.update((x, y) for x, y, *_ in geom.coords)

    for geom in gdf.geometry:
        _collect(geom)

    return np.array(list(coords))

def geodataframe_to_vertex_lists(gdfs):
    print("\n📐 Extracting walkable vertices …")
    arrays = [extract_vertices_from_gdf(gdf) for gdf in gdfs if len(gdf) > 0]
    if not arrays:
        print("❌ No walkable vertices found. Aborting.")
        return None

    raw_vertices = np.vstack(arrays)
    return raw_vertices
# ---------------------------------------------------------------------------
# Polygon extraction
# ---------------------------------------------------------------------------

def geodataframe_to_polygon_lists(gdfs, point_buffer=1.0):
    """
    Takes a GeoDataFrame (or list of GeoDataFrames) and returns
    a flat list of all polygons as coordinate lists.
    """
    all_polygons = []
    geometries = getGeometries(gdfs)
    for geomtry in geometries:
        for geom in geomtry:
            all_polygons.extend(geometry_to_polygons(geom, point_buffer))
    return all_polygons

def getGeometries(gdfs):
    geometries = []
    for gdf in gdfs:
        geometries.append(gdf.geometry)
    return geometries

def geometry_to_polygons(geometry:GDF.geometry, buffer):
    polygons=[]
    if geometry is None or geometry.is_empty:
        return polygons
    geom_type = geometry.geom_type

    if geom_type == "Point":
        coords = list(geometry.coords)[0]
        polygons.append(point_to_square(coords, buffer))

    elif geom_type == "MultiPoint":
        for pt in geometry.geoms:
            coords = list(pt.coords)[0]
            polygons.append(point_to_square(coords, buffer))

    elif geom_type in ("Polygon", "Polygon Z"):
        exterior = [[x, y] for x, y, *_ in geometry.exterior.coords]
        polygons.append(exterior)

    elif geom_type in ("MultiPolygon", "MultiPolygon Z"):
        for poly in geometry.geoms:
            exterior = [[x, y] for x, y, *_ in poly.exterior.coords]
            polygons.append(exterior)

    elif geom_type in ("LineString", "LineString Z"):
        coords = [[x, y] for x, y, *_ in geometry.coords]
        polygons.append(coords)

    elif geom_type in ("MultiLineString", "MultiLineString Z"):
        for line in geometry.geoms:
            coords = [[x, y] for x, y, *_ in line.coords]
            polygons.append(coords)

    elif geom_type == "GeometryCollection":
        for geom in geometry.geoms:
            polygons.extend(geometry_to_polygons(geom, buffer))

    return polygons