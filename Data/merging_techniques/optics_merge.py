from sklearn.cluster import OPTICS
import numpy as np

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