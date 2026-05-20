#!/usr/bin/env python3
"""
Graph Algorithms Library - Usage Examples

BFS, DFS, Dijkstra, Kruskal's MST, Topological Sort, and more.
"""

from graph import (
    Graph,
    bfs,
    dfs,
    dijkstra,
    dijkstra_trace,
    bellman_ford,
    reconstruct_path,
    kruskal_mst,
    kruskal_mst_trace,
    prim_mst,
    topological_sort,
    has_cycle,
    connected_components,
    is_connected,
    visualize_graph,
    visualize_path,
    visualize_mst,
    complete_graph,
    grid_graph,
)


def example_basic():
    """
    Example 1: Basic Graph Operations
    """
    print("=" * 60)
    print("Example 1: 📊 Basic Graph Operations")
    print("=" * 60)
    
    print("""
Graphs consist of vertices (nodes) and edges (connections).
    - Undirected: edges go both ways (A↔B)
    - Directed: edges have direction (A→B)
    - Weighted: edges have costs
""")
    
    g = Graph(directed=False)
    g.add_edge("A", "B", 4)
    g.add_edge("A", "C", 2)
    g.add_edge("B", "C", 1)
    g.add_edge("B", "D", 5)
    g.add_edge("C", "D", 8)
    
    print(visualize_graph(g))
    print(f"\nVertices: {g.vertices}")
    print(f"Degree of A: {g.degree('A')}")
    print()


def example_bfs():
    """
    Example 2: Breadth-First Search
    """
    print("=" * 60)
    print("Example 2: 🌊 Breadth-First Search (BFS)")
    print("=" * 60)
    
    print("""
BFS explores level by level - closest vertices first.
Perfect for finding shortest paths in UNWEIGHTED graphs.

Think of it like a wave spreading out from the start.
""")
    
    g = Graph()
    g.add_edge("A", "B")
    g.add_edge("A", "C")
    g.add_edge("B", "D")
    g.add_edge("B", "E")
    g.add_edge("C", "F")
    g.add_edge("D", "G")
    
    print("Graph:")
    print("    A")
    print("   / \\")
    print("  B   C")
    print(" /|   |")
    print("D E   F")
    print("|")
    print("G\n")
    
    distances, parents = bfs(g, "A")
    
    print("BFS from A:")
    for v in sorted(distances.keys()):
        print(f"  {v}: distance={distances[v]}")
    
    print(f"\nShortest path A→G:")
    path = reconstruct_path(parents, "A", "G")
    print(f"  {' → '.join(path)}")
    print()


def example_dijkstra():
    """
    Example 3: Dijkstra's Algorithm
    """
    print("=" * 60)
    print("Example 3: 🛤️ Dijkstra's Shortest Paths")
    print("=" * 60)
    
    print("""
Dijkstra finds shortest paths in WEIGHTED graphs.
Uses a priority queue to always process the closest vertex.

Time: O((V + E) log V) with binary heap
""")
    
    g = Graph()
    g.add_edge("A", "B", 4)
    g.add_edge("A", "C", 2)
    g.add_edge("B", "C", 1)
    g.add_edge("B", "D", 5)
    g.add_edge("C", "D", 8)
    g.add_edge("C", "E", 10)
    g.add_edge("D", "E", 2)
    
    print(visualize_graph(g))
    
    distances, parents = dijkstra(g, "A")
    
    print("\nShortest distances from A:")
    for v in sorted(distances.keys()):
        print(f"  {v}: {distances[v]}")
    
    print(f"\nShortest path A→E:")
    path = reconstruct_path(parents, "A", "E")
    print(f"  {' → '.join(path)}")
    print(f"  Total distance: {distances['E']}")
    print()


