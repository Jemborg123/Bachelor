import requests
import json
import xml.etree.ElementTree as ET
import numpy as np
import geopandas as gpd
import networkx as nx
from shapely.geometry import LineString
from shapely.ops import unary_union
from scipy.spatial import KDTree
import pickle
import random
import folium
import pyproj
import matplotlib.pyplot as plt
import heapq  # 👈 For priority queue
import math   # 👈 For log2 in complexity analysis

# ---------------------------------------------------------------------------
# Global config
# ---------------------------------------------------------------------------

FETCH_LAYER_NAMES = False
FETCH_LAYER_DATA  = False
BUILD_GRAPH       = False
RUN_DIJKSTRA      = False

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
# Config loader
# ---------------------------------------------------------------------------

def load_config(config_file):
    global FETCH_LAYER_NAMES, FETCH_LAYER_DATA, BUILD_GRAPH, RUN_DIJKSTRA
    try:
        with open(config_file, 'r') as f:
            config = json.load(f)
        FETCH_LAYER_NAMES = config.get('fetch_layer_names', 'false').lower() == 'true'
        FETCH_LAYER_DATA  = config.get('fetch_layer_data',  'false').lower() == 'true'
        BUILD_GRAPH       = config.get('build_graph',       'false').lower() == 'true'
        RUN_DIJKSTRA      = config.get('run_dijkstra',      'false').lower() == 'true'
        print(f"Config: FETCH_LAYER_NAMES={FETCH_LAYER_NAMES}, FETCH_LAYER_DATA={FETCH_LAYER_DATA}, "
              f"BUILD_GRAPH={BUILD_GRAPH}, RUN_DIJKSTRA={RUN_DIJKSTRA}")
    except FileNotFoundError:
        print(f"Error: '{config_file}' not found — using defaults.")
    except json.JSONDecodeError:
        print(f"Error: Invalid JSON in '{config_file}'.")
    except Exception as e:
        print(f"Error loading config: {e}")


# ---------------------------------------------------------------------------
# GeoServer helpers
# ---------------------------------------------------------------------------

def get_layers_from_geoserver():
    params  = {'service': 'WMS', 'version': '1.3.0', 'request': 'GetCapabilities'}
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        print(f"📡 Fetching capabilities from: {WMS_URL}")
        response = requests.get(WMS_URL, params=params, headers=headers, timeout=15)
        response.raise_for_status()
        root = ET.fromstring(response.content)
        for elem in root.iter():
            if '}' in elem.tag:
                elem.tag = elem.tag.split('}', 1)[1]
        layers = []
        for layer in root.findall('.//Layer[Name]'):
            name_elem  = layer.find('Name')
            title_elem = layer.find('Title')
            layer_name  = name_elem.text
            layer_title = title_elem.text if title_elem is not None else layer_name
            bbox_info = {}
            bbox = layer.find('LatLonBoundingBox')
            if bbox is not None:
                bbox_info = {k: bbox.get(k) for k in ('minx', 'miny', 'maxx', 'maxy')}
            layers.append({
                'name':      layer_name.split(':')[-1],
                'full_name': layer_name,
                'title':     layer_title,
                'workspace': WORKSPACE,
                'bbox':      bbox_info
            })
        return layers
    except requests.exceptions.RequestException as e:
        print(f"❌ Network error: {e}")
    except ET.ParseError as e:
        print(f"❌ XML parse error: {e}")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
    return None


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


def fetchLayerNamesAndSave():
    print("\n📋 Fetching layer names …")
    layers = get_layers_from_geoserver()
    if layers:
        print(f"✅ Found {len(layers)} layers!")
        with open('dtu_layers.json', 'w', encoding='utf-8') as f:
            json.dump(layers, f, indent=2, ensure_ascii=False)
        print("💾 Saved to 'dtu_layers.json'")
    else:
        print("❌ Failed to fetch layers.")


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
# Vertex merging
# ---------------------------------------------------------------------------

def merge_nearby_vertices(vertices, merge_distance=MERGE_DISTANCE):
    """
    Greedy KDTree merge: cluster vertices within `merge_distance` of each
    other into a single centroid point.
    """
    if len(vertices) == 0:
        return vertices

    tree    = KDTree(vertices)
    visited = np.zeros(len(vertices), dtype=bool)
    merged  = []

    for i in range(len(vertices)):
        if visited[i]:
            continue
        neighbours = tree.query_ball_point(vertices[i], merge_distance)
        cluster    = vertices[neighbours]
        merged.append(cluster.mean(axis=0))
        visited[neighbours] = True

    result = np.array(merged)
    print(f"  Merged {len(vertices)} → {len(result)} vertices (merge_distance={merge_distance} m)")
    return result


