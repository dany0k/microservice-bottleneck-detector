"""Run bottleneck analysis over a CSV log and save results.

Usage:
python3 scripts/run_bottleneck_analysis.py --in resources/logs_large.csv --source api-gateway --sink db-user --window 60 --step 30 --out out/analysis.json
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from mbd.parser import LogParser
from mbd.graph import analyze_time_windows, aggregate_bottlenecks


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--in", dest="infile", required=True)
    p.add_argument("--source", required=True)
    p.add_argument("--sink", required=True)
    p.add_argument("--window", type=int, default=60)
    p.add_argument("--step", type=int, default=30)
    p.add_argument("--capacity", dest="capacity_attr", default="capacity")
    p.add_argument("--out", dest="outfile", default="out/analysis.json")
    p.add_argument("--viz", dest="vizfile", default=None, help="generate interactive HTML visualization")
    args = p.parse_args()

    infile = Path(args.infile)
    outfile = Path(args.outfile)
    outfile.parent.mkdir(parents=True, exist_ok=True)

    print(f"Parsing logs from {infile}")
    records = LogParser.parse_csv(str(infile))
    print(f"Parsed {len(records)} records")

    print(f"Running sliding-window analysis: window={args.window}s step={args.step}s capacity={args.capacity_attr}")
    results = analyze_time_windows(records, source=args.source, sink=args.sink, window_seconds=args.window, step_seconds=args.step, capacity_attr=args.capacity_attr)

    agg = aggregate_bottlenecks(results, top_k=20)

    out_obj: dict[str, Any] = {
        "input": str(infile),
        "source": args.source,
        "sink": args.sink,
        "window": args.window,
        "step": args.step,
        "capacity_attr": args.capacity_attr,
        "windows": [] ,
        "aggregated_bottlenecks": [ {"edge": [e[0], e[1]], "count": c} for e,c in agg ]
    }

    for w in results:
        out_obj["windows"].append({
            "start": w["start"].isoformat(),
            "end": w["end"].isoformat(),
            "flow": w.get("flow", 0.0),
            "cut_value": w.get("cut_value", 0.0),
            "min_cut": [[u, v] for (u, v) in w.get("min_cut", [])]
        })

    with open(outfile, "w") as f:
        json.dump(out_obj, f, indent=2, ensure_ascii=False)

    print(f"Saved analysis to {outfile}")
    print("Top bottleneck edges:")
    for e, c in agg:
        print(f"{e} : {c}")

    # optional visualization
    if args.vizfile:
        from mbd.graph import GraphBuilder, GraphVisualizer

        print(f"Building full graph for viz and highlighting top aggregated edges")
        G_full = GraphBuilder.build_graph(records)
        viz_out_dir = Path(args.vizfile).parent
        viz = GraphVisualizer(output_dir=str(viz_out_dir) if viz_out_dir != Path('.') else "out")
        top_edges = [tuple(e["edge"]) for e in out_obj["aggregated_bottlenecks"]]
        viz.render_pyvis(G_full, filename=Path(args.vizfile).name, highlighted_edges=top_edges)


if __name__ == '__main__':
    main()
