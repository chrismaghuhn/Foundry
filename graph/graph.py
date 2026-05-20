"""
Graph: Graph Algorithms Library

Graph algorithms visualized. BFS, DFS, Dijkstra, Kruskal's MST,
topological sort. Watch algorithms explore your graph step by step.

Included Algorithms:

    Traversal:
        - BFS (Breadth-First Search): Level-order, shortest unweighted paths
        - DFS (Depth-First Search): Deep exploration, cycle detection
    
    Shortest Paths:
        - Dijkstra: Single-source shortest paths (non-negative weights)
        - Bellman-Ford: Handles negative weights, detects negative cycles
    
    Minimum Spanning Tree:
        - Kruskal: Greedy edge selection with Union-Find
        - Prim: Grow tree from a starting vertex
    
    DAG Operations:
        - Topological Sort: Dependency ordering
        - Cycle Detection: Find cycles in directed graphs
    
    Analysis:
        - Connected Components
        - Strongly Connected Components (Tarjan/Kosaraju)
        - Bridges and Articulation Points

Data Structures:

    Graph:
        Adjacency list representation. Efficient for sparse graphs.
        Supports directed/undirected, weighted/unweighted.
    
    UnionFind:
        Disjoint set data structure for Kruskal's algorithm.
        Path compression + union by rank = near O(1) operations.

Visualization:

    All algorithms can yield intermediate states for visualization.
    Watch Dijkstra's frontier expand, see the MST grow edge by edge.

Usage:
    >>> from graph import Graph, dijkstra, bfs, kruskal_mst
    >>> 
    >>> g = Graph()
    >>> g.add_edge("A", "B", 4)
    >>> g.add_edge("A", "C", 2)
    >>> g.add_edge("B", "C", 1)
    >>> g.add_edge("B", "D", 5)
    >>> g.add_edge("C", "D", 8)
    >>> 
    >>> # Shortest paths from A
    >>> distances, parents = dijkstra(g, "A")
    >>> print(distances)  # {'A': 0, 'C': 2, 'B': 3, 'D': 8}
    >>> 
    >>> # Reconstruct path
    >>> path = reconstruct_path(parents, "A", "D")
    >>> print(path)  # ['A', 'C', 'B', 'D']

Author: chrismaghuhn
License: MIT
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import (
    Dict, List, Set, Tuple, Optional, Iterator, 
    TypeVar, Generic, Callable, Any, Union
)
from collections import defaultdict, deque
from enum import Enum, auto
import heapq


# =============================================================================
# Types
# =============================================================================

T = TypeVar('T')  # Vertex type
Weight = Union[int, float]


class GraphType(Enum):
    """Type of graph."""
    DIRECTED = auto()
    UNDIRECTED = auto()


@dataclass
class Edge(Generic[T]):
    """An edge in the graph."""
    source: T
    target: T
    weight: Weight = 1
    
    def __lt__(self, other: 'Edge') -> bool:
        return self.weight < other.weight
    
    def reversed(self) -> 'Edge[T]':
        """Return edge with source and target swapped."""
        return Edge(self.target, self.source, self.weight)


# =============================================================================
# Graph
# =============================================================================

class Graph(Generic[T]):
    """
    Graph with adjacency list representation.
    
    Supports:
        - Directed or undirected edges
        - Weighted or unweighted edges
        - Self-loops and parallel edges
    
    Adjacency list is efficient for sparse graphs (most real graphs).
    Space: O(V + E), Edge lookup: O(degree), Iterate neighbors: O(degree)
    """
    
    def __init__(self, directed: bool = False):
        """
        Initialize graph.
        
        Args:
            directed: If True, edges are one-way. If False, edges are bidirectional.
        """
        self.directed = directed
        self._adj: Dict[T, List[Tuple[T, Weight]]] = defaultdict(list)
        self._vertices: Set[T] = set()
    
    def add_vertex(self, v: T) -> None:
        """Add a vertex (node) to the graph."""
        self._vertices.add(v)
        if v not in self._adj:
            self._adj[v] = []
    
    def add_edge(self, u: T, v: T, weight: Weight = 1) -> None:
        """
        Add an edge from u to v.
        
        For undirected graphs, also adds edge from v to u.
        """
        self._vertices.add(u)
        self._vertices.add(v)
        
        self._adj[u].append((v, weight))
        
        if not self.directed:
            self._adj[v].append((u, weight))
    
    def remove_edge(self, u: T, v: T) -> bool:
        """Remove edge from u to v. Returns True if edge existed."""
        if u not in self._adj:
            return False
        
        original_len = len(self._adj[u])
        self._adj[u] = [(target, w) for target, w in self._adj[u] if target != v]
        removed = len(self._adj[u]) < original_len
        
        if not self.directed and removed:
            self._adj[v] = [(target, w) for target, w in self._adj[v] if target != u]
        
        return removed
    
    def has_edge(self, u: T, v: T) -> bool:
        """Check if edge exists from u to v."""
        if u not in self._adj:
            return False
        return any(target == v for target, _ in self._adj[u])
    
    def get_weight(self, u: T, v: T) -> Optional[Weight]:
        """Get weight of edge from u to v, or None if not exists."""
        if u not in self._adj:
            return None
        for target, weight in self._adj[u]:
            if target == v:
                return weight
        return None
    
    def neighbors(self, v: T) -> List[T]:
        """Get list of neighbors of vertex v."""
        return [target for target, _ in self._adj.get(v, [])]
    
    def neighbors_with_weights(self, v: T) -> List[Tuple[T, Weight]]:
        """Get list of (neighbor, weight) tuples for vertex v."""
        return list(self._adj.get(v, []))
    
    @property
    def vertices(self) -> Set[T]:
        """Get all vertices in the graph."""
        return self._vertices.copy()
    
    @property
    def edges(self) -> List[Edge[T]]:
        """Get all edges in the graph."""
        seen = set()
        result = []
        
        for u in self._adj:
            for v, weight in self._adj[u]:
                if self.directed:
                    result.append(Edge(u, v, weight))
                else:
                    edge_key = (min(u, v), max(u, v)) if isinstance(u, str) else (u, v) if u < v else (v, u)
                    if edge_key not in seen:
                        seen.add(edge_key)
                        result.append(Edge(u, v, weight))
        
        return result
    
    @property
    def num_vertices(self) -> int:
        """Number of vertices."""
        return len(self._vertices)
    
    @property
    def num_edges(self) -> int:
        """Number of edges."""
        total = sum(len(neighbors) for neighbors in self._adj.values())
        return total if self.directed else total // 2
    
    def degree(self, v: T) -> int:
        """Get degree of vertex (number of edges)."""
        return len(self._adj.get(v, []))
    
    def in_degree(self, v: T) -> int:
        """Get in-degree (for directed graphs)."""
        if not self.directed:
            return self.degree(v)
        
        count = 0
        for u in self._adj:
            for target, _ in self._adj[u]:
                if target == v:
                    count += 1
        return count
    
    def out_degree(self, v: T) -> int:
        """Get out-degree (for directed graphs)."""
        return len(self._adj.get(v, []))
    
    def __contains__(self, v: T) -> bool:
        return v in self._vertices
    
    def __repr__(self) -> str:
        graph_type = "Directed" if self.directed else "Undirected"
        return f"Graph({graph_type}, V={self.num_vertices}, E={self.num_edges})"
    
    def to_string(self) -> str:
        """Pretty print the graph."""
        lines = [repr(self)]
        for v in sorted(self._vertices, key=str):
            neighbors = self._adj.get(v, [])
            if neighbors:
                neighbor_str = ", ".join(f"{n}({w})" for n, w in sorted(neighbors, key=lambda x: str(x[0])))
                lines.append(f"  {v} → {neighbor_str}")
            else:
                lines.append(f"  {v} → (no edges)")
        return "\n".join(lines)


# =============================================================================
# Union-Find (Disjoint Set)
# =============================================================================

class UnionFind(Generic[T]):
    """
    Union-Find (Disjoint Set Union) data structure.
    
    Efficiently tracks connected components.
    Used in Kruskal's MST algorithm.
    
    Operations:
        find(x): Find root of x's component - O(α(n)) amortized
        union(x, y): Merge components of x and y - O(α(n)) amortized
        connected(x, y): Check if x and y are in same component
    
    Uses path compression and union by rank for near-constant time operations.
    α(n) is the inverse Ackermann function, effectively ≤ 4 for all practical n.
    """
    
    def __init__(self):
        self._parent: Dict[T, T] = {}
        self._rank: Dict[T, int] = {}
    
    def make_set(self, x: T) -> None:
        """Create a new set containing only x."""
        if x not in self._parent:
            self._parent[x] = x
            self._rank[x] = 0
    
    def find(self, x: T) -> T:
        """
        Find the root (representative) of x's component.
        
        Uses path compression: all nodes on path point directly to root.
        """
        if x not in self._parent:
            self.make_set(x)
        
        if self._parent[x] != x:
            self._parent[x] = self.find(self._parent[x])  # Path compression
        return self._parent[x]
    
    def union(self, x: T, y: T) -> bool:
        """
        Merge the components containing x and y.
        
        Returns True if they were in different components (merge happened).
        Uses union by rank to keep trees balanced.
        """
        root_x = self.find(x)
        root_y = self.find(y)
        
        if root_x == root_y:
            return False  # Already in same component
        
        # Union by rank: attach smaller tree under larger
        if self._rank[root_x] < self._rank[root_y]:
            root_x, root_y = root_y, root_x
        
        self._parent[root_y] = root_x
        
        if self._rank[root_x] == self._rank[root_y]:
            self._rank[root_x] += 1
        
        return True
    
    def connected(self, x: T, y: T) -> bool:
        """Check if x and y are in the same component."""
        return self.find(x) == self.find(y)


# =============================================================================
# Traversal Algorithms
# =============================================================================

@dataclass
class TraversalState(Generic[T]):
    """State during graph traversal for visualization."""
    current: T
    visited: Set[T]
    queue_or_stack: List[T]
    parent: Dict[T, Optional[T]]
    step: int


def bfs(
    graph: Graph[T],
    start: T,
    goal: Optional[T] = None
) -> Tuple[Dict[T, int], Dict[T, Optional[T]]]:
    """
    Breadth-First Search.
    
    Explores vertices level by level (closest first).
    Finds shortest paths in unweighted graphs.
    
    Args:
        graph: The graph to search
        start: Starting vertex
        goal: Optional goal vertex (stops early if found)
    
    Returns:
        (distances, parents) where:
        - distances[v] = shortest distance from start to v
        - parents[v] = predecessor of v on shortest path
    
    Time: O(V + E)
    Space: O(V)
    """
    if start not in graph:
        raise ValueError(f"Start vertex {start} not in graph")
    
    distances: Dict[T, int] = {start: 0}
    parents: Dict[T, Optional[T]] = {start: None}
    queue = deque([start])
    
    while queue:
        current = queue.popleft()
        
        if goal is not None and current == goal:
            break
        
        for neighbor in graph.neighbors(current):
            if neighbor not in distances:
                distances[neighbor] = distances[current] + 1
                parents[neighbor] = current
                queue.append(neighbor)
    
    return distances, parents


def bfs_trace(
    graph: Graph[T],
    start: T
) -> Iterator[TraversalState[T]]:
    """
    BFS with step-by-step state for visualization.
    
    Yields TraversalState at each step.
    """
    if start not in graph:
        raise ValueError(f"Start vertex {start} not in graph")
    
    visited: Set[T] = {start}
    parents: Dict[T, Optional[T]] = {start: None}
    queue = deque([start])
    step = 0
    
    while queue:
        current = queue.popleft()
        
        yield TraversalState(
            current=current,
            visited=visited.copy(),
            queue_or_stack=list(queue),
            parent=parents.copy(),
            step=step
        )
        step += 1
        
        for neighbor in graph.neighbors(current):
            if neighbor not in visited:
                visited.add(neighbor)
                parents[neighbor] = current
                queue.append(neighbor)


def dfs(
    graph: Graph[T],
    start: T,
    goal: Optional[T] = None
) -> Tuple[Dict[T, int], Dict[T, Optional[T]]]:
    """
    Depth-First Search (iterative).
    
    Explores as deep as possible before backtracking.
    
    Args:
        graph: The graph to search
        start: Starting vertex
        goal: Optional goal vertex
    
    Returns:
        (discovery_time, parents)
    
    Time: O(V + E)
    Space: O(V)
    """
    if start not in graph:
        raise ValueError(f"Start vertex {start} not in graph")
    
    discovery: Dict[T, int] = {}
    parents: Dict[T, Optional[T]] = {start: None}
    stack = [start]
    time = 0
    
    while stack:
        current = stack.pop()
        
        if current in discovery:
            continue
        
        discovery[current] = time
        time += 1
        
        if goal is not None and current == goal:
            break
        
        for neighbor in graph.neighbors(current):
            if neighbor not in discovery:
                if neighbor not in parents:
                    parents[neighbor] = current
                stack.append(neighbor)
    
    return discovery, parents


def dfs_recursive(
    graph: Graph[T],
    start: T,
    visited: Optional[Set[T]] = None,
    pre_visit: Optional[Callable[[T], None]] = None,
    post_visit: Optional[Callable[[T], None]] = None
) -> Set[T]:
    """
    Recursive DFS with customizable visit callbacks.
    
    Useful for topological sort, cycle detection, etc.
    """
    if visited is None:
        visited = set()
    
    visited.add(start)
    
    if pre_visit:
        pre_visit(start)
    
    for neighbor in graph.neighbors(start):
        if neighbor not in visited:
            dfs_recursive(graph, neighbor, visited, pre_visit, post_visit)
    
    if post_visit:
        post_visit(start)
    
    return visited


# =============================================================================
# Shortest Path Algorithms
# =============================================================================

@dataclass
class DijkstraState(Generic[T]):
    """State during Dijkstra's algorithm for visualization."""
    current: T
    current_distance: Weight
    distances: Dict[T, Weight]
    visited: Set[T]
    frontier: List[Tuple[Weight, T]]
    step: int


