import requests
import numpy as np
import geopandas as gpd
from geopandas import GeoDataFrame as GDF

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
# Top-level graph builder
# ---------------------------------------------------------------------------


def fetch_layer_data():
    print("\n📥 Fetching OBSTACLE layers …")
    obstacle_gdfs = []
    for name in OBSTACLE_LAYERS:
        gdf = fetch_wfs_layer(name)
        if gdf is not None:
            obstacle_gdfs.append(gdf)


    return obstacle_gdfs

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

def point_to_square(point,buffer):
    square=[]
    for i in [-buffer,buffer]:
        for j in [-buffer,buffer]:
            x,y=point[0]+i,point[1]+j
            square.append([x,y])
    return square

    # geometries = []
    # if gdf is None or gdf.is_empty:
    #         return
    # if hasattr(gdf, 'exterior'):       # Polygon
    #     geometries.append(g for g in gdf.exterior)
    #     for interior in gdf.interiors:
    #         geometries.append(interior)
    # elif hasattr(gdf, 'geoms'):        # Multi* / gdfetryCollection
    #     for part in gdf.geoms:
    #         geometries.extend(getGeometries(part))
    # elif hasattr(gdf, 'coords'):       # LineString / Point
    #         geometries.update((x, y) for x, y, *_ in gdf.coords)
    # return geometries

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