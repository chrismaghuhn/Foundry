"""Tests for graph."""

import pytest
from graph import (
    # Core
    Graph, Edge, UnionFind,
    
    # Traversal
    bfs, dfs, dfs_recursive,
    
    # Shortest paths
    dijkstra, bellman_ford, reconstruct_path,
    
    # MST
    kruskal_mst, prim_mst,
    
    # DAG
    topological_sort, has_cycle,
    
    # Components
    connected_components, is_connected,
    
    # Visualization
    visualize_graph, visualize_path, visualize_mst,
    
    # Builders
    complete_graph, grid_graph, from_edges,
)


# =============================================================================
# Graph Construction Tests
# =============================================================================

class TestGraphConstruction:
    """Test graph construction operations."""
    
    def test_empty_graph(self):
        """Empty graph."""
        g = Graph()
        assert g.num_vertices == 0
        assert g.num_edges == 0
    
    def test_add_vertex(self):
        """Add vertices."""
        g = Graph()
        g.add_vertex("A")
        g.add_vertex("B")
        
        assert g.num_vertices == 2
        assert "A" in g
        assert "B" in g
    
    def test_add_edge_undirected(self):
        """Add undirected edge."""
        g = Graph(directed=False)
        g.add_edge("A", "B", 5)
        
        assert g.has_edge("A", "B")
        assert g.has_edge("B", "A")  # Symmetric
        assert g.get_weight("A", "B") == 5
    
    def test_add_edge_directed(self):
        """Add directed edge."""
        g = Graph(directed=True)
        g.add_edge("A", "B", 5)
        
        assert g.has_edge("A", "B")
        assert not g.has_edge("B", "A")  # Not symmetric
    
    def test_neighbors(self):
        """Get neighbors."""
        g = Graph()
        g.add_edge("A", "B")
        g.add_edge("A", "C")
        
        neighbors = g.neighbors("A")
        assert "B" in neighbors
        assert "C" in neighbors
    
    def test_remove_edge(self):
        """Remove edge."""
        g = Graph()
        g.add_edge("A", "B")
        
        assert g.remove_edge("A", "B")
        assert not g.has_edge("A", "B")
    
    def test_degree(self):
        """Vertex degree."""
        g = Graph()
        g.add_edge("A", "B")
        g.add_edge("A", "C")
        g.add_edge("A", "D")
        
        assert g.degree("A") == 3


# =============================================================================
# BFS Tests
# =============================================================================

class TestBFS:
    """Test Breadth-First Search."""
    
    def test_simple_bfs(self):
        """Simple BFS traversal."""
        g = Graph()
        g.add_edge("A", "B")
        g.add_edge("A", "C")
        g.add_edge("B", "D")
        
        distances, parents = bfs(g, "A")
        
        assert distances["A"] == 0
        assert distances["B"] == 1
        assert distances["C"] == 1
        assert distances["D"] == 2
    
    def test_bfs_shortest_path(self):
        """BFS finds shortest unweighted path."""
        g = Graph()
        g.add_edge("A", "B")
        g.add_edge("B", "C")
        g.add_edge("A", "C")  # Direct path
        
        distances, _ = bfs(g, "A")
        assert distances["C"] == 1  # Direct path is shorter
    
    def test_bfs_unreachable(self):
        """Unreachable vertices not in result."""
        g = Graph()
        g.add_edge("A", "B")
        g.add_vertex("C")  # Isolated
        
        distances, _ = bfs(g, "A")
        assert "C" not in distances
    
    def test_bfs_invalid_start(self):
        """Invalid start vertex raises error."""
        g = Graph()
        g.add_edge("A", "B")
        
        with pytest.raises(ValueError):
            bfs(g, "X")


# =============================================================================
# DFS Tests
# =============================================================================

class TestDFS:
    """Test Depth-First Search."""
    
    def test_simple_dfs(self):
        """Simple DFS traversal."""
        g = Graph()
        g.add_edge("A", "B")
        g.add_edge("B", "C")
        g.add_edge("A", "D")
        
        discovery, parents = dfs(g, "A")
        
        assert "A" in discovery
        assert "B" in discovery
        assert "C" in discovery
        assert "D" in discovery
    
    def test_dfs_recursive(self):
        """Recursive DFS."""
        g = Graph()
        g.add_edge("A", "B")
        g.add_edge("B", "C")
        
        visited = dfs_recursive(g, "A")
        
        assert "A" in visited
        assert "B" in visited
        assert "C" in visited


# =============================================================================
# Dijkstra Tests
# =============================================================================