def dijkstra(
    graph: Graph[T],
    start: T,
    goal: Optional[T] = None
) -> Tuple[Dict[T, Weight], Dict[T, Optional[T]]]:
    """
    Dijkstra's Single-Source Shortest Paths.
    
    Finds shortest paths from start to all reachable vertices.
    Works with non-negative edge weights.
    
    Algorithm:
        1. Initialize distances: start=0, others=∞
        2. Use priority queue ordered by distance
        3. Process closest unvisited vertex
        4. Update neighbors if shorter path found
        5. Repeat until all reachable vertices processed
    
    Args:
        graph: The graph (weights must be non-negative)
        start: Starting vertex
        goal: Optional goal (stops early if found)
    
    Returns:
        (distances, parents) where:
        - distances[v] = shortest distance from start to v
        - parents[v] = predecessor of v on shortest path
    
    Time: O((V + E) log V) with binary heap
    Space: O(V)
    """
    if start not in graph:
        raise ValueError(f"Start vertex {start} not in graph")
    
    distances: Dict[T, Weight] = {start: 0}
    parents: Dict[T, Optional[T]] = {start: None}
    visited: Set[T] = set()
    
    # Priority queue: (distance, vertex)
    # heapq is a min-heap, so smallest distance comes first
    heap: List[Tuple[Weight, T]] = [(0, start)]
    
    while heap:
        current_dist, current = heapq.heappop(heap)
        
        if current in visited:
            continue
        
        visited.add(current)
        
        if goal is not None and current == goal:
            break
        
        for neighbor, weight in graph.neighbors_with_weights(current):
            if weight < 0:
                raise ValueError(f"Negative edge weight: {current} → {neighbor} ({weight})")
            
            new_dist = current_dist + weight
            
            if neighbor not in distances or new_dist < distances[neighbor]:
                distances[neighbor] = new_dist
                parents[neighbor] = current
                heapq.heappush(heap, (new_dist, neighbor))
    
    return distances, parents


