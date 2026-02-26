"""
Map visualization module for DTU pathfinding.
Creates Folium maps with paths and building overlays.
"""

import folium
import geopandas as gpd
import numpy as np
import requests
from shapely.geometry import Point
import time
import os

# Constants
WFS_URL = "https://casgis.azurewebsites.net/geoserver/dtu/wfs"
WORKSPACE = "dtu"
MAPS_FOLDER = "Maps"

def detect_crs():
    """Detect CRS from GeoServer by fetching a sample layer."""
    params = {
        'service': 'WFS', 'version': '1.0.0', 'request': 'GetFeature',
        'typeName': f'{WORKSPACE}:fortove', 'outputFormat': 'application/json',
        'maxFeatures': '1'
    }
    sample_gdf = gpd.read_file(requests.get(WFS_URL, params=params).content)
    return sample_gdf.crs


def create_path_map(graph, path, cost, source_node, target_node, filename="path_map.html"):
    """
    Create a Folium map showing the path.
    
    Args:
        graph: NetworkX graph with node positions
        path: List of node IDs in the path
        cost: Total path distance
        source_node: Source node ID
        target_node: Target node ID
        filename: Output HTML filename
    
    Returns:
        Folium map object
    """
    filepath = os.path.join(MAPS_FOLDER, filename)
    
    print(f"\n🗺️  Creating map: {filename}")
    map_start = time.time()
    
    # Detect CRS
    source_crs = detect_crs()
    
    # Reproject path nodes to WGS84
    path_points = gpd.GeoDataFrame(
        [{'node': n, 'geometry': Point(graph.nodes[n]['x'], graph.nodes[n]['y'])} for n in path],
        crs=source_crs
    ).to_crs("EPSG:4326")
    
    path_latlon = [(row.geometry.y, row.geometry.x) for _, row in path_points.iterrows()]
    
    # Center map on path midpoint
    mid_lat = np.mean([p[0] for p in path_latlon])
    mid_lon = np.mean([p[1] for p in path_latlon])
    
    # Create base map
    m = folium.Map(location=[mid_lat, mid_lon], zoom_start=17, tiles='OpenStreetMap')
    
    # Add DTU buildings WMS layer
    folium.WmsTileLayer(
        url="https://casgis.azurewebsites.net/geoserver/dtu/wms",
        name='DTU Buildings',
        layers='dtu:llyn_bygning_dtu',
        fmt='image/png',
        transparent=True,
        version='1.1.1',
        attr='GeoServer DTU',
        overlay=True,
        control=True
    ).add_to(m)
    
    # Add path
    folium.PolyLine(
        locations=path_latlon,
        color='red',
        weight=5,
        opacity=0.8,
        tooltip=f"Path: {cost:.1f} m"
    ).add_to(m)
    
    # Add start marker
    folium.Marker(
        location=path_latlon[0],
        popup=f"Start (node {source_node})",
        icon=folium.Icon(color='green', icon='play')
    ).add_to(m)
    
    # Add end marker
    folium.Marker(
        location=path_latlon[-1],
        popup=f"End (node {target_node})",
        icon=folium.Icon(color='red', icon='stop')
    ).add_to(m)
    
    # Add layer control
    folium.LayerControl().add_to(m)
    
    # Save map
    m.save(filepath)
    map_time = time.time() - map_start
    print(f"  ✅ Map saved to '{filepath}' ({map_time:.2f} seconds)")
    
    return m


def create_comparison_map(graph, results_dict, filename="comparison_map.html"):
    """
    Create a map comparing multiple algorithms.
    
    Args:
        graph: NetworkX graph with node positions
        results_dict: Dictionary of {algorithm_name: (path, cost)}
        filename: Output HTML filename
    """
    filepath = os.path.join(MAPS_FOLDER, filename)

    print(f"\n🗺️  Creating comparison map: {filename}")
    map_start = time.time()
    
    # Use first path for centering
    first_path = list(results_dict.values())[0][0]
    
    # Detect CRS
    source_crs = detect_crs()
    
    # Reproject all paths
    paths_latlon = {}
    for algo_name, (path, cost) in results_dict.items():
        path_points = gpd.GeoDataFrame(
            [{'node': n, 'geometry': Point(graph.nodes[n]['x'], graph.nodes[n]['y'])} for n in path],
            crs=source_crs
        ).to_crs("EPSG:4326")
        paths_latlon[algo_name] = [(row.geometry.y, row.geometry.x) for _, row in path_points.iterrows()]
    
    # Center map on first path midpoint
    first_latlon = paths_latlon[list(paths_latlon.keys())[0]]
    mid_lat = np.mean([p[0] for p in first_latlon])
    mid_lon = np.mean([p[1] for p in first_latlon])
    
    # Create base map
    m = folium.Map(location=[mid_lat, mid_lon], zoom_start=17, tiles='OpenStreetMap')
    
    # Add DTU buildings
    folium.WmsTileLayer(
        url="https://casgis.azurewebsites.net/geoserver/dtu/wms",
        name='DTU Buildings',
        layers='dtu:llyn_bygning_dtu',
        fmt='image/png',
        transparent=True,
        version='1.1.1',
        attr='GeoServer DTU',
        overlay=True,
        control=True
    ).add_to(m)
    
    # Color map for different algorithms
    colors = ['red', 'blue', 'green', 'purple', 'orange', 'darkred', 'cadetblue']
    
    # Add each path
    for i, (algo_name, latlon) in enumerate(paths_latlon.items()):
        color = colors[i % len(colors)]
        cost = results_dict[algo_name][1]
        
        folium.PolyLine(
            locations=latlon,
            color=color,
            weight=4,
            opacity=0.7,
            tooltip=f"{algo_name}: {cost:.1f} m",
            popup=f"{algo_name}"
        ).add_to(m)
    
    # Add start marker (from first path)
    folium.Marker(
        location=first_latlon[0],
        popup="Start",
        icon=folium.Icon(color='green', icon='play')
    ).add_to(m)
    
    # Add end marker (from first path)
    folium.Marker(
        location=first_latlon[-1],
        popup="End",
        icon=folium.Icon(color='red', icon='stop')
    ).add_to(m)
    
    # Add layer control
    folium.LayerControl().add_to(m)
    
    # Save map
    m.save(filepath)
    map_time = time.time() - map_start
    print(f"  ✅ Comparison map saved to '{filepath}' ({map_time:.2f} seconds)")
    
    return m

# Constants for outlier filtering
OUTLIER_RADIUS = 500
OUTLIER_MIN_NBR = 5

def filter_outliers(G):
    """Return the list of kept nodes after removing spatial outliers."""
    from scipy.spatial import KDTree
    import time
    import numpy as np
    
    filter_start = time.time()
    
    all_x = np.array([d['x'] for _, d in G.nodes(data=True)])
    all_y = np.array([d['y'] for _, d in G.nodes(data=True)])
    coords = np.stack([all_x, all_y], axis=1)

    tree = KDTree(coords)
    counts = np.array([len(tree.query_ball_point(c, r=OUTLIER_RADIUS)) for c in coords])
    mask = counts >= OUTLIER_MIN_NBR

    nodes = list(G.nodes())
    kept_nodes = [n for n, m in zip(nodes, mask) if m]
    filter_time = time.time() - filter_start
    print(f"  Kept {len(kept_nodes)} / {len(nodes)} nodes after outlier filtering")
    print(f"  ⏱️  Filtering time: {filter_time:.4f} seconds")
    
    return kept_nodes