def example_dijkstra_trace():
    """
    Example 4: Watch Dijkstra Work
    """
    print("=" * 60)
    print("Example 4: 👁️ Watch Dijkstra Work")
    print("=" * 60)
    
    print("""
See how Dijkstra's algorithm expands outward like a wave,
always processing the vertex with smallest distance.
""")
    
    g = Graph()
    g.add_edge("A", "B", 4)
    g.add_edge("A", "C", 2)
    g.add_edge("B", "C", 1)
    g.add_edge("B", "D", 5)
    g.add_edge("C", "D", 8)
    
    print("Step-by-step execution:")
    for state in dijkstra_trace(g, "A"):
        frontier = ", ".join(f"{v}({d})" for d, v in sorted(state.frontier))
        print(f"  Step {state.step}: Process {state.current} (dist={state.current_distance})")
        print(f"    Visited: {state.visited}")
        print(f"    Distances: {state.distances}")
        if frontier:
            print(f"    Frontier: {frontier}")
        print()


def example_mst():
    """
    Example 5: Minimum Spanning Tree
    """
    print("=" * 60)
    print("Example 5: 🌲 Minimum Spanning Tree")
    print("=" * 60)
    
    print("""
A Minimum Spanning Tree (MST) connects all vertices with
minimum total edge weight. It has exactly V-1 edges.

Applications:
    - Network design (minimize cable length)
    - Cluster analysis
    - Approximation algorithms
""")
    
    g = Graph()
    g.add_edge("A", "B", 4)
    g.add_edge("A", "C", 2)
    g.add_edge("B", "C", 1)
    g.add_edge("B", "D", 5)
    g.add_edge("C", "D", 8)
    g.add_edge("C", "E", 10)
    g.add_edge("D", "E", 2)
    g.add_edge("D", "F", 6)
    g.add_edge("E", "F", 3)
    
    print(visualize_graph(g))
    
    mst, total = kruskal_mst(g)
    print("\nKruskal's MST:")
    print(visualize_mst(mst, total))
    
    _, prim_total = prim_mst(g)
    print(f"\nPrim's MST total: {prim_total} (same as Kruskal)")
    print()


def example_mst_trace():
    """
    Example 6: Watch MST Grow
    """
    print("=" * 60)
    print("Example 6: 🌱 Watch MST Grow (Kruskal)")
    print("=" * 60)
    
    print("""
Kruskal's algorithm:
    1. Sort edges by weight
    2. Add smallest edge that doesn't create a cycle
    3. Repeat until V-1 edges added
""")
    
    g = Graph()
    g.add_edge("A", "B", 4)
    g.add_edge("A", "C", 2)
    g.add_edge("B", "C", 1)
    g.add_edge("B", "D", 5)
    g.add_edge("C", "D", 8)
    
    print("Building MST step by step:")
    for state in kruskal_mst_trace(g):
        if state.current_edge:
            e = state.current_edge
            status = "✓ Added" if len(state.mst_edges) > 0 and state.mst_edges[-1] == e else "✗ Skip"
            print(f"  Consider {e.source}--({e.weight})--{e.target}: {status}")
    
    print(f"\nFinal MST weight: {state.total_weight}")
    print()


def example_topological_sort():
    """
    Example 7: Topological Sort
    """
    print("=" * 60)
    print("Example 7: 📋 Topological Sort")
    print("=" * 60)
    
    print("""
Topological sort orders vertices so that for every edge A→B,
A comes before B. Only works on Directed Acyclic Graphs (DAGs).

Applications:
    - Build systems (compile dependencies)
    - Package managers (install order)
    - Task scheduling
""")
    
    # Build dependency graph
    g = Graph(directed=True)
    g.add_edge("main.c", "main.o")
    g.add_edge("util.c", "util.o")
    g.add_edge("util.h", "util.o")
    g.add_edge("util.h", "main.o")
    g.add_edge("main.o", "program")
    g.add_edge("util.o", "program")
    
    print("Build dependencies:")
    print("  main.c  util.c  util.h")
    print("     ↓      ↓      ↓↓")
    print("  main.o ← util.o")
    print("     ↓      ↓")
    print("     → program ←\n")
    
    order = topological_sort(g)
    
    if order:
        print(f"Build order: {' → '.join(order)}")
    print()