def dijkstra_trace(
    graph: Graph[T],
    start: T
) -> Iterator[DijkstraState[T]]:
    """
    Dijkstra's algorithm with step-by-step state for visualization.
    
    Yields DijkstraState at each step showing:
    - Current vertex being processed
    - All distances computed so far
    - The frontier (priority queue)
    """
    if start not in graph:
        raise ValueError(f"Start vertex {start} not in graph")
    
    distances: Dict[T, Weight] = {start: 0}
    parents: Dict[T, Optional[T]] = {start: None}
    visited: Set[T] = set()
    heap: List[Tuple[Weight, T]] = [(0, start)]
    step = 0
    
    while heap:
        current_dist, current = heapq.heappop(heap)
        
        if current in visited:
            continue
        
        visited.add(current)
        
        yield DijkstraState(
            current=current,
            current_distance=current_dist,
            distances=distances.copy(),
            visited=visited.copy(),
            frontier=list(heap),
            step=step
        )
        step += 1
        
        for neighbor, weight in graph.neighbors_with_weights(current):
            new_dist = current_dist + weight
            
            if neighbor not in distances or new_dist < distances[neighbor]:
                distances[neighbor] = new_dist
                parents[neighbor] = current
                heapq.heappush(heap, (new_dist, neighbor))


