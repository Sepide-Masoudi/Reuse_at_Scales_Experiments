#!/usr/bin/env python3
"""
generate_chapter_figures.py

Generates the chapter figures from the experiment folders under paper_experiments/.
Run from paper_experiments/ with the venv active:

    source phd-plots/.venv/bin/activate
    python3 phd-plots/generate_chapter_figures.py

Figures are written to paper_experiments/phd-plots/figures/*.pdf

Energy method (same as compute_all_metrics.py):
  node energy = integral of kepler_node_cpu_power_sum (watts) over the window
  pod/service = last-first of the cumulative kepler_pod_cpu_power_joules_raw counter
No simulation figures are produced.
"""
import os, glob, json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib as mpl

ROOT = "."
FIGDIR = os.path.join("phd-plots", "figures")
os.makedirs(FIGDIR, exist_ok=True)

mpl.rcParams.update({
    "figure.figsize": (6.2, 4.0),
    "font.size": 11,
    "axes.grid": True,
    "grid.alpha": 0.3,
    "savefig.bbox": "tight",
    "savefig.dpi": 200,
})

SERVICE_UIDS = {
    "a35b873b-a47b-4833-983d-89866cf55b30",
    "d7f1ab00-0042-4627-803e-10346fc79c3b",
}

def _col(df, *names):
    for c in df.columns:
        if str(c).strip().lower() in names:
            return c
    return None

def _treatment_rows(df):
    tcol = _col(df, "treatment")
    if tcol is None:
        return df
    return df[df[tcol].astype(str).str.strip().str.lower() == "treatment"]

def node_energy_J(folder):
    f = os.path.join(folder, "data", "kepler_node_cpu_power_sum.csv")
    try:
        df = pd.read_csv(f)
    except Exception:
        return np.nan
    df = _treatment_rows(df)
    if df.empty:
        return np.nan
    ecol = _col(df, "epoch") or df.columns[1]
    vcol = _col(df, "value", "kepler_node_cpu_power_sum")
    if vcol is None:
        vcol = df.columns[2] if len(df.columns) > 2 else df.columns[-1]
    df = df[[ecol, vcol]].astype(float).sort_values(ecol)
    ep, w = df[ecol].values, df[vcol].values
    e = 0.0
    for i in range(1, len(ep)):
        dt = ep[i] - ep[i-1]
        if 0 < dt <= 60:
            e += 0.5 * (w[i] + w[i-1]) * dt
    return e

def pod_and_service_J(folder):
    f = os.path.join(folder, "data", "kepler_pod_cpu_power_joules_raw.csv")
    try:
        df = pd.read_csv(f)
    except Exception:
        return np.nan, np.nan
    df = _treatment_rows(df)
    if df.empty:
        return np.nan, np.nan
    pid = _col(df, "pod_id", "podid") or df.columns[0]
    val = _col(df, "kepler_pod_cpu_power_joules_raw", "value")
    if val is None:
        val = df.columns[3] if len(df.columns) > 3 else df.columns[-1]
    ep = _col(df, "epoch") or (df.columns[2] if len(df.columns) > 2 else df.columns[1])
    df = df[[pid, val, ep]].copy()
    df[val] = df[val].astype(float); df[ep] = df[ep].astype(float)
    total = service = 0.0
    for uid, sub in df.groupby(pid):
        sub = sub.sort_values(ep)
        d = sub[val].iloc[-1] - sub[val].iloc[0]
        if d < 0:
            d = sub[val].iloc[-1]
        total += d
        if uid in SERVICE_UIDS:
            service += d
    return total, service

def meta(folder):
    rj = os.path.join(folder, "run.json")
    if not os.path.isfile(rj):
        return {}
    with open(rj) as f:
        return json.load(f)

def find_one(pattern_dir, exp_substr):
    # (1) wrapped layout: <scale_dir>/nextflow_rnaseq_*/{data,run.json}
    for d in glob.glob(os.path.join(pattern_dir, "nextflow_rnaseq_*")):
        m = meta(d)
        if exp_substr in m.get("user_data", {}).get("experiment", ""):
            return d
    # (2) direct layout: <scale_dir>/{data,run.json} with no wrapper folder
    if os.path.isfile(os.path.join(pattern_dir, "run.json")) and \
       os.path.isdir(os.path.join(pattern_dir, "data")):
        m = meta(pattern_dir)
        if exp_substr in m.get("user_data", {}).get("experiment", ""):
            return pattern_dir
    # (3) fallback: any wrapped folder
    cands = glob.glob(os.path.join(pattern_dir, "nextflow_rnaseq_*"))
    if cands:
        return cands[0]
    # (4) fallback: the dir itself if it has data/
    if os.path.isdir(os.path.join(pattern_dir, "data")):
        return pattern_dir
    return None

def dur(folder):
    return meta(folder).get("treatment_duration", np.nan)

SCALES = [2, 4, 8, 16]
PCTS = [10, 20, 50]