def example_cycle_detection():
    """
    Example 8: Cycle Detection
    """
    print("=" * 60)
    print("Example 8: 🔄 Cycle Detection")
    print("=" * 60)
    
    print("""
Detecting cycles is important for:
    - Deadlock detection
    - Dependency validation
    - DAG verification
""")
    
    # Acyclic
    g1 = Graph(directed=True)
    g1.add_edge("A", "B")
    g1.add_edge("B", "C")
    g1.add_edge("A", "C")
    
    print("Graph 1 (A→B→C, A→C):")
    print(f"  Has cycle: {has_cycle(g1)}")
    
    # Has cycle
    g2 = Graph(directed=True)
    g2.add_edge("A", "B")
    g2.add_edge("B", "C")
    g2.add_edge("C", "A")  # Creates cycle
    
    print("\nGraph 2 (A→B→C→A):")
    print(f"  Has cycle: {has_cycle(g2)}")
    print()


def example_connected_components():
    """
    Example 9: Connected Components
    """
    print("=" * 60)
    print("Example 9: 🏝️ Connected Components")
    print("=" * 60)
    
    print("""
A connected component is a maximal set of vertices
where every vertex is reachable from every other.
""")
    
    g = Graph()
    # Component 1
    g.add_edge("A", "B")
    g.add_edge("B", "C")
    # Component 2
    g.add_edge("X", "Y")
    # Component 3 (isolated)
    g.add_vertex("Z")
    
    components = connected_components(g)
    
    print(f"Graph has {len(components)} connected components:")
    for i, comp in enumerate(components, 1):
        print(f"  Component {i}: {comp}")
    
    print(f"\nIs graph connected? {is_connected(g)}")
    print()


def example_builders():
    """
    Example 10: Graph Builders
    """
    print("=" * 60)
    print("Example 10: 🏗️ Graph Builders")
    print("=" * 60)
    
    print("Complete graph K4 (every vertex connected):")
    k4 = complete_graph(4)
    print(f"  Vertices: {k4.num_vertices}, Edges: {k4.num_edges}")
    
    print("\nGrid graph 3x3:")
    grid = grid_graph(3, 3)
    print(f"  Vertices: {grid.num_vertices}, Edges: {grid.num_edges}")
    print("  Layout:")
    print("    (0,0)-(0,1)-(0,2)")
    print("      |     |     |")
    print("    (1,0)-(1,1)-(1,2)")
    print("      |     |     |")
    print("    (2,0)-(2,1)-(2,2)")
    print()


def example_banner():
    """Print a cool banner."""
    print("""
╔═══════════════════════════════════════════════════════════════╗
║                                                               ║
║   ██████╗ ██████╗  █████╗ ██████╗ ██╗  ██╗                    ║
║  ██╔════╝ ██╔══██╗██╔══██╗██╔══██╗██║  ██║                    ║
║  ██║  ███╗██████╔╝███████║██████╔╝███████║                    ║
║  ██║   ██║██╔══██╗██╔══██║██╔═══╝ ██╔══██║                    ║
║  ╚██████╔╝██║  ██║██║  ██║██║     ██║  ██║                    ║
║   ╚═════╝ ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝     ╚═╝  ╚═╝                    ║
║                                                               ║
║     📊 Graph Algorithms Library 📊                            ║
║                                                               ║
║  BFS · DFS · Dijkstra · MST · Topological Sort                ║
║                                                               ║
╚═══════════════════════════════════════════════════════════════╝
""")


def main():
    """Run all examples."""
    example_banner()
    
    example_basic()
    example_bfs()
    example_dijkstra()
    example_dijkstra_trace()
    example_mst()
    example_mst_trace()
    example_topological_sort()
    example_cycle_detection()
    example_connected_components()
    example_builders()
    
    print("=" * 60)
    print("  ✨ All examples completed!")
    print("=" * 60)
    print("""
Algorithms Summary:

    TRAVERSAL:
    • BFS: Level-order, shortest unweighted paths - O(V+E)
    • DFS: Deep exploration, cycle detection - O(V+E)
    
    SHORTEST PATHS:
    • Dijkstra: Non-negative weights - O((V+E) log V)
    • Bellman-Ford: Handles negative weights - O(VE)
    
    MINIMUM SPANNING TREE:
    • Kruskal: Sort edges, Union-Find - O(E log E)
    • Prim: Grow from vertex - O((V+E) log V)
    
    DAG:
    • Topological Sort: Dependency ordering - O(V+E)
    • Cycle Detection: Validate DAG - O(V+E)
""")


if __name__ == "__main__":
    main()