def bellman_ford(
    graph: Graph[T],
    start: T
) -> Tuple[Dict[T, Weight], Dict[T, Optional[T]], bool]:
    """
    Bellman-Ford Single-Source Shortest Paths.
    
    Like Dijkstra but handles negative edge weights.
    Can detect negative cycles.
    
    Algorithm:
        1. Initialize distances
        2. Relax all edges V-1 times
        3. Check for negative cycles (any edge can still be relaxed)
    
    Returns:
        (distances, parents, has_negative_cycle)
    
    Time: O(VE)
    Space: O(V)
    """
    if start not in graph:
        raise ValueError(f"Start vertex {start} not in graph")
    
    vertices = graph.vertices
    edges = graph.edges
    
    distances: Dict[T, Weight] = {v: float('inf') for v in vertices}
    parents: Dict[T, Optional[T]] = {v: None for v in vertices}
    distances[start] = 0
    
    # Relax all edges V-1 times
    for _ in range(len(vertices) - 1):
        for edge in edges:
            if distances[edge.source] + edge.weight < distances[edge.target]:
                distances[edge.target] = distances[edge.source] + edge.weight
                parents[edge.target] = edge.source
    
    # Check for negative cycles
    has_negative_cycle = False
    for edge in edges:
        if distances[edge.source] + edge.weight < distances[edge.target]:
            has_negative_cycle = True
            break
    
    return distances, parents, has_negative_cycle