def collect_scale(group, scale, exp_pat):
    d = find_one(f"{ROOT}/{group}/u{scale}", exp_pat)
    if not d:
        return None
    return {"folder": d, "node_J": node_energy_J(d), "dur_s": dur(d)}

baseline = {}
for s in [2, 4, 8, 16]:
    r = collect_scale("baseline", s, "baseline")
    if r: baseline[s] = r

podsvc = {}
for s in [2, 4, 8, 16]:
    r = collect_scale("pod_service", s, "pod-service")
    if r: podsvc[s] = r
for s in [32, 64]:
    d = find_one(f"{ROOT}/pod_service/u{s}_redo", "pod-service") or find_one(f"{ROOT}/pod_service/u{s}", "pod-service")
    if d:
        podsvc[s] = {"folder": d, "node_J": node_energy_J(d), "dur_s": dur(d)}

reuse = {s: {} for s in SCALES}
for s in SCALES:
    for p in PCTS:
        d = find_one(f"{ROOT}/data_reuse/u{s}", f"{p}pct")
        if d:
            reuse[s][p] = {"folder": d, "node_J": node_energy_J(d), "dur_s": dur(d)}

stress = {}
for d in glob.glob(f"{ROOT}/pipeline_under_stress/nextflow_rnaseq_*"):
    m = meta(d); exp = m.get("user_data", {}).get("experiment", "")
    if "stress-s" in exp:
        s = int(exp.split("stress-s")[1].split("-")[0])
        ne = node_energy_J(d); tot, svc = pod_and_service_J(d)
        stress[s] = {"node_J": ne, "dur_s": dur(d),
                     "service_pct": (svc/tot*100 if tot and tot==tot and tot>0 else np.nan)}

print("collected:",
      "baseline", sorted(baseline), "| podsvc", sorted(podsvc),
      "| reuse", {s: sorted(reuse[s]) for s in reuse},
      "| stress", sorted(stress))

kJ = lambda j: j/1000.0
h  = lambda s: s/3600.0
def cph(users, dur_s):
    return users/(dur_s/3600.0) if dur_s and dur_s==dur_s and dur_s>0 else np.nan

# =====================================================================
# FIG 1: pod-service energy vs sequential consumers (log-log + linear ref)
# =====================================================================
xs = [u for u in [2,4,8,16,32,64] if u in podsvc]
ys = [kJ(podsvc[u]["node_J"]) for u in xs]
fig, ax = plt.subplots()
ax.plot(xs, ys, "o-", label="measured")
y0, x0 = ys[0], xs[0]
ax.plot(xs, [y0*(u/x0) for u in xs], "k--", alpha=0.6, label="linear reference")
ax.set_xscale("log", base=2); ax.set_yscale("log", base=2)
ax.set_xticks(xs); ax.set_xticklabels(xs)
ax.set_xlabel("sequential consumers"); ax.set_ylabel("node energy (kJ)")
ax.legend()
fig.savefig(f"{FIGDIR}/fig_podservice_scaling.pdf"); plt.close(fig)

# =====================================================================
# FIG 2: baseline vs pod-service (energy + duration) at U8, U16
# =====================================================================
us = [u for u in [8,16] if u in baseline and u in podsvc]
x = np.arange(len(us)); w = 0.35
fig, (a1, a2) = plt.subplots(1, 2, figsize=(9, 4))
a1.bar(x-w/2, [kJ(baseline[u]["node_J"]) for u in us], w, label="baseline")
a1.bar(x+w/2, [kJ(podsvc[u]["node_J"]) for u in us], w, label="pod-service")
a1.set_xticks(x); a1.set_xticklabels([f"U{u}" for u in us])
a1.set_ylabel("node energy (kJ)"); a1.legend()
a2.bar(x-w/2, [h(baseline[u]["dur_s"]) for u in us], w, label="baseline")
a2.bar(x+w/2, [h(podsvc[u]["dur_s"]) for u in us], w, label="pod-service")
a2.set_xticks(x); a2.set_xticklabels([f"U{u}" for u in us])
a2.set_ylabel("duration (h)"); a2.legend()
fig.savefig(f"{FIGDIR}/fig_baseline_vs_podservice.pdf"); plt.close(fig)

# =====================================================================
# FIG 3: data-reuse energy vs reuse level, each scale
# =====================================================================
fig, ax = plt.subplots()
for s in SCALES:
    if all(p in reuse[s] for p in PCTS):
        ax.plot(PCTS, [kJ(reuse[s][p]["node_J"]) for p in PCTS], "o-", label=f"U{s}")
ax.set_xlabel("reuse level (\\%)"); ax.set_ylabel("node energy (kJ)")
ax.set_xticks(PCTS); ax.legend(title="scale")
fig.savefig(f"{FIGDIR}/fig_datareuse_energy_vs_pct.pdf"); plt.close(fig)

# =====================================================================
# FIG 4: data-reuse energy per consumer vs scale (baseline only where it exists)
# =====================================================================
fig, ax = plt.subplots()
for p in PCTS:
    xs2 = [s for s in SCALES if p in reuse[s]]
    ax.plot(xs2, [kJ(reuse[s][p]["node_J"])/s for s in xs2], "o-", label=f"{p}\\% reuse")
