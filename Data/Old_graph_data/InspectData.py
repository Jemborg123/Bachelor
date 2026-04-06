#This file tries to loosely follow the implementation from the main.py file in order to inspect the old datastructure, with the goal of comparing it to the new adjacencylist


import sys, os
import pickle

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from utils import minmaxxy
from scipy.spatial import KDTree
import numpy as np


GRAPH_FILE = 'Data/Old_graph_data/walkability_graph.pkl'


def load_nx_graph():
    """Load the pre-built graph."""
    print(f"\n📂 Loading NetworkX graph from {GRAPH_FILE}...")
    with open(GRAPH_FILE, 'rb') as f:
        G = pickle.load(f)
    print(f"  ✅ Graph loaded: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges")
    return G



OUTLIER_RADIUS = 500
OUTLIER_MIN_NBR = 5
G = load_nx_graph()
node_ids = list(G.nodes())
coords = np.array([(data['x'], data['y']) for _, data in G.nodes(data=True)])


tree = KDTree(coords)
counts = np.array([len(tree.query_ball_point(c, r=OUTLIER_RADIUS)) for c in coords])
mask = counts >= OUTLIER_MIN_NBR

kept_node_ids = [n for n, m in zip(node_ids, mask) if m]
subG = G.subgraph(kept_node_ids)

nodes = [(data['x'],data['y']) for node, data in subG.nodes(data=True)]
minmaxxy(nodes)

n1Coords = G.nodes[7108]
n2Coords = G.nodes[6914]

print(7108, "has coords", n1Coords)
print(6914, "has coords", n2Coords)