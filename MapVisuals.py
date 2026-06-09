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

def create_adj_path_map(adj_list, path, cost, source, target, filename="adj_path_map.html"):
    """Create a Folium map for adjacency list path."""
    import folium
    import numpy as np
    import geopandas as gpd
    from MapVisuals import detect_crs
    from shapely.geometry import Point
        
    source_crs = detect_crs()
    # Reproject path nodes to WGS84
    path_points = gpd.GeoDataFrame(
    [{'node': i} for i, n in enumerate(path)],
    geometry=[Point(n[0], n[1]) for n in path], 
    crs=source_crs
).to_crs("EPSG:4326")
    
    path_latlon = [(row.geometry.y, row.geometry.x) for _, row in path_points.iterrows()]
    
    if len(path_latlon) == 0:
        print(f"  ⚠️ No valid coordinates found in path, skipping map")
        return

    mid_lat = np.mean([p[0] for p in path_latlon])
    mid_lon = np.mean([p[1] for p in path_latlon])

    # Check for NaN values
    if np.isnan(mid_lat) or np.isnan(mid_lon):
        print(f"  ⚠️ Invalid map center coordinates, skipping map")
        return
    
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
    
    # Add markers
    folium.Marker(
        location=path_latlon[0],
        popup=f"Start",
        icon=folium.Icon(color='green', icon='play')
    ).add_to(m)
    
    folium.Marker(
        location=path_latlon[-1],
        popup=f"End",
        icon=folium.Icon(color='red', icon='stop')
    ).add_to(m)
    
    folium.LayerControl().add_to(m)
    m.save(filename)
    print(f"  ✅ Map saved to '{filename}'")


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

