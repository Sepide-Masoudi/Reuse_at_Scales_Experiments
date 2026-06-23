#!/usr/bin/env python3
"""
recover_u64_metrics.py  (v2 - POST form-encoded, matches working curl behavior)

Rebuild SMA metric CSVs for a run whose end-of-run fetch failed with HTTP 400
(query_range 11k-point limit). Raw data is still in Prometheus. Re-queries each
metric in time-chunks under the 11k limit and writes one CSV per metric.

Key fix vs v1: uses POST with form-encoded body (like curl --data-urlencode),
which reliably handles the multi-line PromQL in the SMA config. v1 used GET with
urlencode and silently returned empty series for the multi-line queries.

Usage:
  python3 recover_u64_metrics.py <RUN_FOLDER> [STEP_SECONDS] [CHUNK_HOURS] [ONLY_METRIC]
"""

import sys, os, json, csv, time
import datetime as dt
from urllib.parse import urlencode
from urllib.request import urlopen, Request
from urllib.error import HTTPError
import yaml

PROM = "http://178.105.129.44:30090"
CONFIG_PATH = "/mnt/nextflow-data/nextflow-sma-measurments.yaml"


def parse_ts(s: str) -> float:
    d = dt.datetime.strptime(s, "%Y_%m_%d_%H_%M_%S")
    return d.replace(tzinfo=dt.timezone.utc).timestamp()


def load_metrics(config_path):
    with open(config_path) as f:
        cfg = yaml.safe_load(f)
    out = []
    for m in cfg["sma"]["measurements"]:
        for name, spec in m.items():
            q = spec.get("query", "")
            if q and q.strip():
                # SMA substitutes template vars at runtime; replicate that here.
                q = q.replace("${namespace}", "nextflow")
                out.append((name, q))
    return out


def prom_query_range(promql, start, end, step):
    """POST form-encoded query_range (handles multi-line PromQL reliably)."""
    body = urlencode({
        "query": promql,
        "start": f"{start:.3f}",
        "end": f"{end:.3f}",
        "step": str(step),
    }).encode()
    req = Request(f"{PROM}/api/v1/query_range", data=body,
                  headers={"Content-Type": "application/x-www-form-urlencoded"})
    with urlopen(req, timeout=180) as r:
        return json.loads(r.read().decode())


def query_chunked(promql, start, end, step, chunk_seconds):
    merged = {}
    t = start
    while t < end:
        c_end = min(t + chunk_seconds, end)
        for attempt in range(3):
            try:
                data = prom_query_range(promql, t, c_end, step)
                break
            except HTTPError as e:
                if attempt == 2:
                    raise RuntimeError(f"HTTP {e.code}: {e.read()[:200]}")
                time.sleep(2)
            except Exception:
                if attempt == 2:
                    raise
                time.sleep(2)
        if data.get("status") != "success":
            raise RuntimeError(f"query failed: {data.get('error','?')}")
        for s in data["data"]["result"]:
            key = frozenset(s["metric"].items())
            if key not in merged:
                merged[key] = {"metric": s["metric"], "values": []}
            merged[key]["values"].extend(s["values"])
        t = c_end
    return list(merged.values())


def write_csv(path, name, series_list):
    label_keys, seen = [], set()
    for s in series_list:
        for k in s["metric"]:
            if k not in seen:
                seen.add(k); label_keys.append(k)
    header = label_keys + ["timestamp", "epoch", "value"]
    rows = 0
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(header)
        for s in series_list:
            base = [s["metric"].get(k, "") for k in label_keys]
            for ts, val in s["values"]:
                iso = dt.datetime.fromtimestamp(float(ts), dt.timezone.utc).isoformat()
                w.writerow(base + [iso, ts, val]); rows += 1
    return rows


def main():
    if len(sys.argv) < 2:
        print(__doc__); sys.exit(1)
    run_folder = sys.argv[1].rstrip("/")
    step = int(sys.argv[2]) if len(sys.argv) > 2 else 10
    chunk_hours = float(sys.argv[3]) if len(sys.argv) > 3 else 6.0
    only = sys.argv[4] if len(sys.argv) > 4 else None
    chunk_seconds = int(chunk_hours * 3600)

    pts = chunk_seconds / step
    print(f"chunk={chunk_hours}h step={step}s -> {pts:.0f} pts/chunk (<11000 required)")
    assert pts < 11000

    with open(os.path.join(run_folder, "run.json")) as f:
        rj = json.load(f)
    start = parse_ts(rj["treatment_start"]) - 90
    end = parse_ts(rj["treatment_end"]) + 90
    print(f"window {rj['treatment_start']} -> {rj['treatment_end']} ({(end-start)/3600:.1f}h)")

    out_dir = os.path.join(run_folder, "data")
    os.makedirs(out_dir, exist_ok=True)

    metrics = load_metrics(CONFIG_PATH)
    if only:
        metrics = [(n, q) for n, q in metrics if n == only]
    print(f"recovering {len(metrics)} metric(s)\n")

    ok, failed = 0, []
    for name, promql in metrics:
        try:
            series = query_chunked(promql, start, end, step, chunk_seconds)
            if not series:
                print(f"  [empty] {name}"); failed.append(name); continue
            rows = write_csv(os.path.join(out_dir, f"{name}.csv"), name, series)
            print(f"  [ok]    {name}: {len(series)} series, {rows} rows"); ok += 1
        except Exception as e:
            print(f"  [FAIL]  {name}: {e}"); failed.append(name)

    print(f"\n{ok}/{len(metrics)} recovered.")
    if failed:
        print("missing:", ", ".join(failed))


if __name__ == "__main__":
    main()