def reconstruct_path(
    parents: Dict[T, Optional[T]],
    start: T,
    goal: T
) -> Optional[List[T]]:
    """
    Reconstruct path from start to goal using parent pointers.
    
    Returns None if no path exists.
    """
    if goal not in parents:
        return None
    
    path = []
    current: Optional[T] = goal
    
    while current is not None:
        path.append(current)
        current = parents[current]
    
    path.reverse()
    
    if path[0] != start:
        return None
    
    return path


# =============================================================================
# Minimum Spanning Tree
# =============================================================================

@dataclass
class MSTState(Generic[T]):
    """State during MST algorithm for visualization."""
    mst_edges: List[Edge[T]]
    total_weight: Weight
    current_edge: Optional[Edge[T]]
    step: int


def kruskal_mst(graph: Graph[T]) -> Tuple[List[Edge[T]], Weight]:
    """
    Kruskal's Minimum Spanning Tree.
    
    Finds a subset of edges that connects all vertices with minimum total weight.
    
    Algorithm:
        1. Sort edges by weight
        2. For each edge (smallest first):
           - If it connects two different components, add it to MST
           - Use Union-Find to track components
    
    Time: O(E log E) = O(E log V) for sorting
    Space: O(V) for Union-Find
    
    Only works for undirected graphs.
    """
    if graph.directed:
        raise ValueError("Kruskal's MST only works for undirected graphs")
    
    edges = sorted(graph.edges, key=lambda e: e.weight)
    uf = UnionFind[T]()
    
    mst: List[Edge[T]] = []
    total_weight: Weight = 0
    
    for edge in edges:
        if uf.union(edge.source, edge.target):
            mst.append(edge)
            total_weight += edge.weight
            
            # MST has exactly V-1 edges
            if len(mst) == graph.num_vertices - 1:
                break
    
    return mst, total_weight


