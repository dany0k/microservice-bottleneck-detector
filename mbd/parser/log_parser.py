import csv
from typing import List

from mbd.model.record import LogRecord


class LogParser:

    @staticmethod
    def parse_csv(filepath: str) -> List[LogRecord]:
        records = []

        with open(filepath, "r") as f:
            reader = csv.reader(f)
            for row in reader:
                if not row or row[0].startswith("#"):
                    continue

                timestamp, src, src_ep, dst, dst_ep, latency = row
                records.append(
                    LogRecord(
                        timestamp=timestamp,
                        src_service=src,
                        src_endpoint=src_ep,
                        dst_service=dst,
                        dst_endpoint=dst_ep,
                        latency=float(latency),
                    )
                )
        return records
