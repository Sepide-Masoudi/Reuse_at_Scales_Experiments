#!/usr/bin/env python3
"""
main_concurrent_reuse_sim.py
Trace-parameterized CONCURRENT data-reuse simulation (Option B), measured on the SUT.

Models N concurrent pipeline "users" as N CPU-burn pods, each replaying a real
trace-derived CPU profile (baseline = full compute; reuse@X = cached tasks skipped).
Because reuse users skip cached compute, each consumes less CPU -> more users fit
before the 8-core SUT saturates. This bypasses the Nextflow JVM ceiling and the
cache histlock (no Nextflow, no shared cache) that blocked real concurrent reuse.

For each workload W in {baseline, reuse10, reuse20, reuse50}
  and each concurrency N in {2,4,8,16}:
    - launch N CPU-burn pods (profile W) on the SUT
    - SMA measures the window
    - wait for all pods, delete them
  -> one SMA folder per (W, N) = 16 measured runs.

Prereqs staged on PVC at /workspace/sim/ :
  cpu_burn_worker.py
  profile_baseline.json, profile_reuse10.json, profile_reuse20.json, profile_reuse50.json

Usage:
  python3 main_concurrent_reuse_sim.py
"""
import os
import time
import json
import subprocess
import threading
import datetime
from dataclasses import dataclass
from logging import getLogger
from sma import SustainabilityMeasurementAgent, Config, SMASession

SIM_DIR = "/workspace/sim"
WORKER = f"{SIM_DIR}/cpu_burn_worker.py"
PY_IMAGE = "python:3.11-slim"
NAMESPACE = "nextflow"

WORKLOADS = ["baseline", "reuse10", "reuse20", "reuse50"]
CONCURRENCY = [2, 4, 8, 16]

UID_LOG = "/workspace/sim_pod_uids.csv"

# Explicit env so kubectl works regardless of how SMA spawns the subprocess
KUBE_ENV = {
    **os.environ,
    "KUBECONFIG": os.environ.get("KUBECONFIG", "/root/.kube/config"),
    "HOME": os.environ.get("HOME", "/root"),
    "PATH": os.environ.get("PATH", "") + ":/usr/local/bin:/usr/bin:/bin",
}


def kubectl(args, **kwargs):
    """Run a kubectl command with the explicit env."""
    return subprocess.run(["kubectl", *args], env=KUBE_ENV, **kwargs)


def profile_path(workload: str) -> str:
    return f"{SIM_DIR}/profile_{workload}.json"


def pod_manifest(name: str, workload: str) -> str:
    """A single CPU-burn pod, pinned to the SUT, mounting the PVC."""
    return f"""apiVersion: v1
kind: Pod
metadata:
  name: {name}
  namespace: {NAMESPACE}
  labels:
    app: reuse-sim
    workload: "{workload}"
spec:
  restartPolicy: Never
  nodeSelector:
    role: sut
  containers:
  - name: burn
    image: {PY_IMAGE}
    command: ["python3", "{WORKER}", "{profile_path(workload)}"]
    resources:
      requests:
        cpu: "100m"
      limits:
        cpu: "8"
    volumeMounts:
    - name: workspace
      mountPath: /workspace
  volumes:
  - name: workspace
    persistentVolumeClaim:
      claimName: nextflow-pvc
"""


@dataclass
class SimExperiment:
    name: str
    workload: str
    concurrency: int

    def to_dict(self):
        return {"experiment": self.name, "workload": self.workload,
                "concurrency": self.concurrency, "type": "concurrent-reuse-sim"}