# ---------------------------------------------------------------------------
# Obstacle geometry
# ---------------------------------------------------------------------------

def build_obstacle_geometry(obstacle_gdfs, buffer_distance=OBSTACLE_BUFFER):
    """Union all obstacle geometries and buffer them."""
    all_geoms = []
    for gdf in obstacle_gdfs:
        if gdf is not None and len(gdf) > 0:
            all_geoms.extend(gdf.geometry.tolist())

    if not all_geoms:
        print("  ⚠️  No obstacle geometries — edges won't be filtered.")
        return None

    unioned  = unary_union(all_geoms)
    buffered = unioned.buffer(buffer_distance)
    print(f"  Obstacle union buffered by {buffer_distance} m")
    return buffered


# ---------------------------------------------------------------------------
# Graph construction
# ---------------------------------------------------------------------------

def build_walkability_graph(walkable_vertices, obstacle_geom,
                             k=K_NEIGHBOURS, merge_dist=MERGE_DISTANCE):
    """
    Build a NetworkX graph from walkable vertices.
    For each vertex, attempt to connect to the k nearest unobstructed neighbours.
    Edges are weighted by Euclidean distance.
    """
    n = len(walkable_vertices)
    print(f"\n🔨 Building graph for {n} vertices (k={k}) …")

    tree = KDTree(walkable_vertices)
    G    = nx.Graph()

    for i, (x, y) in enumerate(walkable_vertices):
        G.add_node(i, x=float(x), y=float(y), pos=(float(x), float(y)))

    edges_added  = 0
    edges_tested = 0

    for i in range(n):
        dists, idxs = tree.query(walkable_vertices[i], k=k + 1)
        connected   = 0

        for dist, j in zip(dists, idxs):
            if j == i:
                continue
            if G.has_edge(i, j):
                connected += 1
                if connected >= k:
                    break
                continue

            edges_tested += 1
            p1        = walkable_vertices[i]
            p2        = walkable_vertices[j]
            edge_line = LineString([p1, p2])

            if obstacle_geom is not None and edge_line.intersects(obstacle_geom):
                continue

            G.add_edge(i, j, weight=float(dist))
            edges_added += 1
            connected   += 1
            if connected >= k:
                break

    print(f"  Tested {edges_tested} candidate edges → kept {edges_added}")
    print(f"  Graph: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges")
    return G


# ---------------------------------------------------------------------------
# Top-level graph builder
# ---------------------------------------------------------------------------

def fetch_and_build_graph():
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
    print(f"  Raw vertices: {len(raw_vertices)}")
    vertices = merge_nearby_vertices(raw_vertices, merge_distance=MERGE_DISTANCE)

    print("\n🚧 Building obstacle geometry …")
    obstacle_geom = build_obstacle_geometry(obstacle_gdfs, buffer_distance=OBSTACLE_BUFFER)

    G = build_walkability_graph(vertices, obstacle_geom,
                                k=K_NEIGHBOURS, merge_dist=MERGE_DISTANCE)

    with open('walkability_graph.pkl', 'wb') as f:
        pickle.dump(G, f)
    print("\n💾 Graph saved to 'walkability_graph.pkl'")

    np.save('walkable_vertices.npy', vertices)
    print("💾 Vertices saved to 'walkable_vertices.npy'")

    return G


# ---------------------------------------------------------------------------
# Outlier filtering (shared between dijkstra + matplotlib visualisation)
# ---------------------------------------------------------------------------

def filter_outliers(G):
    """Return the list of kept nodes after removing spatial outliers."""
    all_x  = np.array([d['x'] for _, d in G.nodes(data=True)])
    all_y  = np.array([d['y'] for _, d in G.nodes(data=True)])
    coords = np.stack([all_x, all_y], axis=1)

    tree   = KDTree(coords)
    counts = np.array([len(tree.query_ball_point(c, r=OUTLIER_RADIUS)) for c in coords])
    mask   = counts >= OUTLIER_MIN_NBR

    nodes       = list(G.nodes())
    kept_nodes  = [n for n, m in zip(nodes, mask) if m]
    print(f"  Kept {len(kept_nodes)} / {len(nodes)} nodes after outlier filtering")
    return kept_nodes


# ---------------------------------------------------------------------------
# CRS conversion
# ---------------------------------------------------------------------------

def to_latlon(x, y, transformer):
    lon, lat = transformer.transform(x, y)
    return lat, lon



# ---------------------------------------------------------------------------
# CUSTOM DIJKSTRA IMPLEMENTATION
# ---------------------------------------------------------------------------

