"""
Algorithm package for DTU pathfinding.
"""
# ========== NETWORKX ALGORITHMS (Original) ==========
# NetworkX-based algorithms (original)
from .Dijkstra import dijkstra as dijkstra_nx
from .AStar import astar as astar_nx
from .BidirectionalAStar import bidirectional_astar as bidirectional_astar_nx
from .ALT import alt as alt_nx, alt_with_preprocessing, select_landmarks, precompute_landmark_distances

# ========== ADJACENCY LIST ALGORITHMS (New) ==========
# AdjacencyList-based algorithms (new - with _adj suffix)
from .A_Dijkstra import dijkstra as dijkstra_adj
from .A_AStar import astar as astar_adj
from .A_BidirectionalAStar import bidirectional_astar as bidirectional_astar_adj
from .A_ALT import alt as alt_adj

# ========== SHARED ==========
# Complexity analysis (shared)
from .Dijkstra import analyze_complexity

__all__ = [
    # NetworkX versions
    'dijkstra_nx',
    'astar_nx',
    'bidirectional_astar_nx',
    'alt_nx',
    
    # AdjacencyList versions
    'dijkstra_adj',
    'astar_adj',
    'bidirectional_astar_adj',
    'alt_adj',
    
    # Shared utilities
    'alt_with_preprocessing',
    'select_landmarks',
    'precompute_landmark_distances',
    'analyze_complexity'
]