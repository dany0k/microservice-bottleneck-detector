import networkx as nx


class GraphAnalyzer:

    @staticmethod
    def print_stats(G: nx.DiGraph):
        print("=== GRAPH STATS ===")
        print("Nodes:", len(G.nodes))
        print("Edges:", len(G.edges))
        print()

        for u, v in G.edges:
            avg = G[u][v].get("avg_latency", 0.0)
            cap = G[u][v].get("capacity", 0.0)
            calls = G[u][v].get("count", len(G[u][v].get("times", [])))
            print(f"{u} → {v}: calls={calls}, avg={avg:.2f} ms, cap={cap:.4f}")

    @staticmethod
    def max_flow(G: nx.DiGraph, source: str, sink: str, capacity_attr: str = "capacity"):
        """Compute max flow using the specified capacity attribute on edges."""
        return nx.maximum_flow(G, source, sink, capacity=capacity_attr)

    @staticmethod
    def min_cut(G: nx.DiGraph, source: str, sink: str, capacity_attr: str = "capacity"):
        """Compute minimum cut using the specified capacity attribute on edges."""
        return nx.minimum_cut(G, source, sink, capacity=capacity_attr)