def kruskal_mst_trace(graph: Graph[T]) -> Iterator[MSTState[T]]:
    """
    Kruskal's MST with step-by-step state for visualization.
    """
    if graph.directed:
        raise ValueError("Kruskal's MST only works for undirected graphs")
    
    edges = sorted(graph.edges, key=lambda e: e.weight)
    uf = UnionFind[T]()
    
    mst: List[Edge[T]] = []
    total_weight: Weight = 0
    step = 0
    
    for edge in edges:
        yield MSTState(
            mst_edges=mst.copy(),
            total_weight=total_weight,
            current_edge=edge,
            step=step
        )
        step += 1
        
        if uf.union(edge.source, edge.target):
            mst.append(edge)
            total_weight += edge.weight
            
            if len(mst) == graph.num_vertices - 1:
                break
    
    yield MSTState(
        mst_edges=mst,
        total_weight=total_weight,
        current_edge=None,
        step=step
    )


def prim_mst(graph: Graph[T], start: Optional[T] = None) -> Tuple[List[Edge[T]], Weight]:
    """
    Prim's Minimum Spanning Tree.
    
    Grows MST from a starting vertex by always adding the minimum-weight
    edge that connects a new vertex.
    
    Time: O((V + E) log V) with binary heap
    Space: O(V)
    """
    if graph.directed:
        raise ValueError("Prim's MST only works for undirected graphs")
    
    if graph.num_vertices == 0:
        return [], 0
    
    if start is None:
        start = next(iter(graph.vertices))
    
    visited: Set[T] = {start}
    mst: List[Edge[T]] = []
    total_weight: Weight = 0
    
    # Priority queue: (weight, source, target)
    heap: List[Tuple[Weight, T, T]] = []
    
    for neighbor, weight in graph.neighbors_with_weights(start):
        heapq.heappush(heap, (weight, start, neighbor))
    
    while heap and len(visited) < graph.num_vertices:
        weight, source, target = heapq.heappop(heap)
        
        if target in visited:
            continue
        
        visited.add(target)
        mst.append(Edge(source, target, weight))
        total_weight += weight
        
        for neighbor, edge_weight in graph.neighbors_with_weights(target):
            if neighbor not in visited:
                heapq.heappush(heap, (edge_weight, target, neighbor))
    
    return mst, total_weight


# =============================================================================
# DAG Algorithms
# =============================================================================

