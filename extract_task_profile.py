#!/usr/bin/env python3
"""
extract_task_profile.py
Reads a Nextflow trace.txt and emits a compact CPU-burn profile: a JSON list of
[realtime_sec, cores] for every COMPLETED task (CACHED tasks are skipped, since a
cached task costs ~nothing — that skip IS the reuse saving).

cores = %cpu / 100  (observed effective cores: 99% -> 0.99, 185% -> 1.85)

Trace columns (1-indexed): 4=name 5=status 9=realtime 10=%cpu

Usage:
  python3 extract_task_profile.py <trace.txt> <out.json> [<label>]
"""
import sys, json, re

def tosec(t):
    t = t.strip()
    if not t or t == "-":
        return 0.0
    s = 0.0
    m = re.match(r'(?:(\d+)h)?\s*(?:(\d+)m(?!s))?\s*(?:([\d.]+)s)?$', t)
    # handle ms separately
    if t.endswith("ms"):
        return float(t[:-2]) / 1000.0
    if m and any(m.groups()):
        h, mi, se = m.groups()
        if h:  s += float(h) * 3600
        if mi: s += float(mi) * 60
        if se: s += float(se)
        return s
    # bare number fallback
    try:
        return float(re.sub(r'[^\d.]', '', t))
    except Exception:
        return 0.0

def main():
    trace, out = sys.argv[1], sys.argv[2]
    label = sys.argv[3] if len(sys.argv) > 3 else "profile"
    tasks = []
    completed = cached = 0
    total_coresec = 0.0
    with open(trace) as f:
        header = f.readline()
        for line in f:
            c = line.rstrip("\n").split("\t")
            if len(c) < 10:
                continue
            status = c[4]
            if status == "CACHED":
                cached += 1
                continue
            completed += 1
            rt = tosec(c[8])           # realtime
            cpu = c[9].replace("%", "").strip()
            try:
                cores = float(cpu) / 100.0
            except Exception:
                cores = 0.0
            # clamp tiny/zero tasks to a minimal burn so they still take time
            if rt <= 0:
                rt = 0.05
            cores = max(cores, 0.01)
            tasks.append([round(rt, 3), round(cores, 3)])
            total_coresec += rt * cores
    with open(out, "w") as f:
        json.dump({"label": label, "tasks": tasks,
                   "completed": completed, "cached": cached,
                   "total_core_seconds": round(total_coresec, 1)}, f)
    print(f"{label}: completed={completed} cached={cached} "
          f"core-seconds={total_coresec:.1f} -> {out}")

if __name__ == "__main__":
    main()