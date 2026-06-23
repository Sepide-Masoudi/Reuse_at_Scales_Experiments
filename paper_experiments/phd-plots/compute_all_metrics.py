#!/usr/bin/env python3
"""
compute_all_metrics.py  (v2 — correct energy computation)

Energy is computed correctly and consistently across live + recovered runs:
  - NODE energy: integrate kepler_node_cpu_power_sum (instantaneous WATTS) over the
    treatment window -> joules. Handles live schema (has 'treatment' col, watts in
    'kepler_node_cpu_power_sum') and recovered schema (cols: timestamp,epoch,value).
    Live files contain idle NoTreatment rows + gaps, so we filter to Treatment rows;
    recovered files are already the run window.
  - PER-POD / SERVICE energy: kepler_pod_cpu_power_joules_raw is a CUMULATIVE COUNTER,
    so per-pod energy = last - first over the window (NOT sum). Total pod energy =
    sum of per-pod deltas. Service energy = delta for the two known service UIDs.

Run from: paper_experiments/
  python3 phd-plots/compute_all_metrics.py
"""
import os, glob, json
import pandas as pd

ROOT = "."
SERVICE_UIDS = {
    "a35b873b-a47b-4833-983d-89866cf55b30": "featurecounts",
    "d7f1ab00-0042-4627-803e-10346fc79c3b": "stringtie",
}

def _col(df, *names):
    for c in df.columns:
        if str(c).strip().lower() in names:
            return c
    return None

def _treatment_rows(df):
    tcol = _col(df, "treatment")
    if tcol is None:
        return df  # recovered file: already the window
    return df[df[tcol].astype(str).str.strip().str.lower() == "treatment"]

def node_energy_J(folder):
    """Integrate node power (watts) over the treatment window -> joules."""
    f = os.path.join(folder, "data", "kepler_node_cpu_power_sum.csv")
    try:
        df = pd.read_csv(f)
    except Exception:
        return float("nan")
    df = _treatment_rows(df)
    if df.empty:
        return float("nan")
    ecol = _col(df, "epoch") or df.columns[1]
    vcol = _col(df, "value", "kepler_node_cpu_power_sum")
    if vcol is None:
        vcol = df.columns[2] if len(df.columns) > 2 else df.columns[-1]
    df = df[[ecol, vcol]].astype(float).sort_values(ecol)
    ep = df[ecol].values
    w = df[vcol].values
    e = 0.0
    for i in range(1, len(ep)):
        dt = ep[i] - ep[i-1]
        # guard against idle gaps: skip intervals > 60s (not contiguous sampling)
        if 0 < dt <= 60:
            e += 0.5 * (w[i] + w[i-1]) * dt
    return e

def _pod_counter_df(folder):
    f = os.path.join(folder, "data", "kepler_pod_cpu_power_joules_raw.csv")
    try:
        df = pd.read_csv(f)
    except Exception:
        return None
    df = _treatment_rows(df)
    return df if not df.empty else None

def _pod_cols(df):
    pid = _col(df, "pod_id", "podid") or df.columns[0]
    val = _col(df, "kepler_pod_cpu_power_joules_raw", "value")
    if val is None:
        val = df.columns[3] if len(df.columns) > 3 else df.columns[-1]
    ep = _col(df, "epoch") or (df.columns[2] if len(df.columns) > 2 else df.columns[1])
    return pid, val, ep

def pod_energy_delta(folder):
    """Total pod energy = sum over pods of (last-first) cumulative joules.
    Returns (total_J, service_J)."""
    df = _pod_counter_df(folder)
    if df is None:
        return float("nan"), float("nan")
    pid, val, ep = _pod_cols(df)
    try:
        df = df[[pid, val, ep]].copy()
        df[val] = df[val].astype(float)
        df[ep] = df[ep].astype(float)
    except Exception:
        return float("nan"), float("nan")
    total = 0.0
    service = 0.0
    for uid, sub in df.groupby(pid):
        sub = sub.sort_values(ep)
        delta = sub[val].iloc[-1] - sub[val].iloc[0]
        if delta < 0:  # counter reset -> skip (rare)
            delta = sub[val].iloc[-1]
        total += delta
        if uid in SERVICE_UIDS:
            service += delta
    return total, service

def run_meta(folder):
    rj = os.path.join(folder, "run.json")
    if not os.path.isfile(rj):
        return None
    with open(rj) as f:
        return json.load(f)

def collect(label, folder, rows):
    try:
        m = run_meta(folder)
        if not m:
            return
        exp = m.get("user_data", {}).get("experiment", "?")
        dur = m.get("treatment_duration", float("nan"))
        ne = node_energy_J(folder)
        pe, se = pod_energy_delta(folder)
        rows.append({
            "group": label,
            "experiment": exp,
            "duration_s": round(dur, 1) if dur == dur else "",
            "node_energy_J": round(ne, 1) if ne == ne else "",
            "pod_energy_J": round(pe, 1) if pe == pe else "",
            "service_energy_J": round(se, 1) if se == se else "",
            "service_pct": round(se/pe*100, 1) if (pe and pe == pe and se == se and pe > 0) else "",
        })
    except Exception as e:
        rows.append({"group": label, "experiment": f"ERROR:{os.path.basename(folder)}:{e}",
                     "duration_s": "", "node_energy_J": "", "pod_energy_J": "",
                     "service_energy_J": "", "service_pct": ""})

def main():
    rows = []
    for scale_dir in sorted(glob.glob(f"{ROOT}/baseline/u*")):
        for d in glob.glob(f"{scale_dir}/nextflow_rnaseq_*"):
            collect(f"baseline/{os.path.basename(scale_dir)}", d, rows)
    for scale_dir in sorted(glob.glob(f"{ROOT}/data_reuse/u*")):
        for d in glob.glob(f"{scale_dir}/nextflow_rnaseq_*"):
            collect(f"data_reuse/{os.path.basename(scale_dir)}", d, rows)
    for scale_dir in sorted(glob.glob(f"{ROOT}/pod_service/u*")):
        for d in glob.glob(f"{scale_dir}/nextflow_rnaseq_*"):
            collect(f"pod_service/{os.path.basename(scale_dir)}", d, rows)
    for d in glob.glob(f"{ROOT}/pipeline_under_stress/nextflow_rnaseq_*"):
        collect("pipeline_under_stress", d, rows)
    for d in glob.glob(f"{ROOT}/concurrent_reuse_sim/nextflow_rnaseq_*"):
        collect("concurrent_reuse_sim", d, rows)

    df = pd.DataFrame(rows)
    # dedupe identical rows (same folder copied/listed twice)
    df = df.drop_duplicates(subset=["group", "experiment", "duration_s", "node_energy_J"])
    df = df.sort_values(["group", "experiment"])
    df.to_csv("chapter_metrics.csv", index=False)
    print("=" * 95)
    print("CHAPTER METRICS  (corrected energy)  — also saved to chapter_metrics.csv")
    print("=" * 95)
    with pd.option_context('display.max_rows', None, 'display.width', 220):
        print(df.to_string(index=False))

if __name__ == "__main__":
    main()