"""Generate synthetic microservice call logs with scenarios:
- baseline: steady traffic
- spike: short high-rate period on chosen edge(s)
- degradation: gradual latency increase on chosen edge(s)

Output CSV format compatible with existing parser: timestamp,src,src_ep,dst,dst_ep,latency

Usage example:
python3 scripts/generate_scenarios.py --out resources/logs_large.csv --events 20000 --seed 42
"""
from __future__ import annotations

import argparse
import csv
import random
from datetime import datetime, timedelta

# reuse DEFAULT_EDGES from generate_mocks but replicate here to avoid imports
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


def generate_scenario(out_path: str, events: int = 20000, window_seconds: int = 3600, seed: int | None = None):
    rng = random.Random(seed)
    start = datetime.utcnow()
    rows = []

    # define phases within the window (fractions)
    baseline_frac = 0.7
    spike_frac = 0.15
    degr_frac = 0.15

    baseline_events = int(events * baseline_frac)
    spike_events = int(events * spike_frac)
    degr_events = events - baseline_events - spike_events

    # choose edge(s) for spike and degradation by finding matching entries in DEFAULT_EDGES
    def find_edge(src_name, dst_name):
        for e in DEFAULT_EDGES:
            if e[0] == src_name and e[2] == dst_name:
                return e
        return None

    spike_edge = find_edge("media-service", "storage-service")
    degr_edge = find_edge("user-service", "db-user")
    if spike_edge is None or degr_edge is None:
        raise RuntimeError("Could not find spike/degradation edge definitions in DEFAULT_EDGES")

    # Baseline: uniform random across DEFAULT_EDGES
    for _ in range(baseline_events):
        offset = rng.uniform(0, window_seconds)
        ts = start + timedelta(seconds=offset * 0.5)  # place baseline in first half
        edge = rng.choice(DEFAULT_EDGES)
        src, src_ep, dst, dst_ep, min_lat, max_lat = edge
        latency = rng.uniform(min_lat, max_lat)
        rows.append((iso_z(ts), src, src_ep, dst, dst_ep, f"{latency:.1f}"))

    # Spike: concentrated in a short time towards middle
    spike_window = 30  # seconds
    spike_center = start + timedelta(seconds=window_seconds * 0.5)
    for _ in range(spike_events):
        # cluster times around spike_center
        offset = rng.gauss(0, spike_window / 4)
        ts = spike_center + timedelta(seconds=offset)
        src, src_ep, dst, dst_ep, min_lat, max_lat = spike_edge
        # increase latency and frequency during spike
        latency = rng.uniform(max_lat * 1.2, max_lat * 2.0)
        rows.append((iso_z(ts), src, src_ep, dst, dst_ep, f"{latency:.1f}"))

    # Degradation: gradually increasing latency over last part
    degr_start = start + timedelta(seconds=window_seconds * 0.7)
    degr_end = start + timedelta(seconds=window_seconds)
    for i in range(degr_events):
        frac = i / max(1, degr_events - 1)
        ts = degr_start + (degr_end - degr_start) * frac
        src, src_ep, dst, dst_ep, min_lat, max_lat = degr_edge
        # latency increases linearly from max_lat to 3*max_lat
        latency = rng.uniform(max_lat * (1 + frac), max_lat * (1 + 2 * frac))
        rows.append((iso_z(ts), src, src_ep, dst, dst_ep, f"{latency:.1f}"))

    # Shuffle and sort to simulate real logs (but keep natural time order)
    rows.sort(key=lambda r: r[0])

    with open(out_path, "w", newline="") as f:
        w = csv.writer(f)
        for r in rows:
            w.writerow(r)

    print(f"Wrote {len(rows)} events to {out_path}")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--out", type=str, default="resources/logs_large.csv")
    p.add_argument("--events", type=int, default=20000)
    p.add_argument("--window", type=int, default=3600, help="window length in seconds")
    p.add_argument("--seed", type=int, default=42)
    args = p.parse_args()

    generate_scenario(args.out, args.events, args.window, args.seed)
