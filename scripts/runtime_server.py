import argparse
import csv
import json
import threading
import time
from collections import deque
from datetime import datetime, timedelta

from flask import Flask, jsonify, send_file

from mbd.model.record import LogRecord
from mbd.graph.bottleneck import analyze_time_windows, aggregate_bottlenecks
from mbd.graph.visualizer import GraphVisualizer


def parse_csv_line(line: str) -> LogRecord:
    # robust CSV parse for a single line
    reader = csv.reader([line])
    row = next(reader)
    if not row or row[0].startswith("#"):
        return None
    timestamp, src, src_ep, dst, dst_ep, latency = row
    return LogRecord(timestamp=timestamp, src_service=src, src_endpoint=src_ep, dst_service=dst, dst_endpoint=dst_ep, latency=float(latency))


class RuntimeAnalyzer:
    def __init__(self, log_path: str, source: str, sink: str, window: int = 60, step: int = 30, capacity: str = "capacity"):
        self.log_path = log_path
        self.source = source
        self.sink = sink
        self.window = window
        self.step = step
        self.capacity = capacity

        self.records = []
        self.lock = threading.Lock()
        self.latest_windows = []
        self.latest_bottlenecks = []
        self.latest_graph = None

        self.visualizer = GraphVisualizer(output_dir="out")

    def tail_loop(self, poll_interval: float = 0.5):
        # open and seek to end
        with open(self.log_path, "r") as f:
            f.seek(0, 2)
            while True:
                line = f.readline()
                if not line:
                    time.sleep(poll_interval)
                    continue
                try:
                    rec = parse_csv_line(line.strip())
                except Exception:
                    continue
                if rec is None:
                    continue
                with self.lock:
                    self.records.append(rec)

    def analyze_loop(self, analyze_interval: float = 5.0):
        while True:
            time.sleep(analyze_interval)
            with self.lock:
                records_copy = list(self.records)
            if not records_copy:
                continue

            # run sliding-window analysis on available records
            try:
                windows = analyze_time_windows(records_copy, self.source, self.sink, self.window, self.step, capacity_attr=self.capacity)
                top = aggregate_bottlenecks(windows, top_k=10)
            except Exception:
                windows = []
                top = []

            with self.lock:
                self.latest_windows = windows
                self.latest_bottlenecks = top

            # NOTE: don't try to build `latest_graph` from an undefined G here.
            # We'll build latest_graph below when we have `windows` and construct G.

            # update interactive graph HTML to reflect current loads and highlight top bottlenecks
            if windows:
                # pick last window's graph for visualization
                last_window = windows[-1]
                # build graph anew from the records in the last window
                try:
                    from mbd.graph.graph_builder import GraphBuilder

                    # use end of last window to filter records
                    start = last_window.get("start")
                    end = last_window.get("end")
                    # filter records by timestamp range (string ISO)
                    def in_range(r):
                        try:
                            ts = datetime.fromisoformat(r.timestamp.replace("Z", "+00:00"))
                            return start <= ts <= end
                        except Exception:
                            return False

                    window_recs = [r for r in records_copy if in_range(r)]
                    G = GraphBuilder.build_graph(window_recs)
                    highlighted = [e for e, cnt in top[:5]]
                    # build serializable latest_graph from G (used by /graph-data & /graph-live)
                    try:
                        nodes = []
                        edges = []
                        loads = [G.nodes[n].get("load", 0.0) for n in G.nodes]
                        min_load = min(loads) if loads else 0.0
                        max_load = max(loads) if loads else 0.0
                        for n in G.nodes:
                            load = G.nodes[n].get("load", 0.0)
                            size = 10
                            if max_load > min_load:
                                frac = (load - min_load) / (max_load - min_load)
                                size = 10 + frac * 50
                            color = "#97c2fc"
                            if max_load > 0 and max_load > min_load:
                                intensity = int(255 * ((load - min_load) / (max_load - min_load)))
                                r = min(255, 100 + intensity)
                                g = max(50, 200 - intensity)
                                b = max(50, 200 - intensity // 2)
                                color = f"rgb({r},{g},{b})"
                            title = f"{n}\nload={load:.3f}"
                            nodes.append({"id": n, "label": n, "title": title, "size": size, "color": color})

                        for u, v in G.edges:
                            attrs = G[u][v]
                            label = ""
                            if "avg_latency" in attrs:
                                label = f"{attrs['avg_latency']:.2f}"
                            color = "red" if (u, v) in highlighted else attrs.get("color", "black")
                            width = float(attrs.get("penwidth", 1))
                            edges.append({"from": u, "to": v, "label": label, "color": color, "width": width})

                        with self.lock:
                            self.latest_graph = {"nodes": nodes, "edges": edges}
                    except Exception:
                        pass

                    # also render pyvis HTML for convenience
                    self.visualizer.render_pyvis(G, filename="runtime_graph.html", highlighted_edges=highlighted, edge_label_attr="avg_latency")
                except Exception:
                    pass


def create_app(analyzer: RuntimeAnalyzer):
    app = Flask(__name__)

    @app.route("/health")
    def health():
        return "ok"

    @app.route("/alerts")
    def alerts():
        with analyzer.lock:
            data = {"bottlenecks": analyzer.latest_bottlenecks, "windows": len(analyzer.latest_windows)}
        return jsonify(data)

    @app.route("/graph")
    def graph():
        # Serve the interactive live visualization page (default)
        # This page polls /graph-data or /graph-agg and renders using vis.js.
        try:
            return send_file('resources/graph_live.html')
        except Exception:
            # fallback to the pyvis-generated HTML if present
            path = "out/runtime_graph.html"
            try:
                return send_file(path)
            except Exception:
                return "graph not ready", 503

    @app.route('/pyvis')
    def pyvis_graph():
        path = "out/runtime_graph.html"
        try:
            return send_file(path)
        except Exception:
            return "pyvis graph not ready", 503

    @app.route("/graph-data")
    def graph_data():
        with analyzer.lock:
            gd = analyzer.latest_graph
        if not gd:
            return jsonify({"nodes": [], "edges": []}), 204
        return jsonify(gd)

    @app.route('/lib/<path:fname>')
    def lib_file(fname):
        # serve local lib files (e.g., vis-network JS/CSS)
        from pathlib import Path
        base = Path(__file__).resolve().parents[1] / 'lib'
        target = base / fname
        if not target.exists():
            return "not found", 404
        return send_file(str(target))
        @app.route('/graph-live')
        def graph_live():
                try:
                        return send_file('resources/graph_live.html')
                except Exception:
                        return "graph-live not ready", 503

    @app.route('/graph-agg')
    def graph_agg():
        # build aggregated graph from all records seen so far (useful to show full topology)
        try:
            from mbd.graph.graph_builder import GraphBuilder
        except Exception:
            return jsonify({"nodes": [], "edges": []}), 500

        with analyzer.lock:
            records_copy = list(analyzer.records)
        if not records_copy:
            return jsonify({"nodes": [], "edges": []}), 204

        G = GraphBuilder.build_graph(records_copy)
        nodes = []
        edges = []
        loads = [G.nodes[n].get("load", 0.0) for n in G.nodes]
        min_load = min(loads) if loads else 0.0
        max_load = max(loads) if loads else 0.0
        for n in G.nodes:
            load = G.nodes[n].get("load", 0.0)
            size = 10
            if max_load > min_load:
                frac = (load - min_load) / (max_load - min_load)
                size = 10 + frac * 50
            color = "#97c2fc"
            if max_load > 0 and max_load > min_load:
                intensity = int(255 * ((load - min_load) / (max_load - min_load)))
                r = min(255, 100 + intensity)
                g = max(50, 200 - intensity)
                b = max(50, 200 - intensity // 2)
                color = f"rgb({r},{g},{b})"
            title = f"{n}\nload={load:.3f}"
            nodes.append({"id": n, "label": n, "title": title, "size": size, "color": color})

        for u, v in G.edges:
            attrs = G[u][v]
            label = ""
            if "avg_latency" in attrs:
                label = f"{attrs['avg_latency']:.2f}"
            color = attrs.get("color", "black")
            width = float(attrs.get("penwidth", 1))
            edges.append({"from": u, "to": v, "label": label, "color": color, "width": width})

        return jsonify({"nodes": nodes, "edges": edges})

    return app


def main():
    parser = argparse.ArgumentParser(description="Runtime bottleneck detector (tail log & serve alerts)")
    parser.add_argument("--log", dest="log", default="resources/logs.csv", help="CSV log file to tail")
    parser.add_argument("--source", dest="source", required=True)
    parser.add_argument("--sink", dest="sink", required=True)
    parser.add_argument("--port", dest="port", type=int, default=8080)
    parser.add_argument("--window", dest="window", type=int, default=60)
    parser.add_argument("--step", dest="step", type=int, default=30)
    parser.add_argument("--capacity", dest="capacity", default="capacity")
    args = parser.parse_args()

    analyzer = RuntimeAnalyzer(args.log, args.source, args.sink, args.window, args.step, args.capacity)

    t_tail = threading.Thread(target=analyzer.tail_loop, name="tail-loop", daemon=True)
    t_analyze = threading.Thread(target=analyzer.analyze_loop, name="analyze-loop", daemon=True)
    t_tail.start()
    t_analyze.start()

    app = create_app(analyzer)
    app.run(host="0.0.0.0", port=args.port, debug=False)


if __name__ == "__main__":
    main()