bxs = [u for u in [2,4,8,16] if u in baseline]
ax.plot(bxs, [kJ(baseline[u]["node_J"])/u for u in bxs], "ks--", label="baseline")
ax.set_xlabel("sequential consumers"); ax.set_ylabel("energy per consumer (kJ)")
ax.set_xscale("log", base=2); ax.set_xticks(SCALES); ax.set_xticklabels(SCALES)
ax.legend()
fig.savefig(f"{FIGDIR}/fig_datareuse_per_consumer.pdf"); plt.close(fig)

# =====================================================================
# FIG 5: pipeline-under-stress: service share + duration vs concurrent callers
# =====================================================================
ss = sorted(stress); totals = [s+1 for s in ss]
fig, ax1 = plt.subplots()
ax1.plot(totals, [stress[s]["service_pct"] for s in ss], "o-", color="#C44E52")
ax1.set_xlabel("concurrent callers")
ax1.set_ylabel("service-pod share of pod energy (\\%)", color="#C44E52")
ax1.tick_params(axis="y", labelcolor="#C44E52")
ax1.set_xscale("log", base=2); ax1.set_xticks(totals); ax1.set_xticklabels(totals)
ax2 = ax1.twinx(); ax2.grid(False)
ax2.plot(totals, [stress[s]["dur_s"] for s in ss], "s--", color="#4C72B0")
ax2.set_ylabel("pipeline duration (s)", color="#4C72B0")
ax2.tick_params(axis="y", labelcolor="#4C72B0")
fig.savefig(f"{FIGDIR}/fig_pipeline_under_stress.pdf"); plt.close(fig)

# =====================================================================
# FIG 6: three-way energy comparison (baseline, pod-svc, reuse 10/20/50)
# =====================================================================
us = [u for u in [2,4,8,16] if u in baseline]
x = np.arange(len(us)); w = 0.16
fig, ax = plt.subplots()
ax.bar(x-2*w, [kJ(baseline[u]["node_J"]) for u in us], w, label="baseline")
ax.bar(x-1*w, [kJ(podsvc[u]["node_J"]) for u in us], w, label="pod-service")
ax.bar(x+0*w, [kJ(reuse[u][10]["node_J"]) for u in us], w, label="reuse 10\\%")
ax.bar(x+1*w, [kJ(reuse[u][20]["node_J"]) for u in us], w, label="reuse 20\\%")
ax.bar(x+2*w, [kJ(reuse[u][50]["node_J"]) for u in us], w, label="reuse 50\\%")
ax.set_xticks(x); ax.set_xticklabels([f"U{u}" for u in us])
ax.set_ylabel("node energy (kJ)"); ax.legend(fontsize=8, ncol=2)
fig.savefig(f"{FIGDIR}/fig_threeway_comparison.pdf"); plt.close(fig)

# =====================================================================
# FIG 7: throughput (consumers/hour) three-way
# =====================================================================
us = [u for u in [2,4,8,16] if u in baseline]
x = np.arange(len(us)); w = 0.16
fig, ax = plt.subplots()
ax.bar(x-2*w, [cph(u, baseline[u]["dur_s"]) for u in us], w, label="baseline")
ax.bar(x-1*w, [cph(u, podsvc[u]["dur_s"]) for u in us], w, label="pod-service")
ax.bar(x+0*w, [cph(u, reuse[u][10]["dur_s"]) for u in us], w, label="reuse 10\\%")
ax.bar(x+1*w, [cph(u, reuse[u][20]["dur_s"]) for u in us], w, label="reuse 20\\%")
ax.bar(x+2*w, [cph(u, reuse[u][50]["dur_s"]) for u in us], w, label="reuse 50\\%")
ax.set_xticks(x); ax.set_xticklabels([f"U{u}" for u in us])
ax.set_ylabel("throughput (consumers / hour)"); ax.legend(fontsize=8, ncol=2)
fig.savefig(f"{FIGDIR}/fig_throughput_threeway.pdf"); plt.close(fig)

# =====================================================================
# FIG 8: data-reuse throughput (consumers/hour) vs reuse level, each scale
# =====================================================================
fig, ax = plt.subplots()
for s in SCALES:
    if all(p in reuse[s] for p in PCTS):
        ax.plot(PCTS, [cph(s, reuse[s][p]["dur_s"]) for p in PCTS], "o-", label=f"U{s}")
for u in [2,4,8,16]:
    if u in baseline:
        ax.axhline(cph(u, baseline[u]["dur_s"]), ls=":", alpha=0.4)
ax.set_xlabel("reuse level (\\%)"); ax.set_ylabel("throughput (consumers / hour)")
ax.set_xticks(PCTS); ax.legend(title="scale")
fig.savefig(f"{FIGDIR}/fig_throughput_datareuse.pdf"); plt.close(fig)

print(f"\nFigures written to {FIGDIR}/")
for f in sorted(glob.glob(f"{FIGDIR}/*.pdf")):
    print("  ", f)
