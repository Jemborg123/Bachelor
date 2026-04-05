"""
Algorithm package for DTU pathfinding.
"""

# from .Dijkstra import dijkstra, analyze_complexity
# from .AStar import astar, euclidean_heuristic, manhattan_heuristic, zero_heuristic
# from .BidirectionalAStar import bidirectional_astar
# from .ALT import alt, alt_with_preprocessing, select_landmarks, precompute_landmark_distances
# from .A_Dijkstra import dijkstra

# __all__ = [
#     'dijkstra', 
#     'astar',
#     'bidirectional_astar',
#     'alt',                   
#     'alt_with_preprocessing',
#     'select_landmarks',
#     'precompute_landmark_distances',
#     'analyze_complexity'
# ]

# NetworkX-based algorithms (original)
from .Dijkstra import dijkstra as dijkstra_nx
from .AStar import astar as astar_nx
from .BidirectionalAStar import bidirectional_astar as bidirectional_astar_nx
from .ALT import alt as alt_nx, alt_with_preprocessing, select_landmarks, precompute_landmark_distances

# AdjacencyList-based algorithms (new - with _adj suffix)
from .A_Dijkstra import dijkstra as dijkstra_adj
# from .A_AStar import astar as astar_adj
# from .A_BidirectionalAStar import bidirectional_astar as bidirectional_astar_adj

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
    # 'astar_adj',
    # 'bidirectional_astar_adj',
    
    # Shared utilities
    'alt_with_preprocessing',
    'select_landmarks',
    'precompute_landmark_distances',
    'analyze_complexity'
]