import networkx as nx
from typing import List
from datetime import datetime

from mbd.model.record import LogRecord


class GraphBuilder:

    @staticmethod
    def build_graph(records: List[LogRecord]) -> nx.DiGraph:
        """Builds a directed service graph from log records.

        For each edge we store:
        - times: list of observed latencies (ms)
        - count: number of calls observed
        - avg_latency: average latency (ms)
        - throughput: estimated calls per second over the observed time span
        - capacity_latency: capacity derived from latency (1 / avg_latency)
        - capacity_throughput: capacity derived from throughput (throughput)
        - capacity: chosen default capacity (throughput if available, otherwise latency-based)
        """
        G = nx.DiGraph()

        timestamps = []

        for r in records:
            src = r.src_service
            dst = r.dst_service
            latency = r.latency

            # collect timestamps to compute observed time window
            try:
                ts = datetime.fromisoformat(r.timestamp.replace("Z", "+00:00"))
                timestamps.append(ts)
            except Exception:
                # ignore parse errors; will use fallback duration
                pass

            if G.has_edge(src, dst):
                G[src][dst]["times"].append(latency)
                G[src][dst]["count"] += 1
            else:
                G.add_edge(src, dst, times=[latency], count=1)

        # compute time window
        if timestamps:
            duration = (max(timestamps) - min(timestamps)).total_seconds()
            if duration <= 0:
                duration = 1.0
        else:
            duration = 1.0

        for src, dst in G.edges:
            times = G[src][dst]["times"]
            count = G[src][dst].get("count", len(times))
            avg = sum(times) / len(times)
            throughput = count / duration

            G[src][dst]["avg_latency"] = avg
            G[src][dst]["count"] = count
            G[src][dst]["throughput"] = throughput
            G[src][dst]["capacity_latency"] = 1.0 / avg if avg > 0 else 0.0
            G[src][dst]["capacity_throughput"] = throughput

            # default capacity prefer throughput when available (represents requests/sec)
            G[src][dst]["capacity"] = throughput if throughput > 0 else G[src][dst]["capacity_latency"]

        # compute per-node load: sum of incident throughputs (in + out)
        for n in list(G.nodes):
            in_throughput = 0.0
            out_throughput = 0.0
            for u, v in G.in_edges(n):
                in_throughput += G[u][v].get("throughput", 0.0)
            for u, v in G.out_edges(n):
                out_throughput += G[u][v].get("throughput", 0.0)

            node_load = in_throughput + out_throughput
            # store load and breakdown
            G.nodes[n]["load"] = node_load
            G.nodes[n]["in_throughput"] = in_throughput
            G.nodes[n]["out_throughput"] = out_throughput

        return G
