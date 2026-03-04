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

def merge_points_simpleDbscan(points: np.ndarray, eps: float = 0.5, min_samples: int = 3) -> np.ndarray:
    """
    Args:
        points: np.ndarray of shape (N, 2)
        eps: maximum distance between points to be considered neighbors
             LOWER = more clusters, HIGHER = fewer clusters
        min_samples: minimum points to form a cluster
                     LOWER = more clusters, HIGHER = fewer clusters
    """
    labels = simpleDBSCAN(points, eps, min_samples)

    merged = []

    unique_labels = set(labels)
    for label in unique_labels:
        cluster_points = np.array([points[i] for i, v in enumerate(labels) if v == label])
        if label == -1:
            merged.extend(cluster_points)  # keep noise points as-is
        else:
            merged.append(cluster_points.mean(axis=0))  # collapse to centroid

    return np.array(merged)

def simpleDBSCAN(dataset, Eps, minPts):
    Eps = Eps**2
    n = len(dataset)
    neighbors = computeNeighbors(dataset, Eps)

    visited = [False] * n
    labels = [0] * n
    clusterId = 0

    for i in range(n):
        print(f"\rProgress: {i}/{n}", end="", flush=True)
        if not visited[i]:
            visited[i] = True
            if len(neighbors[i]) < minPts:
                labels[i] = -1
            else:
                clusterId += 1
                expandCluster(i, clusterId, neighbors, visited, labels, minPts)

    return labels

def expandCluster(i, clusterId, neighbors, visited, labels, minPts):
    labels[i] = clusterId
    queue = list(neighbors[i])
    while queue:
        neighbour = queue.pop()
        if not visited[neighbour]:
            visited[neighbour] = True
            if len(neighbors[neighbour]) >= minPts:
                queue.extend(neighbors[neighbour])
        if labels[neighbour] == 0:
            labels[neighbour] = clusterId

def computeNeighbors(dataset, Eps):
    print("PreComputing all neighbours")
    n = len(dataset)
    neighbors = [[] for _ in range(n)]
    for i in range(n):
        print(f"\rProgress: {i}/{n}", end="", flush=True)
        for j in range(i+1, n):
            if simpleDistance(dataset[i], dataset[j]) <= Eps:
                neighbors[i].append(j)
                neighbors[j].append(i)
    return neighbors

def simpleDistance(p1, p2):
    x1, y1 = p1
    x2, y2 = p2
    return (x1-x2)**2 + (y1-y2)**2