class TestDijkstra:
    """Test Dijkstra's shortest path algorithm."""
    
    def test_simple_dijkstra(self):
        """Simple shortest paths."""
        g = Graph()
        g.add_edge("A", "B", 4)
        g.add_edge("A", "C", 2)
        g.add_edge("B", "C", 1)
        g.add_edge("B", "D", 5)
        g.add_edge("C", "D", 8)
        
        distances, parents = dijkstra(g, "A")
        
        assert distances["A"] == 0
        assert distances["C"] == 2
        assert distances["B"] == 3  # A→C→B
        assert distances["D"] == 8  # A→C→B→D
    
    def test_reconstruct_path(self):
        """Path reconstruction."""
        g = Graph()
        g.add_edge("A", "B", 1)
        g.add_edge("B", "C", 1)
        g.add_edge("C", "D", 1)
        
        _, parents = dijkstra(g, "A")
        path = reconstruct_path(parents, "A", "D")
        
        assert path == ["A", "B", "C", "D"]
    
    def test_dijkstra_negative_weight_error(self):
        """Negative weight raises error."""
        g = Graph()
        g.add_edge("A", "B", -1)
        
        with pytest.raises(ValueError):
            dijkstra(g, "A")
    
    def test_dijkstra_unreachable(self):
        """Unreachable vertex not in distances."""
        g = Graph()
        g.add_edge("A", "B", 1)
        g.add_vertex("C")
        
        distances, _ = dijkstra(g, "A")
        assert "C" not in distances


# =============================================================================
# Bellman-Ford Tests
# =============================================================================

class TestBellmanFord:
    """Test Bellman-Ford algorithm."""
    
    def test_simple_bellman_ford(self):
        """Simple shortest paths."""
        g = Graph(directed=True)
        g.add_edge("A", "B", 4)
        g.add_edge("A", "C", 2)
        g.add_edge("C", "B", 1)
        
        distances, _, has_neg_cycle = bellman_ford(g, "A")
        
        assert not has_neg_cycle
        assert distances["B"] == 3  # A→C→B
    
    def test_negative_weight(self):
        """Handles negative weights."""
        g = Graph(directed=True)
        g.add_edge("A", "B", 5)
        g.add_edge("B", "C", -2)
        g.add_edge("A", "C", 4)
        
        distances, _, has_neg_cycle = bellman_ford(g, "A")
        
        assert not has_neg_cycle
        assert distances["C"] == 3  # A→B→C with negative edge


# =============================================================================
# MST Tests
# =============================================================================

class TestMST:
    """Test Minimum Spanning Tree algorithms."""
    
    def test_kruskal_simple(self):
        """Simple MST with Kruskal."""
        g = Graph()
        g.add_edge("A", "B", 1)
        g.add_edge("B", "C", 2)
        g.add_edge("A", "C", 3)
        
        mst, total = kruskal_mst(g)
        
        assert total == 3  # A-B(1) + B-C(2)
        assert len(mst) == 2
    
    def test_prim_simple(self):
        """Simple MST with Prim."""
        g = Graph()
        g.add_edge("A", "B", 1)
        g.add_edge("B", "C", 2)
        g.add_edge("A", "C", 3)
        
        mst, total = prim_mst(g, "A")
        
        assert total == 3
        assert len(mst) == 2
    
    def test_kruskal_equals_prim(self):
        """Kruskal and Prim find same total weight."""
        g = Graph()
        g.add_edge("A", "B", 4)
        g.add_edge("A", "C", 2)
        g.add_edge("B", "C", 1)
        g.add_edge("B", "D", 5)
        g.add_edge("C", "D", 8)
        
        _, kruskal_total = kruskal_mst(g)
        _, prim_total = prim_mst(g)
        
        assert kruskal_total == prim_total
    
    def test_mst_directed_error(self):
        """MST on directed graph raises error."""
        g = Graph(directed=True)
        g.add_edge("A", "B", 1)
        
        with pytest.raises(ValueError):
            kruskal_mst(g)


# =============================================================================
# Topological Sort Tests
# =============================================================================

class TestTopologicalSort:
    """Test topological sort."""
    
    def test_simple_topo_sort(self):
        """Simple topological sort."""
        g = Graph(directed=True)
        g.add_edge("A", "B")
        g.add_edge("A", "C")
        g.add_edge("B", "D")
        g.add_edge("C", "D")
        
        order = topological_sort(g)
        
        assert order is not None
        assert order.index("A") < order.index("B")
        assert order.index("A") < order.index("C")
        assert order.index("B") < order.index("D")
        assert order.index("C") < order.index("D")
    
    def test_topo_sort_cycle(self):
        """Cycle returns None."""
        g = Graph(directed=True)
        g.add_edge("A", "B")
        g.add_edge("B", "C")
        g.add_edge("C", "A")  # Cycle
        
        order = topological_sort(g)
        assert order is None
    
    def test_topo_sort_undirected_error(self):
        """Undirected graph raises error."""
        g = Graph(directed=False)
        g.add_edge("A", "B")
        
        with pytest.raises(ValueError):
            topological_sort(g)


