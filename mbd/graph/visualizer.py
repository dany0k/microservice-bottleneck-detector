import networkx as nx
import pydot
from pathlib import Path
from typing import Iterable, Tuple, Optional, List

from pyvis.network import Network


class GraphVisualizer:
    def __init__(self, output_dir: str = "out"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def render_service_graph(self, graph: nx.DiGraph, filename: str = "service_graph.png", bottlenecks: Iterable[Tuple[str, str]] = None):
        """Render the graph to PNG via Graphviz. Optionally highlight bottleneck edges.

        `bottlenecks` is an iterable of (u, v) edges to highlight.
        """
        dot_path = self.output_dir / "service_graph.dot"

        # annotate edges for highlighting
        if bottlenecks:
            highlighted = set(bottlenecks)
            for u, v in graph.edges:
                attrs = graph[u][v]
                if (u, v) in highlighted:
                    attrs["color"] = "red"
                    attrs["penwidth"] = "3"
                else:
                    attrs.setdefault("color", "black")
                    attrs.setdefault("penwidth", "1")

        # Save graph to DOT
        nx.drawing.nx_pydot.write_dot(graph, dot_path)

        # Render via pydot → Graphviz
        (graphviz_graph,) = pydot.graph_from_dot_file(str(dot_path))
        output_path = self.output_dir / filename
        graphviz_graph.write_png(str(output_path))

        print(f"[OK] Graph saved to {output_path}")

    def render_pyvis(self, graph: nx.DiGraph, filename: str = "service_graph.html", highlighted_edges: Optional[Iterable[Tuple[str, str]]] = None, edge_label_attr: Optional[str] = "avg_latency") -> str:
        """Render an interactive HTML graph using pyvis. Returns output path string.

        `highlighted_edges` - iterable of (u,v) to color red.
        `edge_label_attr` - edge attribute to show as label (if present).
        """
        net = Network(height="800px", width="100%", directed=True, notebook=False)

        # compute min/max load for normalization
        loads = [graph.nodes[n].get("load", 0.0) for n in graph.nodes]
        min_load = min(loads) if loads else 0.0
        max_load = max(loads) if loads else 0.0

        # add nodes with size based on relative load
        for n in graph.nodes:
            load = graph.nodes[n].get("load", 0.0)
            # normalize to size range 10..60
            size = 10
            if max_load > min_load:
                frac = (load - min_load) / (max_load - min_load)
                size = 10 + frac * 50
            color = "#97c2fc"
            # more loaded nodes - warmer color
            if max_load > 0:
                intensity = int(255 * ((load - min_load) / (max_load - min_load)) ) if max_load>min_load else 0
                # map intensity to color from light blue to red-ish
                r = min(255, 100 + intensity)
                g = max(50, 200 - intensity)
                b = max(50, 200 - intensity//2)
                color = f"rgb({r},{g},{b})"
            title = n + "\nload=" + f"{load:.3f}"
            net.add_node(n, label=n, title=title, value=size, size=size, color=color)

        highlighted = set(highlighted_edges or [])

        # add edges
        for u, v in graph.edges:
            attrs = graph[u][v]
            label = ""
            if edge_label_attr and edge_label_attr in attrs:
                label = f"{attrs[edge_label_attr]:.2f}"
            color = "red" if (u, v) in highlighted else attrs.get("color", "black")
            width = float(attrs.get("penwidth", 1))
            net.add_edge(u, v, title=label, color=color, width=width)

        out_path = str(self.output_dir / filename)
        net.show(out_path)
        print(f"[OK] Interactive graph saved to {out_path}")
        return out_path
