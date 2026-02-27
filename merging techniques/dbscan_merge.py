from sklearn.cluster import DBSCAN
import numpy as np

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