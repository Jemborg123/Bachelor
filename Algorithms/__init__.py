"""
Algorithm package for DTU pathfinding.
"""

from .Dijkstra import dijkstra, analyze_complexity
from .AStar import astar, euclidean_heuristic, manhattan_heuristic, zero_heuristic

# __all__ = ['Dijkstra', 'analyze_complexity']

# # Re-export analyze_complexity with consistent name
# Re-export
# analyze_complexity = analyze_dijkstra

__all__ = [
    'dijkstra', 
    'astar',           # 👈 ADD THIS
    'analyze_complexity'
]