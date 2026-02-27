import requests
from sklearn.cluster import OPTICS, DBSCAN
import numpy as np
import geopandas as gpd
import matplotlib.pyplot as plt

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

def intoGrid(points,SQUARE_SIZE = 5):
    squares = {}
    for x, y in points:
        # Calculate which square this point belongs to
        # Integer division to find the grid coordinates
        grid_x = x // SQUARE_SIZE
        grid_y = y // SQUARE_SIZE
        
        # Create a unique key for this square
        square_key = (grid_x, grid_y)
        
        # If this square doesn't exist yet, create it
        if square_key not in squares:
            squares[square_key] = []
        
        # Add the point to its square
        squares[square_key].append((x, y))
    return squares

def printSquare(squares,SQUARE_SIZE = 5):
    print("Points sorted into 5×5 squares:")
    print("-" * 40)
    stoppoint = 10
    i=0
    for square, pts in sorted(squares.items()):
        i+=1
        if i >= stoppoint: break
        grid_x, grid_y = square
        x_range = f"[{grid_x*SQUARE_SIZE}, {(grid_x+1)*SQUARE_SIZE})"
        y_range = f"[{grid_y*SQUARE_SIZE}, {(grid_y+1)*SQUARE_SIZE})"
        print(f"Square {square} (x:{x_range}, y:{y_range}): {pts}")

def findCentroid(squares):
    centroids = []
    for square_points in squares.values():
        if square_points:  # Skip empty squares
            # Calculate centroid (average of x and y coordinates)
            n = len(square_points)
            sum_x = sum(p[0] for p in square_points)
            sum_y = sum(p[1] for p in square_points)
            
            centroid_x = sum_x / n
            centroid_y = sum_y / n
            
            centroids.append((centroid_x, centroid_y))
    
    return centroids

def plot_with_density(points, title="Point Distribution", 
                      bins=30, bandwidth=None, 
                      show_scatter=True, show_contour=True,
                      figsize=(14, 6)):
    """
    Create a plot with points and density map side by side.
    
    Args:
        points: List of (x, y) points
        title: Main title for the plot
        bins: Number of bins for histogram (int or [x_bins, y_bins])
        bandwidth: Bandwidth for KDE (None for automatic)
        show_scatter: Whether to show scatter plot alongside density
        show_contour: Whether to show contour lines on density plot
        figsize: Figure size (width, height)
    """
    # Convert to numpy array for easier manipulation
    points = np.array(points)
    x = points[:, 0]
    y = points[:, 1]
    
    if show_scatter:
        # Create figure with two subplots
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=figsize)
        
        # Plot 1: Scatter plot
        ax1.scatter(x, y, c='blue', alpha=0.6, s=1, edgecolors='white', linewidth=0.5)
        ax1.set_xlabel('X')
        ax1.set_ylabel('Y')
        ax1.set_title(f'Scatter Plot (n={len(points)})')
        ax1.grid(True, alpha=0.3)
        ax1.set_aspect('equal', adjustable='box')
        
        # Plot 2: Density map
        ax2 = create_density_plot(ax2, x, y, bins, bandwidth, show_contour)
        
    else:
        # Just create density plot
        fig, ax = plt.subplots(1, 1, figsize=figsize)
        ax = create_density_plot(ax, x, y, bins, bandwidth, show_contour)
    
    plt.suptitle(title, fontsize=14, fontweight='bold')
    plt.tight_layout()
    plt.show()
    
    return fig

def create_density_plot(ax, x, y, bins=30, bandwidth=None, show_contour=True):
    """Helper function to create density plot on given axis."""
    
    # Create density map using 2D histogram
    if isinstance(bins, int):
        hist_bins = bins
    else:
        hist_bins = bins
    
    # Calculate 2D histogram
    hist, xedges, yedges = np.histogram2d(x, y, bins=hist_bins, density=True)
    
    # Create meshgrid for plotting
    X, Y = np.meshgrid(xedges[:-1] + (xedges[1] - xedges[0])/2,
                       yedges[:-1] + (yedges[1] - yedges[0])/2)
    
    # Plot heatmap
    im = ax.pcolormesh(X, Y, hist.T, cmap='hot', shading='auto')
    plt.colorbar(im, ax=ax, label='Density')
    
    if show_contour:
        # Add contour lines
        contour = ax.contour(X, Y, hist.T, colors='white', alpha=0.5, linewidths=1)
        ax.clabel(contour, inline=True, fontsize=8, fmt='%.2f')
    
    ax.set_xlabel('X')
    ax.set_ylabel('Y')
    ax.set_title('Density Heatmap')
    ax.set_aspect('equal', adjustable='box')
    
    return ax

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

def merge_points_optics(points, min_samples=16, xi=0.05, min_cluster_size=0.01) -> np.ndarray:
    """
    Takes an array of 2D points, clusters them using OPTICS, and returns
    centroids for each cluster. Noise points (label = -1) are kept as-is.
    
    Args:
        points: np.ndarray of shape (N, 2)
        min_samples: minimum samples for OPTICS core point
        xi: minimum steepness for cluster boundary detection
        min_cluster_size: minimum cluster size as fraction of total points
    
    Returns:
        np.ndarray of shape (M, 2) where M << N
    """
    clustering = OPTICS(min_samples=min_samples, xi=xi, min_cluster_size=min_cluster_size)
    clustering.fit(points)
    labels = clustering.labels_

    merged = []

    # For each cluster, compute the centroid
    for label in set(labels):
        cluster_points = points[labels == label]
        if label == -1:
            # Noise points: keep individually (they didn't fit any cluster)
            merged.extend(cluster_points)
        else:
            # Cluster: replace all points with their centroid
            centroid = cluster_points.mean(axis=0)
            merged.append(centroid)

    return np.array(merged)


def merge_points_dbscan(points: np.ndarray, eps: float = 0.5, min_samples: int = 3) -> np.ndarray:
    """
    Args:
        points: np.ndarray of shape (N, 2)
        eps: maximum distance between points to be considered neighbors
             LOWER = more clusters, HIGHER = fewer clusters
        min_samples: minimum points to form a cluster
                     LOWER = more clusters, HIGHER = fewer clusters
    """
    clustering = DBSCAN(eps=eps, min_samples=min_samples)
    clustering.fit(points)
    labels = clustering.labels_

    merged = []
    for label in set(labels):
        cluster_points = points[labels == label]
        if label == -1:
            merged.extend(cluster_points)  # keep noise points as-is
        else:
            merged.append(cluster_points.mean(axis=0))  # collapse to centroid

    return np.array(merged)

def main():
    walk_points,obstacles = fetch_points()


    print("="*80)
    print("WALK POINTS: ",walk_points)
    print("="*80)
    print("OBSTACLES: ",obstacles)
    
    print("="*80)
    filtered_points = remove_near_zero_outliers(walk_points)
    squares = intoGrid(filtered_points,10)
    merged_points = findCentroid(squares)

    # optics_merged_points = merge_points_optics(filtered_points)
    dbscan_merged_points = merge_points_dbscan(filtered_points, eps=4.0)
    print("raw points: ", len(filtered_points))
    
    print("grid merged points: ", len(merged_points))

    # print("optics merged points", len(optics_merged_points))

    print("DBSCAN merged points: ", len(dbscan_merged_points))
    plot_with_density(filtered_points)
    plot_with_density(merged_points)
    # plot_with_density(optics_merged_points)
    plot_with_density(dbscan_merged_points)


if __name__ == "__main__":
    main()