def topological_sort(graph: Graph[T]) -> Optional[List[T]]:
    """
    Topological Sort using Kahn's algorithm.
    
    Returns vertices in an order such that for every edge (u, v),
    u comes before v in the ordering.
    
    Only works on Directed Acyclic Graphs (DAGs).
    Returns None if the graph has a cycle.
    
    Applications:
        - Build systems (make, gradle)
        - Package managers (npm, pip)
        - Task scheduling
    
    Time: O(V + E)
    Space: O(V)
    """
    if not graph.directed:
        raise ValueError("Topological sort only works for directed graphs")
    
    # Calculate in-degrees
    in_degree: Dict[T, int] = {v: 0 for v in graph.vertices}
    for v in graph.vertices:
        for neighbor in graph.neighbors(v):
            in_degree[neighbor] += 1
    
    # Start with vertices that have no dependencies
    queue = deque([v for v in graph.vertices if in_degree[v] == 0])
    result: List[T] = []
    
    while queue:
        current = queue.popleft()
        result.append(current)
        
        for neighbor in graph.neighbors(current):
            in_degree[neighbor] -= 1
            if in_degree[neighbor] == 0:
                queue.append(neighbor)
    
    # If we processed all vertices, no cycle exists
    if len(result) == graph.num_vertices:
        return result
    
    return None  # Cycle detected


def has_cycle(graph: Graph[T]) -> bool:
    """
    Detect if graph has a cycle.
    
    For directed graphs: Uses DFS coloring
    For undirected graphs: Uses Union-Find
    """
    if graph.directed:
        return _has_cycle_directed(graph)
    else:
        return _has_cycle_undirected(graph)


def _has_cycle_directed(graph: Graph[T]) -> bool:
    """Detect cycle in directed graph using DFS coloring."""
    WHITE, GRAY, BLACK = 0, 1, 2
    color: Dict[T, int] = {v: WHITE for v in graph.vertices}
    
    def dfs(v: T) -> bool:
        color[v] = GRAY
        
        for neighbor in graph.neighbors(v):
            if color[neighbor] == GRAY:
                return True  # Back edge = cycle
            if color[neighbor] == WHITE and dfs(neighbor):
                return True
        
        color[v] = BLACK
        return False
    
    for v in graph.vertices:
        if color[v] == WHITE:
            if dfs(v):
                return True
    
    return False


def _has_cycle_undirected(graph: Graph[T]) -> bool:
    """Detect cycle in undirected graph using Union-Find."""
    uf = UnionFind[T]()
    
    for v in graph.vertices:
        uf.make_set(v)
    
    seen_edges: Set[Tuple[T, T]] = set()
    
    for v in graph.vertices:
        for neighbor, _ in graph.neighbors_with_weights(v):
            edge = (min(v, neighbor), max(v, neighbor)) if isinstance(v, str) else (v, neighbor) if v < neighbor else (neighbor, v)
            
            if edge in seen_edges:
                continue
            seen_edges.add(edge)
            
            if not uf.union(v, neighbor):
                return True  # Already in same component = cycle
    
    return False


# =============================================================================
# Connected Components
# =============================================================================

def connected_components(graph: Graph[T]) -> List[Set[T]]:
    """
    Find all connected components in an undirected graph.
    
    Returns a list of sets, each containing vertices in one component.
    
    Time: O(V + E)
    """
    if graph.directed:
        raise ValueError("Use strongly_connected_components for directed graphs")
    
    visited: Set[T] = set()
    components: List[Set[T]] = []
    
    for v in graph.vertices:
        if v not in visited:
            component: Set[T] = set()
            stack = [v]
            
            while stack:
                current = stack.pop()
                if current in visited:
                    continue
                    
                visited.add(current)
                component.add(current)
                
                for neighbor in graph.neighbors(current):
                    if neighbor not in visited:
                        stack.append(neighbor)
            
            components.append(component)
    
    return components


def is_connected(graph: Graph[T]) -> bool:
    """Check if the graph is connected (all vertices reachable from any vertex)."""
    if graph.num_vertices == 0:
        return True
    
    start = next(iter(graph.vertices))
    distances, _ = bfs(graph, start)
    
    return len(distances) == graph.num_vertices


# =============================================================================
# Visualization
# =============================================================================

