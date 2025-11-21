from mbd.graph.dependency_graph import DependencyGraph
from mbd.graph.visualizer import GraphVisualizer

example_logs = [
    "Auth → UserService : 12ms",
    "UserService → PostService : 30ms",
    "PostService → MediaService : 80ms",
    "Auth → Notification : 18ms",
]

dg = DependencyGraph()
dg.load_from_log_lines(example_logs)

visualizer = GraphVisualizer()
visualizer.render_service_graph(dg.graph)