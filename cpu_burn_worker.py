#!/usr/bin/env python3
"""
cpu_burn_worker.py
Replays a trace-derived CPU profile: for each task [realtime_sec, cores], spawn
`round(cores)` busy PROCESSES (not threads — Python's GIL means threads share one
core; multiprocessing genuinely occupies multiple cores) spinning for realtime_sec.
Models one synthetic "user" reproducing the real CPU demand of a (baseline or reuse)
pipeline run.

Tasks replayed SEQUENTIALLY (single pipeline's task stream). Concurrency across
users = running N of these pods at once.

Usage (inside pod):
  python3 cpu_burn_worker.py /profiles/<profile>.json
"""
import sys, os, json, time, math
from multiprocessing import Process

def burn(duration):
    end = time.time() + duration
    x = 0.0
    while time.time() < end:
        for _ in range(50000):
            x += 1.0001
            x *= 0.9999
    return x

def run_task(realtime, cores):
    """Occupy `cores` cores for `realtime` seconds using separate processes."""
    whole = int(math.floor(cores))
    frac = cores - whole
    procs = []
    for _ in range(whole):
        p = Process(target=burn, args=(realtime,))
        p.start(); procs.append(p)
    if frac > 0.01:
        p = Process(target=burn, args=(realtime * frac,))
        p.start(); procs.append(p)
    if whole == 0 and frac <= 0.01:
        time.sleep(realtime)
    # the main process waits the full realtime regardless (sequential task model)
    deadline = time.time() + realtime
    for p in procs:
        remaining = max(0, deadline - time.time())
        p.join(timeout=remaining + 1)
        if p.is_alive():
            p.terminate()

def main():
    path = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("PROFILE")
    with open(path) as f:
        prof = json.load(f)
    tasks = prof["tasks"]
    label = prof.get("label", "profile")
    t0 = time.time()
    print(f"[worker] start label={label} tasks={len(tasks)} "
          f"core_seconds={prof.get('total_core_seconds')} cpus={os.cpu_count()}", flush=True)
    for rt, cores in tasks:
        run_task(rt, cores)
    print(f"[worker] done label={label} wall={time.time()-t0:.1f}s", flush=True)

if __name__ == "__main__":
    main()