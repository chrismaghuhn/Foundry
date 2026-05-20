"""
Graph: Graph Algorithms Library

BFS, DFS, Dijkstra, Kruskal's MST, Topological Sort, and more.
Watch algorithms explore your graph step by step.

Quick Start:
    >>> from graph import Graph, dijkstra, kruskal_mst
    >>> 
    >>> g = Graph()
    >>> g.add_edge("A", "B", 4)
    >>> g.add_edge("A", "C", 2)
    >>> g.add_edge("B", "C", 1)
    >>> g.add_edge("B", "D", 5)
    >>> 
    >>> # Shortest paths from A
    >>> distances, parents = dijkstra(g, "A")
    >>> print(distances)  # {'A': 0, 'C': 2, 'B': 3, 'D': 8}
    >>> 
    >>> # Minimum spanning tree
    >>> mst, total = kruskal_mst(g)
    >>> print(total)  # Minimum total weight

Algorithms:
    - BFS: Shortest unweighted paths - O(V+E)
    - DFS: Deep exploration, cycle detection - O(V+E)
    - Dijkstra: Shortest weighted paths - O((V+E) log V)
    - Bellman-Ford: Handles negative weights - O(VE)
    - Kruskal/Prim: Minimum Spanning Tree - O(E log E)
    - Topological Sort: DAG ordering - O(V+E)
"""

from .graph import (
    # Types
    GraphType, Edge, Weight,
    
    # Core
    Graph, UnionFind,
    
    # Traversal
    bfs, bfs_trace, dfs, dfs_recursive,
    TraversalState,
    
    # Shortest Paths
    dijkstra, dijkstra_trace, bellman_ford,
    reconstruct_path, DijkstraState,
    
    # MST
    kruskal_mst, kruskal_mst_trace, prim_mst,
    MSTState,
    
    # DAG
    topological_sort, has_cycle,
    
    # Components
    connected_components, is_connected,
    
    # Visualization
    visualize_graph, visualize_path, visualize_mst,
    
    # Builders
    complete_graph, grid_graph, from_edges,
)

__version__ = "1.0.0"
__author__ = "chrismaghuhn"

__all__ = [
    # Types
    'GraphType', 'Edge', 'Weight',
    
    # Core
    'Graph', 'UnionFind',
    
    # Traversal
    'bfs', 'bfs_trace', 'dfs', 'dfs_recursive', 'TraversalState',
    
    # Shortest Paths
    'dijkstra', 'dijkstra_trace', 'bellman_ford',
    'reconstruct_path', 'DijkstraState',
    
    # MST
    'kruskal_mst', 'kruskal_mst_trace', 'prim_mst', 'MSTState',
    
    # DAG
    'topological_sort', 'has_cycle',
    
    # Components
    'connected_components', 'is_connected',
    
    # Visualization
    'visualize_graph', 'visualize_path', 'visualize_mst',
    
    # Builders
    'complete_graph', 'grid_graph', 'from_edges',
]