def dijkstra_custom(graph, source, target, weight='weight'):
    """
    Custom implementation of Dijkstra's algorithm.
    
    Time Complexity: O((V + E) log V) with binary heap
    Space Complexity: O(V)
    
    Args:
        graph: NetworkX graph object
        source: source node
        target: target node
        weight: edge attribute to use as weight
    
    Returns:
        tuple: (path list, distance, stats dictionary)
    """
    stats = {
        'nodes_visited': 0,
        'edges_relaxed': 0,
        'heap_operations': 0
    }
    
    # Initialize distances and predecessors
    dist = {node: float('inf') for node in graph.nodes()}
    prev = {node: None for node in graph.nodes()}
    dist[source] = 0
    
    # Priority queue: (distance, node)
    pq = [(0, source)]
    stats['heap_operations'] += 1
    
    # Visited set
    visited = set()
    
    while pq:
        # Extract min
        current_dist, current = heapq.heappop(pq)
        stats['heap_operations'] += 1
        
        # Skip if we've already found a better path
        if current_dist > dist[current]:
            continue
        
        # Mark as visited
        if current not in visited:
            visited.add(current)
            stats['nodes_visited'] += 1
        
        # Early termination if we reached target
        if current == target:
            break
        
        # Relax all neighbors
        for neighbor in graph.neighbors(current):
            edge_weight = graph[current][neighbor].get(weight, 1)
            stats['edges_relaxed'] += 1
            
            new_dist = current_dist + edge_weight
            
            if new_dist < dist[neighbor]:
                dist[neighbor] = new_dist
                prev[neighbor] = current
                heapq.heappush(pq, (new_dist, neighbor))
                stats['heap_operations'] += 1
    
    # Reconstruct path
    path = []
    if dist[target] < float('inf'):
        node = target
        while node is not None:
            path.append(node)
            node = prev[node]
        path.reverse()
    
    return path, dist[target], stats

# ---------------------------------------------------------------------------
# Time complexity
# ---------------------------------------------------------------------------

def analyze_complexity(V, E, stats, elapsed_time):
    """
    Analyze and print complexity information.
    """
    print("\n📊 COMPLEXITY ANALYSIS:")
    print(f"  Graph size: |V| = {V}, |E| = {E}")
    print(f"  Theoretical: O((|V| + |E|) log |V|) = O(({V} + {E}) log {V})")
    print(f"  ≈ {((V + E) * math.log2(V)):.0f} operations (estimate)")
    print(f"\n  Actual performance:")
    print(f"    Nodes visited: {stats['nodes_visited']} ({stats['nodes_visited']/V*100:.1f}% of |V|)")
    print(f"    Edges relaxed: {stats['edges_relaxed']} ({stats['edges_relaxed']/E*100:.1f}% of |E|)")
    print(f"    Heap ops: {stats['heap_operations']}")
    print(f"    Time: {elapsed_time*1000:.2f} ms")
    
    # Empirical complexity verification
    theoretical_ops = (V + E) * math.log2(V)
    actual_ops = stats['edges_relaxed'] + stats['heap_operations']
    ratio = actual_ops / theoretical_ops if theoretical_ops > 0 else 0
    print(f"\n  Complexity verification:")
    print(f"    Theoretical ops ~ {theoretical_ops:.0f}")
    print(f"    Actual ops: {actual_ops}")
    print(f"    Ratio: {ratio:.3f} (should be ~1 for average case)")
# ---------------------------------------------------------------------------
# Dijkstra + Folium map
# ---------------------------------------------------------------------------

