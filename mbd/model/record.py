from dataclasses import dataclass

@dataclass
class LogRecord:
    timestamp: str
    src_service: str
    src_endpoint: str
    dst_service: str
    dst_endpoint: str
    latency: float
