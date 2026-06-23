#!/usr/bin/env python3
"""
analyze_per_user_energy.py
Reads pod-service kepler_node_cpu_power_sum.csv at each scale, integrates
cluster power (watts) over time to get total energy (Joules), and divides by
user count. Prints a table so you can see if per-user energy is flat (scaling
adds no insight) or trends (scaling is a real result).

Run on your Mac:
  python3 analyze_per_user_energy.py
"""
import csv, glob, os

BASE = "/Users/sepideh.masoudi/Desktop/paper_experiments/pod_service"

SCALES = [
    (8,  "u8"),
    (16, "u16"),
    (32, "u32_redo"),
    (64, "u64_redo"),
]

def find_csv(folder):
    pat = os.path.join(BASE, folder, "nextflow_rnaseq_*", "data", "kepler_node_cpu_power_sum.csv")
    hits = glob.glob(pat)
    return hits[0] if hits else None

def read_series(path):
    """Return list of (epoch_seconds, watts), handling both CSV formats."""
    pts = []
    with open(path) as f:
        r = csv.reader(f)
        header = next(r)
        # find epoch col + value col
        # format A (SMA): timestamp, epoch, <metricname>, layer, unit, treatment  -> epoch idx1, value idx2
        # format B (recovery): timestamp, epoch, value                            -> epoch idx1, value idx2
        # In both, epoch is col 1 and the numeric value is col 2.
        epoch_i, val_i = 1, 2
        for row in r:
            if len(row) <= val_i:
                continue
            try:
                e = float(row[epoch_i]); v = float(row[val_i])
            except ValueError:
                continue
            pts.append((e, v))
    pts.sort()
    return pts

def integrate(pts):
    """Trapezoidal integration of watts over seconds -> Joules. Also return duration."""
    if len(pts) < 2:
        return 0.0, 0.0
    energy = 0.0
    for (t0, w0), (t1, w1) in zip(pts, pts[1:]):
        dt = t1 - t0
        if dt <= 0 or dt > 120:   # skip gaps > 2min (avoids cross-gap artifacts)
            continue
        energy += 0.5 * (w0 + w1) * dt
    dur = pts[-1][0] - pts[0][0]
    return energy, dur

print(f"{'scale':>5} {'rows':>6} {'dur_h':>7} {'total_kJ':>10} {'per_user_kJ':>12} {'avg_W':>7}")
print("-" * 56)
results = []
for n, folder in SCALES:
    path = find_csv(folder)
    if not path:
        print(f"{n:>5}  (no CSV found in {folder})")
        continue
    pts = read_series(path)
    energy_j, dur_s = integrate(pts)
    per_user_j = energy_j / n
    avg_w = (energy_j / dur_s) if dur_s else 0
    print(f"{n:>5} {len(pts):>6} {dur_s/3600:>7.2f} {energy_j/1000:>10.1f} {per_user_j/1000:>12.2f} {avg_w:>7.2f}")
    results.append((n, per_user_j/1000))

print()
if len(results) >= 2:
    vals = [v for _, v in results]
    lo, hi = min(vals), max(vals)
    spread = (hi - lo) / (sum(vals)/len(vals)) * 100
    print(f"per-user energy range: {lo:.2f} – {hi:.2f} kJ  (spread {spread:.1f}% of mean)")
    if spread < 10:
        print("=> FLAT: per-user energy ~constant across scale. Scaling adds little insight;")
        print("   a small N (e.g. 8) is scientifically sufficient.")
    else:
        print("=> TRENDING: per-user energy changes with scale. The scaling curve IS a result;")
        print("   the full range is justified.")