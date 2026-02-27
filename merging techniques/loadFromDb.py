import requests
import numpy as np
import geopandas as gpd

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
    "llyn_byggefelt_100", "llyn_byggefelt_75", "llyn_byggefelt_construction",
    "llyn_byggefelt_east", "llyn_byggefelt_parkering", "llyn_byggeplads",
    "llyn_bygning_andre", "llyn_bygning_dtu", "llyn_stoettemur", "llyn_trae"
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

# ---------------------------------------------------------------------------
# Top-level graph builder
# ---------------------------------------------------------------------------


def fetch_points():
    print("\n📥 Fetching WALKABLE layers …")
    walkable_gdfs = []
    for name in WALKABLE_LAYERS:
        gdf = fetch_wfs_layer(name)
        if gdf is not None and len(gdf) > 0:
            walkable_gdfs.append(gdf)

    print("\n📥 Fetching OBSTACLE layers …")
    obstacle_gdfs = []
    for name in OBSTACLE_LAYERS:
        gdf = fetch_wfs_layer(name)
        if gdf is not None:
            obstacle_gdfs.append(gdf)

    print("\n📐 Extracting walkable vertices …")
    arrays = [extract_vertices_from_gdf(gdf) for gdf in walkable_gdfs if len(gdf) > 0]
    if not arrays:
        print("❌ No walkable vertices found. Aborting.")
        return None

    raw_vertices = np.vstack(arrays)

    return (raw_vertices,obstacle_gdfs)

def minmaxxy(points):
    min_x = max_x = points[0][0]
    min_y = max_y = points[0][1]
    
    # Loop through the remaining points
    for x, y in points[1:]:
        # Update min and max for x
        if x < min_x:
            min_x = x
        if x > max_x:
            max_x = x
        
        # Update min and max for y
        if y < min_y:
            min_y = y
        if y > max_y:
            max_y = y
    
    print(f"X: min = {min_x}, max = {max_x}")
    print(f"Y: min = {min_y}, max = {max_y}")

def remove_near_zero_outliers(points, x_threshold=10000, y_threshold=10000):
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