# =============================================================================
# Cycle Detection Tests
# =============================================================================

class TestCycleDetection:
    """Test cycle detection."""
    
    def test_directed_cycle(self):
        """Detect cycle in directed graph."""
        g = Graph(directed=True)
        g.add_edge("A", "B")
        g.add_edge("B", "C")
        g.add_edge("C", "A")
        
        assert has_cycle(g) == True
    
    def test_directed_no_cycle(self):
        """No cycle in DAG."""
        g = Graph(directed=True)
        g.add_edge("A", "B")
        g.add_edge("B", "C")
        
        assert has_cycle(g) == False
    
    def test_undirected_cycle(self):
        """Detect cycle in undirected graph."""
        g = Graph(directed=False)
        g.add_edge("A", "B")
        g.add_edge("B", "C")
        g.add_edge("C", "A")
        
        assert has_cycle(g) == True
    
    def test_undirected_no_cycle(self):
        """No cycle (tree)."""
        g = Graph(directed=False)
        g.add_edge("A", "B")
        g.add_edge("B", "C")
        
        assert has_cycle(g) == False


# =============================================================================
# Connected Components Tests
# =============================================================================

class TestConnectedComponents:
    """Test connected components."""
    
    def test_single_component(self):
        """Single connected component."""
        g = Graph()
        g.add_edge("A", "B")
        g.add_edge("B", "C")
        
        components = connected_components(g)
        assert len(components) == 1
    
    def test_multiple_components(self):
        """Multiple components."""
        g = Graph()
        g.add_edge("A", "B")
        g.add_edge("C", "D")
        
        components = connected_components(g)
        assert len(components) == 2
    
    def test_is_connected(self):
        """Check connectivity."""
        g = Graph()
        g.add_edge("A", "B")
        g.add_edge("B", "C")
        
        assert is_connected(g) == True
    
    def test_is_not_connected(self):
        """Check disconnected."""
        g = Graph()
        g.add_edge("A", "B")
        g.add_vertex("C")
        
        assert is_connected(g) == False


# =============================================================================
# Union-Find Tests
# =============================================================================

class TestUnionFind:
    """Test Union-Find data structure."""
    
    def test_make_set(self):
        """Create sets."""
        uf = UnionFind()
        uf.make_set("A")
        uf.make_set("B")
        
        assert not uf.connected("A", "B")
    
    def test_union(self):
        """Union sets."""
        uf = UnionFind()
        uf.make_set("A")
        uf.make_set("B")
        
        assert uf.union("A", "B") == True
        assert uf.connected("A", "B")
    
    def test_union_already_connected(self):
        """Union already connected returns False."""
        uf = UnionFind()
        uf.union("A", "B")
        
        assert uf.union("A", "B") == False
    
    def test_transitive(self):
        """Transitivity."""
        uf = UnionFind()
        uf.union("A", "B")
        uf.union("B", "C")
        
        assert uf.connected("A", "C")


# =============================================================================
# Graph Builders Tests
# =============================================================================

class TestGraphBuilders:
    """Test graph builder functions."""
    
    def test_complete_graph(self):
        """Complete graph."""
        g = complete_graph(4)
        
        assert g.num_vertices == 4
        assert g.num_edges == 6  # C(4,2) = 6
    
    def test_grid_graph(self):
        """Grid graph."""
        g = grid_graph(3, 3)
        
        assert g.num_vertices == 9
        # 3x3 grid has 12 edges (6 horizontal + 6 vertical)
        assert g.num_edges == 12
    
    def test_from_edges(self):
        """Build from edge list."""
        edges = [
            ("A", "B", 1),
            ("B", "C", 2),
        ]
        g = from_edges(edges)
        
        assert g.num_vertices == 3
        assert g.has_edge("A", "B")


# =============================================================================
# Visualization Tests
# =============================================================================

class TestVisualization:
    """Test visualization functions."""
    
    def test_visualize_graph(self):
        """Graph visualization."""
        g = Graph()
        g.add_edge("A", "B", 5)
        
        viz = visualize_graph(g)
        assert "A" in viz
        assert "B" in viz
    
    def test_visualize_path(self):
        """Path visualization."""
        g = Graph()
        g.add_edge("A", "B", 1)
        g.add_edge("B", "C", 2)
        
        path = ["A", "B", "C"]
        viz = visualize_path(g, path)
        
        assert "A" in viz
        assert "B" in viz
        assert "C" in viz
    
    def test_visualize_mst(self):
        """MST visualization."""
        mst = [Edge("A", "B", 1), Edge("B", "C", 2)]
        viz = visualize_mst(mst, 3)
        
        assert "Minimum Spanning Tree" in viz


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
