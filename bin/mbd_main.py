from mbd.graph import GraphAnalyzer, GraphBuilder, GraphVisualizer
from mbd.parser import LogParser

LOG_PATH = "../resources/logs.csv"


def main():
    records = LogParser.parse_csv(LOG_PATH)
    G = GraphBuilder.build_graph(records)

    GraphAnalyzer.print_stats(G)

    # choose capacity metric: "capacity" (default), or "capacity_throughput", or "capacity_latency"
    capacity_attr = "capacity"  # change to "capacity_throughput" to prefer throughput explicitly

    source = "api-gateway"
    sink = "db-user"

    flow_value, flow_dict = GraphAnalyzer.max_flow(G, source, sink, capacity_attr)
    print(f"Max flow ({capacity_attr}) from {source} to {sink}: {flow_value}")

    cut_value, (S, T) = GraphAnalyzer.min_cut(G, source, sink, capacity_attr)
    print(f"Min cut value ({capacity_attr}) between {source} and {sink}: {cut_value}")

    bottlenecks = []
    for u in S:
        for v in G.successors(u):
            if v in T:
                bottlenecks.append((u, v))

    viz = GraphVisualizer(output_dir="out")
    viz.render_service_graph(G, filename="service_graph.png", bottlenecks=bottlenecks)


if __name__ == "__main__":
    main()