class _PodManager:
    def __init__(self, workload: str, n: int, run_ts: str):
        self.workload = workload
        self.n = n
        self.run_ts = run_ts
        self.pod_names = [f"sim-{workload}-c{n}-{run_ts}-{i}" for i in range(1, n + 1)]

    def launch(self):
        for name in self.pod_names:
            manifest = pod_manifest(name, self.workload)
            r = kubectl(["apply", "-f", "-"], input=manifest, text=True,
                        capture_output=True)
            if r.returncode != 0:
                raise RuntimeError(f"kubectl apply failed for {name}: {r.stderr.strip()}")
        print(f"   [pods] launched {self.n} x {self.workload}", flush=True)

    def log_uids(self, exp_name: str):
        time.sleep(5)  # let UIDs assign
        header = not os.path.exists(UID_LOG)
        with open(UID_LOG, "a") as f:
            if header:
                f.write("experiment,workload,concurrency,pod_name,pod_uid\n")
            for name in self.pod_names:
                try:
                    uid = kubectl(["get", "pod", name, "-n", NAMESPACE,
                         "-o", "jsonpath={.metadata.uid}"],
                        capture_output=True, text=True).stdout.strip()
                except Exception as e:
                    uid = f"ERROR:{e}"
                f.write(f"{exp_name},{self.workload},{self.n},{name},{uid}\n")
            f.flush()

    def wait_all(self, poll=15):
        """Block until every pod is Succeeded (or Failed)."""
        while True:
            phases = []
            for name in self.pod_names:
                try:
                    p = kubectl(["get", "pod", name, "-n", NAMESPACE,
                         "-o", "jsonpath={.status.phase}"],
                        capture_output=True, text=True).stdout.strip()
                except Exception:
                    p = "Unknown"
                phases.append(p)
            done = sum(1 for p in phases if p in ("Succeeded", "Failed"))
            running = sum(1 for p in phases if p == "Running")
            pending = sum(1 for p in phases if p == "Pending")
            print(f"   [pods] done={done}/{self.n} running={running} pending={pending}", flush=True)
            if done == self.n:
                return
            time.sleep(poll)

    def delete(self):
        for name in self.pod_names:
            kubectl(["delete", "pod", name, "-n", NAMESPACE,
                            "--ignore-not-found", "--wait=false"],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print(f"   [pods] deleted {self.workload} c{self.n}", flush=True)


class SimTrigger:
    def __init__(self, mgr: "_PodManager", exp: SimExperiment):
        self.mgr = mgr
        self.exp = exp

    def trigger(self, cancel: threading.Event = None, **kwargs):
        print(f"🚀 [SMA] {self.exp.workload} concurrency={self.exp.concurrency}", flush=True)
        self.mgr.launch()
        self.mgr.log_uids(self.exp.name)
        self.mgr.wait_all()
        print(f"✅ [SMA] {self.exp.workload} c{self.exp.concurrency} all pods done", flush=True)
        return self.exp.to_dict()


def main():
    log = getLogger("experiment.main")
    config = Config.from_file("./nextflow-sma-measurments.yaml")

    if os.path.exists(UID_LOG):
        os.remove(UID_LOG)

    print("=" * 60)
    print("CONCURRENT REUSE SIMULATION (trace-parameterized CPU load)")
    print(f"Workloads: {WORKLOADS}")
    print(f"Concurrency: {CONCURRENCY}")
    print("=" * 60)

    for workload in WORKLOADS:
        for n in CONCURRENCY:
            run_ts = datetime.datetime.now().strftime("%Y%m%d%H%M%S")  # no underscore: valid pod name
            exp = SimExperiment(name=f"reuse-sim-{workload}-c{n}-run1",
                                workload=workload, concurrency=n)
            print(f"\n----- {workload} | concurrency {n} -----")
            mgr = _PodManager(workload, n, run_ts)
            sma = SustainabilityMeasurementAgent(config)
            try:
                sma.setup(SMASession(name=exp.name))
                sma.connect()
                sma.run(SimTrigger(mgr, exp))
            except Exception as e:
                print(f"⚠️  {workload} c{n}: {e}", flush=True)
            finally:
                try:
                    sma.teardown()
                finally:
                    mgr.delete()
            print(f"----- {workload} | c{n} measured -----", flush=True)

    print("\n" + "=" * 60)
    print(f"🎉 Concurrent reuse simulation complete.")
    print(f"   {len(WORKLOADS)} workloads x {len(CONCURRENCY)} levels = "
          f"{len(WORKLOADS)*len(CONCURRENCY)} runs")
    print("=" * 60)
    log.info("Concurrent reuse simulation finished.")


if __name__ == "__main__":
    main()