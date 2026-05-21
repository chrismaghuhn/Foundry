"""Pathfinding lab for graph module."""

from __future__ import annotations

from typing import Any

from labs.import_path import ensure_foundry_path
from labs.lab_models import LabDefinition, LabInputField, LabPreset, LabRunResult, LabVisual
from labs.adapters._helpers import error_result, merge_preset_input, ok_result

PRESETS: dict[str, dict[str, Any]] = {
    "simple-path": {"algorithm": "bfs", "start": "A", "goal": "D", "graph": "diamond"},
    "weighted": {"algorithm": "dijkstra", "start": "A", "goal": "D", "graph": "weighted"},
}


def _build_graph(name: str):
    ensure_foundry_path()
    from graph.graph import Graph

    g: Graph[str] = Graph(directed=False)
    if name == "diamond":
        for n in "ABCD":
            g.add_vertex(n)
        g.add_edge("A", "B", 1)
        g.add_edge("A", "C", 1)
        g.add_edge("B", "D", 1)
        g.add_edge("C", "D", 1)
    else:
        for n in "ABCD":
            g.add_vertex(n)
        g.add_edge("A", "B", 3)
        g.add_edge("A", "C", 1)
        g.add_edge("B", "D", 2)
        g.add_edge("C", "D", 4)
    return g


def _reconstruct(parents: dict, goal: str) -> list[str]:
    path = []
    cur: str | None = goal
    while cur is not None:
        path.append(cur)
        cur = parents.get(cur)
    path.reverse()
    return path


def get_definition() -> LabDefinition:
    return LabDefinition(
        moduleId="graph",
        title="Pathfinding Lab",
        description="Pick start and goal on a tiny graph and compare BFS vs Dijkstra.",
        mission="Find the shortest route — watch which nodes get visited first.",
        kind="visual",
        tier=1,
        safety="safe",
        primaryAction="Find path",
        presets=[
            LabPreset(id="simple-path", label="Simple path (BFS)", isDefault=True),
            LabPreset(id="weighted", label="Weighted edges (Dijkstra)"),
        ],
        inputs=[
            LabInputField(
                name="algorithm",
                type="select",
                label="Algorithm",
                default="bfs",
                options=[
                    {"value": "bfs", "label": "BFS"},
                    {"value": "dijkstra", "label": "Dijkstra"},
                ],
            ),
            LabInputField(name="start", type="text", label="Start", default="A"),
            LabInputField(name="goal", type="text", label="Goal", default="D"),
            LabInputField(
                name="graph",
                type="select",
                label="Graph preset",
                default="diamond",
                options=[
                    {"value": "diamond", "label": "Diamond"},
                    {"value": "weighted", "label": "Weighted diamond"},
                ],
            ),
        ],
    )


def run_lab(payload: dict) -> LabRunResult:
    try:
        inp = merge_preset_input(payload, PRESETS)
        algo = inp.get("algorithm", "bfs")
        start = str(inp.get("start", "A")).strip().upper()
        goal = str(inp.get("goal", "D")).strip().upper()
        graph_name = inp.get("graph", "diamond")
        g = _build_graph(graph_name)

        ensure_foundry_path()
        from graph.graph import bfs, dijkstra, reconstruct_path

        if algo == "dijkstra":
            dist, parents = dijkstra(g, start)
            if goal not in dist:
                return error_result("graph", f"No path from {start} to {goal}.", input_data=inp)
            path = reconstruct_path(parents, goal)
            visited_order = sorted(dist.keys(), key=lambda n: dist[n])
            summary = f"Dijkstra: path {''.join(path)} with cost {dist[goal]}."
            expl = [
                "Dijkstra picks the lowest-cost frontier node each step.",
                "Works on weighted graphs when edge weights are non-negative.",
            ]
        else:
            dist, parents = bfs(g, start, goal)
            if goal not in parents:
                return error_result("graph", f"No path from {start} to {goal}.", input_data=inp)
            path = _reconstruct(parents, goal)
            visited_order = sorted(dist.keys(), key=lambda n: dist[n])
            summary = f"BFS: path {''.join(path)} in {dist[goal]} steps."
            expl = [
                "BFS explores neighbors level by level.",
                "On unweighted graphs the first arrival at the goal is a shortest path.",
            ]

        edges = []
        nodes = list(g.vertices)
        for u in nodes:
            for v, w in g.neighbors_with_weights(u):
                edges.append({"from": str(u), "to": str(v), "weight": w})

        return ok_result(
            "graph",
            summary,
            input_data=inp,
            result={"path": path, "distance": dist.get(goal), "visited": visited_order},
            visual=LabVisual(
                type="graph-path",
                data={
                    "nodes": [{"id": str(n)} for n in nodes],
                    "edges": edges,
                    "path": path,
                    "visited": visited_order,
                    "start": start,
                    "goal": goal,
                },
            ),
            explanation=expl,
        )
    except Exception as exc:
        return error_result("graph", str(exc), input_data=payload.get("input", {}))
