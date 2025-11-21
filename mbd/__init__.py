"""microservice-bottleneck-detector package (mbd)

Public API is organized into subpackages:
- mbd.parser
- mbd.model
- mbd.graph
- mbd.utils

Use `from mbd.parser import LogParser` and `from mbd.graph import GraphBuilder` etc.
"""

__all__ = ["parser", "model", "graph", "utils"]
"""Top-level package for the microservice bottleneck detector.

This package re-exports the actual implementation located in `src/`.
It provides a stable import path `mbd.*` while we incrementally refactor
the codebase into a proper package layout.
"""
from .parser import LogParser
from .model import LogRecord
from .graph import GraphBuilder, GraphAnalyzer, GraphVisualizer, analyze_time_windows, aggregate_bottlenecks

__all__ = [
    "LogParser",
    "LogRecord",
    "GraphBuilder",
    "GraphAnalyzer",
    "GraphVisualizer",
    "analyze_time_windows",
    "aggregate_bottlenecks",
]
