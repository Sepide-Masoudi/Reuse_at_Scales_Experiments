#!/usr/bin/env python3
"""
main_pipeline_under_stress.py
Measures how a REAL pipeline degrades when the shared reuse services are under
concurrent stress.

For each stress level S in [0, 2, 4, 8, 16, 32, 64]:
  1. (if S>0) launch S background stressers on featureCounts AND S on stringtie
     -> sustained contention on the shared services the pipeline will use
  2. run ONE pod-service pipeline (full rnaseq, uses those services),
     measured by SMA -> its own folder named pipeline-under-stress-s{S}-run1
  3. kill all background stressers
  4. next level

Result: 7 SMA folders = the SAME pipeline measured under increasing background
concurrency. The pipeline's energy/CPU/duration vs S is the degradation curve.
S=0 is the no-contention baseline.

Bypasses the CP JVM ceiling for the *stress* (stressers are lightweight HTTP
senders, not Nextflow), so we can apply far more contention than running real
concurrent pipelines would allow.

Usage:
  python3 main_pipeline_under_stress.py
"""

import os
import sys
import time
import signal
import subprocess
import threading
import datetime
from dataclasses import dataclass
from logging import getLogger
from sma import SustainabilityMeasurementAgent, Config, SMASession

SINGLE_PIPELINE = "./phase3_pod_service_single.sh"
STRESS_SCRIPT = "./stress_background.sh"
STRESS_CSV = "/workspace/stress_side_requests.csv"

# Stress = number of OTHER simulated pipelines calling the services concurrently.
# Total concurrent callers including the 1 real measured pipeline:
#   stress 0  -> 1 total (baseline, no contention)
#   stress 1  -> 2 total
#   stress 3  -> 4 total
#   stress 7  -> 8 total
#   stress 15 -> 16 total
#   stress 31 -> 32 total
#   stress 63 -> 64 total
STRESS_LEVELS = [0, 1, 3, 7, 15, 31, 63]

SERVICE_UID_LOG = "/workspace/service_pod_uids.csv"


def capture_service_uids(stress_level: int, exp_name: str) -> None:
    """Log the featureCounts/stringtie pod UIDs so their energy can be filtered
    out of kepler_pod_cpu_power_joules_raw in analysis (per-pod attribution)."""
    rows = []
    for svc in ("featurecounts-service", "stringtie-service"):
        try:
            uid = subprocess.check_output(
                ["kubectl", "get", "pod", svc, "-n", "nextflow",
                 "-o", "jsonpath={.metadata.uid}"],
                text=True, stderr=subprocess.STDOUT,
            ).strip()
        except Exception as e:
            uid = f"ERROR:{e}"
        rows.append(f"{exp_name},{stress_level},{svc},{uid}")
    try:
        header = not os.path.exists(SERVICE_UID_LOG)
        with open(SERVICE_UID_LOG, "a") as f:
            if header:
                f.write("experiment,stress_level,service,pod_uid\n")
            for r in rows:
                f.write(r + "\n")
            f.flush()
        print(f"   [uids] logged service pod UIDs for stress={stress_level}: {rows}", flush=True)
    except Exception as e:
        print(f"   [uids] WARNING failed to write UID log: {e}", flush=True)


@dataclass
class StressExperiment:
    name: str
    stress: int
    type: str = "pipeline-under-stress"

    def to_dict(self) -> dict:
        return {"experiment": self.name, "stress_level": self.stress, "type": self.type}


class _StressManager:
    """Launches/kills background stressers on both services for a given level."""
    def __init__(self, level: int):
        self.level = level
        self.procs = []

    def start(self):
        if self.level <= 0:
            return
        for service in ("featurecounts", "stringtie"):
            p = subprocess.Popen(
                [STRESS_SCRIPT, service, str(self.level), STRESS_CSV],
                preexec_fn=os.setsid,  # own process group so we can kill the whole tree
            )
            self.procs.append(p)
        # let the stress ramp up before the pipeline starts
        time.sleep(10)
        print(f"   [stress] {self.level} senders/service running on featurecounts+stringtie")

    def stop(self):
        for p in self.procs:
            try:
                os.killpg(os.getpgid(p.pid), signal.SIGTERM)
            except Exception:
                pass
        # also sweep any stray curl/loops
        subprocess.run(["pkill", "-f", "stress_background.sh"], check=False)
        subprocess.run(["pkill", "-f", "loadtest_inputs/test.bam"], check=False)
        time.sleep(3)
        self.procs = []
        if self.level > 0:
            print(f"   [stress] level {self.level} stressers stopped")


class PipelineTrigger:
    """Runs ONE pod-service pipeline (user index 1). SMA measures this window."""
    def __init__(self, exp: StressExperiment, run_ts: str):
        self.exp = exp
        self.run_ts = run_ts

    def trigger(self, cancel: threading.Event = None, **kwargs) -> dict:
        print(f"🚀 [SMA] measured pipeline under stress={self.exp.stress}")
        # phase3_pod_service_single.sh <USER_INDEX> <TOTAL_USERS> <TIMESTAMP>
        subprocess.run(
            [SINGLE_PIPELINE, "1", "1", f"stress{self.exp.stress}_{self.run_ts}"],
            check=True,
        )
        print(f"✅ [SMA] pipeline (stress={self.exp.stress}) finished")
        return self.exp.to_dict()


def main() -> None:
    log = getLogger("experiment.main")
    config = Config.from_file("./nextflow-sma-measurments.yaml")

    with open(STRESS_CSV, "w") as f:
        f.write("service,stress_level,user_id,http_status,latency_sec,start_epoch\n")

    print("=" * 60)
    print("PIPELINE UNDER STRESS")
    print(f"Stress levels (senders/service): {STRESS_LEVELS}")
    print("Each level: background stress on both services + 1 measured pipeline")
    print("=" * 60)

    for s in STRESS_LEVELS:
        run_ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        exp = StressExperiment(name=f"pipeline-under-stress-s{s}-run1", stress=s)
        print(f"\n----- STRESS {s} -----")

        stress = _StressManager(s)
        sma = SustainabilityMeasurementAgent(config)
        try:
            stress.start()                       # background contention (no-op if s=0)
            capture_service_uids(s, exp.name)    # log service pod UIDs for attribution
            sma.setup(SMASession(name=exp.name))
            sma.connect()
            sma.run(PipelineTrigger(exp, run_ts))   # measured pipeline
        except subprocess.CalledProcessError as e:
            print(f"⚠️  stress {s}: pipeline returned non-zero (exit {e.returncode})")
        finally:
            try:
                sma.teardown()
            finally:
                stress.stop()                    # always kill stressers
        print(f"----- STRESS {s} : measured -----")

    print("\n" + "=" * 60)
    print(f"🎉 Pipeline-under-stress sweep complete. Levels: {STRESS_LEVELS}")
    print("=" * 60)
    log.info("Pipeline-under-stress experiment finished.")


if __name__ == "__main__":
    main()