def visualize_graph(graph: Graph[T]) -> str:
    """Create ASCII visualization of a small graph."""
    lines = []
    lines.append(f"{'Directed' if graph.directed else 'Undirected'} Graph")
    lines.append(f"Vertices: {graph.num_vertices}, Edges: {graph.num_edges}")
    lines.append("")
    
    for v in sorted(graph.vertices, key=str):
        neighbors = graph.neighbors_with_weights(v)
        if neighbors:
            edges_str = ", ".join(f"→{n}({w})" for n, w in sorted(neighbors, key=lambda x: str(x[0])))
            lines.append(f"  [{v}] {edges_str}")
        else:
            lines.append(f"  [{v}] (no outgoing edges)")
    
    return "\n".join(lines)


def visualize_path(
    graph: Graph[T],
    path: List[T],
    distances: Optional[Dict[T, Weight]] = None
) -> str:
    """Visualize a path through the graph."""
    if not path:
        return "Empty path"
    
    lines = []
    lines.append("Path: " + " → ".join(str(v) for v in path))
    
    total_weight = 0
    for i in range(len(path) - 1):
        weight = graph.get_weight(path[i], path[i + 1])
        if weight is not None:
            total_weight += weight
            lines.append(f"  {path[i]} --({weight})--> {path[i + 1]}")
    
    lines.append(f"Total weight: {total_weight}")
    
    if distances:
        lines.append(f"Distance to goal: {distances.get(path[-1], 'unknown')}")
    
    return "\n".join(lines)


def visualize_mst(mst: List[Edge[T]], total_weight: Weight) -> str:
    """Visualize a minimum spanning tree."""
    lines = []
    lines.append(f"Minimum Spanning Tree ({len(mst)} edges)")
    lines.append(f"Total weight: {total_weight}")
    lines.append("")
    
    for i, edge in enumerate(mst, 1):
        lines.append(f"  {i}. {edge.source} --({edge.weight})--> {edge.target}")
    
    return "\n".join(lines)


# =============================================================================
# Graph Builders
# =============================================================================

def complete_graph(n: int) -> Graph[int]:
    """Create a complete graph with n vertices (every vertex connected to every other)."""
    g: Graph[int] = Graph(directed=False)
    for i in range(n):
        for j in range(i + 1, n):
            g.add_edge(i, j, 1)
    return g


def grid_graph(rows: int, cols: int) -> Graph[Tuple[int, int]]:
    """Create a grid graph."""
    g: Graph[Tuple[int, int]] = Graph(directed=False)
    
    for r in range(rows):
        for c in range(cols):
            if c + 1 < cols:
                g.add_edge((r, c), (r, c + 1), 1)
            if r + 1 < rows:
                g.add_edge((r, c), (r + 1, c), 1)
    
    return g


def from_edges(edges: List[Tuple[T, T, Weight]], directed: bool = False) -> Graph[T]:
    """Create a graph from a list of (source, target, weight) tuples."""
    g: Graph[T] = Graph(directed=directed)
    for source, target, weight in edges:
        g.add_edge(source, target, weight)
    return g


# =============================================================================
# Exports
# =============================================================================

__all__ = [
    # Types
    'GraphType', 'Edge', 'Weight',
    
    # Core
    'Graph', 'UnionFind',
    
    # Traversal
    'bfs', 'bfs_trace', 'dfs', 'dfs_recursive',
    'TraversalState',
    
    # Shortest Paths
    'dijkstra', 'dijkstra_trace', 'bellman_ford',
    'reconstruct_path', 'DijkstraState',
    
    # MST
    'kruskal_mst', 'kruskal_mst_trace', 'prim_mst',
    'MSTState',
    
    # DAG
    'topological_sort', 'has_cycle',
    
    # Components
    'connected_components', 'is_connected',
    
    # Visualization
    'visualize_graph', 'visualize_path', 'visualize_mst',
    
    # Builders
    'complete_graph', 'grid_graph', 'from_edges',
]