def create_comprehensive_comparison_map(G_nx, adj_list, nx_results, adj_results, 
                                          source_nx, target_nx, source_adj, target_adj,
                                          filename="comprehensive_comparison.html"):
    """
    Create a single map showing ALL algorithms.
    NetworkX algorithms: red
    AdjacencyList algorithms: blue
    """
    filepath = os.path.join(MAPS_FOLDER, filename)

    print(f"\n🗺️  Creating comprehensive comparison map: {filename}")
    map_start = time.time()
    
    # Detect CRS
    source_crs = detect_crs()
    
    # Color mapping
    nx_colors = {
        'Dijkstra (NX)': 'red',
        'A* (NX)': 'red', 
        'Bidirectional A* (NX)': 'red',
        'ALT (NX)': 'red'
    }
    
    adj_colors = {
        'Dijkstra (Adj)': 'blue',
        'A* (Adj)': 'blue', 
        'Bidirectional A* (Adj)': 'blue',
        'ALT (Adj)': 'blue'
    }
    
    # ========== COLLECT ALL COORDINATES FOR CENTERING ==========
    all_lats = []
    all_lons = []
    
    # Get NetworkX path coordinates (already in lat/lon after conversion)
    nx_paths_latlon = {}
    for name, (path, cost, _) in nx_results.items():
        if path and len(path) > 0:
            try:
                path_points = gpd.GeoDataFrame(
                    [{'node': n, 'geometry': Point(G_nx.nodes[n]['x'], G_nx.nodes[n]['y'])} for n in path],
                    crs=source_crs
                ).to_crs("EPSG:4326")
                latlon = [(row.geometry.y, row.geometry.x) for _, row in path_points.iterrows()]
                nx_paths_latlon[name] = (latlon, cost)
                for lat, lon in latlon:
                    all_lats.append(lat)
                    all_lons.append(lon)
            except Exception as e:
                print(f"    ⚠️ Error converting {name}: {e}")
    
    # Get AdjacencyList path coordinates (convert properly!)
    adj_paths_latlon = {}
    for name, (path, cost, _) in adj_results.items():
        if path and len(path) > 0:
            try:
                # Convert adjacency list points (UTM) to lat/lon using GeoDataFrame
                points = [Point(node[0], node[1]) for node in path]
                path_gdf = gpd.GeoDataFrame(geometry=points, crs=source_crs)
                path_gdf = path_gdf.to_crs("EPSG:4326")
                latlon = [(row.geometry.y, row.geometry.x) for _, row in path_gdf.iterrows()]
                adj_paths_latlon[name] = (latlon, cost)
                for lat, lon in latlon:
                    all_lats.append(lat)
                    all_lons.append(lon)
            except Exception as e:
                print(f"    ⚠️ Error converting {name}: {e}")
    
    # Center map on all paths combined
    if all_lats and all_lons:
        mid_lat = np.mean(all_lats)
        mid_lon = np.mean(all_lons)
    else:
        mid_lat, mid_lon = 55.7858, 12.5215
    
    print(f"  Map centered at: ({mid_lat:.5f}, {mid_lon:.5f})")
    
    # Create base map
    m = folium.Map(location=[mid_lat, mid_lon], zoom_start=15, tiles='OpenStreetMap')
    
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
    
    # ========== ADD NETWORKX PATHS (red) ==========
    print("  Adding NetworkX paths (red)...")
    for name, (latlon, cost) in nx_paths_latlon.items():
        folium.PolyLine(
            locations=latlon,
            color=nx_colors.get(name, 'red'),
            weight=4,
            opacity=0.7,
            tooltip=f"{name}: {cost:.1f} m",
            popup=f"{name}<br>Distance: {cost:.1f}m<br>Nodes: {len(latlon)}"
        ).add_to(m)
        print(f"    ✅ Added {name}")
    
    # ========== ADD ADJACENCYLIST PATHS (blue) ==========
    print("  Adding AdjacencyList paths (blue)...")
    for name, (latlon, cost) in adj_paths_latlon.items():
        folium.PolyLine(
            locations=latlon,
            color=adj_colors.get(name, 'blue'),
            weight=3,
            opacity=0.6,
            tooltip=f"{name}: {cost:.1f} m",
            popup=f"{name}<br>Distance: {cost:.1f}m<br>Nodes: {len(latlon)}"
        ).add_to(m)
        print(f"    ✅ Added {name}")
    
    # ========== ADD MARKERS ==========
    # NetworkX markers (already in lat/lon)
    if source_nx is not None:
        try:
            start_point = gpd.GeoDataFrame(
                [{'node': source_nx, 'geometry': Point(G_nx.nodes[source_nx]['x'], G_nx.nodes[source_nx]['y'])}],
                crs=source_crs
            ).to_crs("EPSG:4326")
            start_lat, start_lon = start_point.geometry.y.iloc[0], start_point.geometry.x.iloc[0]
            folium.Marker(
                location=[start_lat, start_lon],
                popup=f"Start (NetworkX node {source_nx})",
                icon=folium.Icon(color='green', icon='play')
            ).add_to(m)
        except:
            pass
    
    if target_nx is not None:
        try:
            end_point = gpd.GeoDataFrame(
                [{'node': target_nx, 'geometry': Point(G_nx.nodes[target_nx]['x'], G_nx.nodes[target_nx]['y'])}],
                crs=source_crs
            ).to_crs("EPSG:4326")
            end_lat, end_lon = end_point.geometry.y.iloc[0], end_point.geometry.x.iloc[0]
            folium.Marker(
                location=[end_lat, end_lon],
                popup=f"End (NetworkX node {target_nx})",
                icon=folium.Icon(color='red', icon='stop')
            ).add_to(m)
        except:
            pass
    
    # AdjacencyList markers (convert from UTM)
    if source_adj is not None:
        try:
            src_gdf = gpd.GeoDataFrame(geometry=[Point(source_adj[0], source_adj[1])], crs=source_crs)
            src_gdf = src_gdf.to_crs("EPSG:4326")
            src_lat, src_lon = src_gdf.geometry.y.iloc[0], src_gdf.geometry.x.iloc[0]
            folium.Marker(
                location=[src_lat, src_lon],
                popup=f"Start (AdjacencyList)",
                icon=folium.Icon(color='lightgreen', icon='info-sign')
            ).add_to(m)
        except:
            pass
    
    if target_adj is not None:
        try:
            tgt_gdf = gpd.GeoDataFrame(geometry=[Point(target_adj[0], target_adj[1])], crs=source_crs)
            tgt_gdf = tgt_gdf.to_crs("EPSG:4326")
            tgt_lat, tgt_lon = tgt_gdf.geometry.y.iloc[0], tgt_gdf.geometry.x.iloc[0]
            folium.Marker(
                location=[tgt_lat, tgt_lon],
                popup=f"End (AdjacencyList)",
                icon=folium.Icon(color='lightred', icon='info-sign')
            ).add_to(m)
        except:
            pass
    
    # Add legend
    legend_html = '''
    <div style="position: fixed; bottom: 50px; right: 50px; z-index: 1000; background-color: white; padding: 10px; border: 2px solid grey; border-radius: 5px; font-size: 12px;">
        <strong>Legend</strong><br>
        <span style="color: red;">■</span> NetworkX Algorithms<br>
        <span style="color: blue;">■</span> AdjacencyList Algorithms<br>
        <hr>
        <span style="color: green;">●</span> Start (NetworkX)<br>
        <span style="color: red;">●</span> End (NetworkX)<br>
        <span style="color: lightgreen;">●</span> Start (AdjacencyList)<br>
        <span style="color: lightred;">●</span> End (AdjacencyList)
    </div>
    '''
    m.get_root().html.add_child(folium.Element(legend_html))
    
    folium.LayerControl().add_to(m)
    
    # Save map
    m.save(filepath)
    map_time = time.time() - map_start
    print(f"  ✅ Comprehensive comparison map saved to '{filepath}' ({map_time:.2f} seconds)")
    
    return m