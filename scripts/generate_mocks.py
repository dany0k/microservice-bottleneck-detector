"""Generate synthetic microservice call logs in CSV format.

Rows: timestamp, src_service, src_endpoint, dst_service, dst_endpoint, latency(ms)

Usage: python scripts/generate_mocks.py --out resources/logs_mock.csv --events 200
"""
from __future__ import annotations

import argparse
import csv
import random
from datetime import datetime, timedelta

DEFAULT_EDGES = [
    ("api-gateway", "/home", "user-service", "/getUser", 10, 30),
    ("user-service", "/getUser", "auth-service", "/verify", 5, 15),
    ("auth-service", "/verify", "cache-service", "/checkToken", 1, 5),
    ("api-gateway", "/home", "post-service", "/getUserPosts", 15, 30),
    ("post-service", "/getUserPosts", "user-service", "/getUser", 10, 40),
    ("user-service", "/getUser", "db-user", "/queryUser", 20, 60),
    ("post-service", "/composePost", "media-service", "/upload", 40, 120),
    ("media-service", "/upload", "storage-service", "/putObject", 80, 200),
    ("media-service", "/getMedia", "storage-service", "/getObject", 50, 120),
    ("timeline-service", "/getTimeline", "post-service", "/getUserPosts", 15, 40),
]


def iso_z(ts: datetime) -> str:
    return ts.isoformat(timespec="seconds") + "Z"


def generate_events(out_path: str, events: int = 200, window_seconds: int = 300, seed: int | None = None):
    rng = random.Random(seed)

    start = datetime.utcnow()
    rows = []

    for i in range(events):
        # pick random offset in window
        offset = rng.uniform(0, window_seconds)
        ts = start + timedelta(seconds=offset)

        # pick an edge weighted randomly
        edge = rng.choice(DEFAULT_EDGES)
        src, src_ep, dst, dst_ep, min_lat, max_lat = edge
        latency = rng.uniform(min_lat, max_lat)

        rows.append((iso_z(ts), src, src_ep, dst, dst_ep, f"{latency:.1f}"))

    # sort by timestamp to mimic real logs
    rows.sort(key=lambda r: r[0])

    with open(out_path, "w", newline="") as f:
        w = csv.writer(f)
        for r in rows:
            w.writerow(r)

    print(f"Wrote {len(rows)} events to {out_path}")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--out", type=str, default="resources/logs_mock.csv")
    p.add_argument("--events", type=int, default=200)
    p.add_argument("--window", type=int, default=300, help="window length in seconds")
    p.add_argument("--seed", type=int, default=None)
    args = p.parse_args()

    generate_events(args.out, args.events, args.window, args.seed)
