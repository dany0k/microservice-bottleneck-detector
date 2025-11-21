"""Bottleneck detection utilities: run sliding-window max-flow/min-cut and aggregate results."""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import List, Tuple, Dict, Any

import networkx as nx

from mbd.model.record import LogRecord
from mbd.graph.graph_builder import GraphBuilder
from mbd.graph.analyzer import GraphAnalyzer


def parse_iso_z(s: str) -> datetime:
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def sliding_windows(records: List[LogRecord], window_seconds: int, step_seconds: int):
    if not records:
        return

    times = [parse_iso_z(r.timestamp) for r in records]
    start = min(times)
    end = max(times)
    current = start
    while current <= end:
        window_end = current + timedelta(seconds=window_seconds)
        yield current, window_end
        current = current + timedelta(seconds=step_seconds)


def records_in_window(records: List[LogRecord], start: datetime, end: datetime) -> List[LogRecord]:
    out = []
    for r in records:
        ts = parse_iso_z(r.timestamp)
        if start <= ts <= end:
            out.append(r)
    return out


def analyze_time_windows(records: List[LogRecord], source: str, sink: str, window_seconds: int = 60, step_seconds: int = 30, capacity_attr: str = "capacity") -> List[Dict[str, Any]]:
    """Run sliding-window analysis. Returns list of dicts with window start/end, flow_value, min_cut_edges.

    Each dict: {"start": datetime, "end": datetime, "flow": float, "min_cut": [(u,v), ...]}
    """
    results = []
    for start, end in sliding_windows(records, window_seconds, step_seconds):
        window_records = records_in_window(records, start, end)
        if not window_records:
            results.append({"start": start, "end": end, "flow": 0.0, "min_cut": []})
            continue

        G = GraphBuilder.build_graph(window_records)

        # ensure source and sink are present
        if source not in G.nodes or sink not in G.nodes:
            results.append({"start": start, "end": end, "flow": 0.0, "min_cut": []})
            continue

        try:
            flow_value, flow_dict = GraphAnalyzer.max_flow(G, source, sink, capacity_attr)
            cut_value, (S, T) = GraphAnalyzer.min_cut(G, source, sink, capacity_attr)
        except Exception:
            # if algorithm fails (disconnected, etc.)
            results.append({"start": start, "end": end, "flow": 0.0, "min_cut": []})
            continue

        # collect min-cut edges
        bottlenecks = []
        for u in S:
            for v in G.successors(u):
                if v in T:
                    bottlenecks.append((u, v))

        results.append({"start": start, "end": end, "flow": flow_value, "min_cut": bottlenecks, "cut_value": cut_value})

    return results


def aggregate_bottlenecks(window_results: List[Dict[str, Any]], top_k: int = 10) -> List[Tuple[Tuple[str, str], int]]:
    """Count how often each edge appears in min-cuts across windows and return top_k edges."""
    counter = {}
    for w in window_results:
        for e in w.get("min_cut", []):
            counter[e] = counter.get(e, 0) + 1
    items = sorted(counter.items(), key=lambda kv: kv[1], reverse=True)
    return items[:top_k]
