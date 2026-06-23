#!/usr/bin/env python3
"""
compute_all_metrics.py
Walks every experiment folder under paper_experiments/ and computes the metrics
needed for the reuse chapter. Outputs ONE summary (printed + chapter_metrics.csv)
that you paste back so the chapter can be written from real numbers.

Run from: /Users/sepideh.masoudi/Desktop/paper_experiments
  python3 compute_all_metrics.py
"""
import os, glob, json, csv
import pandas as pd

ROOT = "."
SERVICE_UIDS = {
    "a35b873b-a47b-4833-983d-89866cf55b30": "featurecounts",
    "d7f1ab00-0042-4627-803e-10346fc79c3b": "stringtie",
}

def tracetosec(t):
    t = str(t).strip()
    if not t or t == "-": return 0.0
    if t.endswith("ms"): return float(t[:-2])/1000
    s=0.0
    if "h" in t:
        h,t=t.split("h"); s+=float(h)*3600
    if "m " in t:
        m,t=t.split("m "); s+=float(m)*60
    elif t.endswith("m") and not t.endswith("ms"):
        s+=float(t[:-1])*60; t=""
    if t.endswith("s"): s+=float(t[:-1])
    return s

def integrate(power_csv, vidx=2):
    """Trapezoidal integral of a watts-over-time CSV (Treatment rows) -> joules."""
    try:
        df = pd.read_csv(power_csv)
    except Exception:
        return float("nan")
    tcol = df.columns[-1]
    df = df[df[tcol]=="Treatment"]
    if df.empty: return float("nan")
    ep = df.iloc[:,1].astype(float).values
    w  = df.iloc[:,vidx].astype(float).values
    e=0.0
    for i in range(1,len(ep)):
        dt=ep[i]-ep[i-1]
        if dt>0: e+=0.5*(w[i]+w[i-1])*dt
    return e

def run_meta(folder):
    rj=os.path.join(folder,"run.json")
    if not os.path.isfile(rj): return None
    with open(rj) as f: m=json.load(f)
    return m

def node_energy(folder):
    return integrate(os.path.join(folder,"data","kepler_node_cpu_power_sum.csv"))

def pod_energy_total(folder):
    f=os.path.join(folder,"data","kepler_pod_cpu_power_joules_raw.csv")
    try: df=pd.read_csv(f)
    except: return float("nan")
    df=df[df["treatment"]=="Treatment"]
    return float(df["kepler_pod_cpu_power_joules_raw"].astype(float).sum())

def service_energy(folder):
    f=os.path.join(folder,"data","kepler_pod_cpu_power_joules_raw.csv")
    try: df=pd.read_csv(f)
    except: return float("nan")
    df=df[df["treatment"]=="Treatment"]
    tot=0.0
    for uid in SERVICE_UIDS:
        tot+=float(df[df["pod_id"]==uid]["kepler_pod_cpu_power_joules_raw"].astype(float).sum())
    return tot

def collect(label, folder, rows):
    m=run_meta(folder)
    if not m: return
    exp=m.get("user_data",{}).get("experiment","?")
    dur=m.get("treatment_duration", float("nan"))
    ne=node_energy(folder)
    pe=pod_energy_total(folder)
    se=service_energy(folder)
    rows.append({
        "group":label, "experiment":exp,
        "duration_s":round(dur,1) if dur==dur else "",
        "node_energy_J":round(ne,1) if ne==ne else "",
        "all_pods_energy_J":round(pe,1) if pe==pe else "",
        "service_energy_J":round(se,1) if se==se else "",
        "service_pct":round(se/pe*100,1) if (pe and se==se and pe==pe and pe>0) else "",
    })

def main():
    rows=[]
    # sequential baseline + reuse: baseline/u*, data_reuse/u*
    for scale_dir in glob.glob(f"{ROOT}/baseline/*") + glob.glob(f"{ROOT}/baseline/u*"):
        for d in glob.glob(f"{scale_dir}/nextflow_rnaseq_*"):
            collect(f"baseline/{os.path.basename(scale_dir)}", d, rows)
    for scale_dir in glob.glob(f"{ROOT}/data_reuse/u*"):
        for d in glob.glob(f"{scale_dir}/nextflow_rnaseq_*"):
            collect(f"data_reuse/{os.path.basename(scale_dir)}", d, rows)
    # pod-service sequential
    for scale_dir in glob.glob(f"{ROOT}/pod_service/u*"):
        for d in glob.glob(f"{scale_dir}/nextflow_rnaseq_*"):
            collect(f"pod_service/{os.path.basename(scale_dir)}", d, rows)
    # pipeline under stress
    for d in glob.glob(f"{ROOT}/pipeline_under_stress/nextflow_rnaseq_*"):
        collect("pipeline_under_stress", d, rows)
    # concurrent reuse sim
    for d in glob.glob(f"{ROOT}/concurrent_reuse_sim/nextflow_rnaseq_*"):
        collect("concurrent_reuse_sim", d, rows)

    df=pd.DataFrame(rows).sort_values(["group","experiment"])
    df.to_csv("chapter_metrics.csv", index=False)
    print("="*90)
    print("CHAPTER METRICS  (also saved to chapter_metrics.csv)")
    print("="*90)
    # print as aligned text so it's easy to paste back
    with pd.option_context('display.max_rows', None, 'display.width', 200):
        print(df.to_string(index=False))

if __name__=="__main__":
    main()