def run_dijkstra_and_map(G):
    print("\n🔍 Running Dijkstra (custom implementation) …")
    total_start = time.time()

    # Filter outliers
    filter_start = time.time()
    kept_nodes = filter_outliers(G)
    filter_time = time.time() - filter_start

    # Get largest connected component
    subgraph = G.subgraph(kept_nodes)
    components = list(nx.connected_components(subgraph))
    largest = list(max(components, key=len))
    print(f"  Largest component: {len(largest)} nodes")

    # Pick random source and target
    node_a, node_b = random.sample(largest, 2)
    print(f"  Source: node {node_a} @ ({G.nodes[node_a]['x']:.2f}, {G.nodes[node_a]['y']:.2f})")
    print(f"  Target: node {node_b} @ ({G.nodes[node_b]['x']:.2f}, {G.nodes[node_b]['y']:.2f})")

    # Run custom Dijkstra
    V = G.number_of_nodes()
    E = G.number_of_edges()
    
    dijkstra_start = time.time()
    path, cost, stats = dijkstra_custom(G, node_a, node_b, weight='weight')
    dijkstra_time = time.time() - dijkstra_start
    
    print(f"  ✅ Path found: {len(path)} nodes, {cost:.1f} m total")
    
    # Analyze complexity
    analyze_complexity(V, E, stats, dijkstra_time)

    # Detect CRS
    print("\n  Detecting CRS from WFS …")
    crs_start = time.time()
    params = {
        'service': 'WFS', 'version': '1.0.0', 'request': 'GetFeature',
        'typeName': f'{WORKSPACE}:fortove', 'outputFormat': 'application/json',
        'maxFeatures': '1'
    }
    sample_gdf = gpd.read_file(requests.get(WFS_URL, params=params).content)
    source_crs = sample_gdf.crs
    crs_time = time.time() - crs_start
    print(f"  Detected CRS: {source_crs}")

    # Reproject path to WGS84 for mapping
    from shapely.geometry import Point
    reproject_start = time.time()
    path_points = gpd.GeoDataFrame(
        [{'node': n, 'geometry': Point(G.nodes[n]['x'], G.nodes[n]['y'])} for n in path],
        crs=source_crs
    ).to_crs("EPSG:4326")
    reproject_time = time.time() - reproject_start

    path_latlon = [(row.geometry.y, row.geometry.x) for _, row in path_points.iterrows()]

    # Create Folium map
    print("\n🗺️  Creating map …")
    map_start = time.time()
    
    # Center map on path midpoint
    mid_lat = np.mean([p[0] for p in path_latlon])
    mid_lon = np.mean([p[1] for p in path_latlon])
    
    m = folium.Map(location=[mid_lat, mid_lon], zoom_start=17, tiles='OpenStreetMap')

    # Add WMS building layer
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
        tooltip=f"Shortest path: {cost:.1f} m"
    ).add_to(m)

    # Add start marker
    folium.Marker(
        location=path_latlon[0],
        popup=f"Start (node {node_a})",
        icon=folium.Icon(color='green', icon='play')
    ).add_to(m)

    # Add end marker
    folium.Marker(
        location=path_latlon[-1],
        popup=f"End (node {node_b})",
        icon=folium.Icon(color='red', icon='stop')
    ).add_to(m)

    # Add layer control
    folium.LayerControl().add_to(m)

    # Save map
    m.save('dijkstra_path_custom.html')
    map_time = time.time() - map_start
    print(f"  ⏱️  Map creation time: {map_time:.2f} seconds")

    total_time = time.time() - total_start
    print(f"\n⏱️  TOTAL DIJKSTRA + MAP TIME: {total_time:.2f} seconds")
    print("💾 Map saved to 'dijkstra_path_custom.html'")

    return path, cost, stats
# ---------------------------------------------------------------------------
# Matplotlib visualisation (optional, for debugging)
# ---------------------------------------------------------------------------

def visualise_graph(G):
    print("\n🎨 Rendering graph …")
    kept_nodes  = filter_outliers(G)
    kept_set    = set(kept_nodes)
    kept_coords = np.array([[G.nodes[n]['x'], G.nodes[n]['y']] for n in kept_nodes])

    x_min, x_max = kept_coords[:,0].min(), kept_coords[:,0].max()
    y_min, y_max = kept_coords[:,1].min(), kept_coords[:,1].max()

    node_pos = {
        n: (
            (G.nodes[n]['x'] - x_min) / (x_max - x_min),
            (G.nodes[n]['y'] - y_min) / (y_max - y_min)
        )
        for n in kept_nodes
    }

    norm_x = np.array([node_pos[n][0] for n in kept_nodes])
    norm_y = np.array([node_pos[n][1] for n in kept_nodes])

    fig, ax = plt.subplots(figsize=(14, 14))

    for u, v in G.edges():
        if u in kept_set and v in kept_set:
            x1, y1 = node_pos[u]
            x2, y2 = node_pos[v]
            ax.plot([x1, x2], [y1, y2], color='gray', linewidth=0.3, alpha=0.3)

    ax.scatter(norm_x, norm_y, s=2, c='steelblue', zorder=5)
    ax.set_xlim(-0.05, 1.05)
    ax.set_ylim(-0.05, 1.05)
    ax.set_aspect('equal')
    ax.set_title(f"Walkability Graph — {len(kept_nodes)} nodes", fontsize=13)
    plt.tight_layout()
    plt.savefig('graph_preview.png', dpi=150)
    plt.show()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    load_config('src\master_config.json')

    if FETCH_LAYER_NAMES:
        fetchLayerNamesAndSave()

    if BUILD_GRAPH:
        fetch_and_build_graph()

    if RUN_DIJKSTRA:
        with open('walkability_graph.pkl', 'rb') as f:
            G = pickle.load(f)
        run_dijkstra_and_map(G)

    print("\n✅ Done")


if __name__ == "__main__":
    main()