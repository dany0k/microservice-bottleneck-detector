import networkx as nx


class DependencyGraph:
    def __init__(self):
        self.graph = nx.DiGraph()

    def load_from_log_lines(self, lines):
        for line in lines:
            try:
                left, right = line.split("→")
                source = left.strip()

                target_part = right.split(":")[0]
                latency_str = right.split(":")[1]

                target = target_part.strip()
                latency = int(latency_str.replace("ms", "").strip())

                self.graph.add_edge(source, target, latency=latency)
            except Exception as e:
                print(f"Ошибка парсинга строки '{line}': {e}")

    def get_graph(self):
        return self.graph
