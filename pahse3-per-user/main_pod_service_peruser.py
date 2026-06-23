#!/usr/bin/env python3
"""
main_pod_service_peruser.py
PER-USER measurement version of the pod-service experiment.

Why this exists:
  The original main called sma.run() ONCE around the whole multi-user script,
  producing a single measurement window spanning the entire run. For runs longer
  than Prometheus retention (8h here), the end-of-run fetch lost most/all data.

What this does:
  Calls sma.run() ONCE PER USER. Each run() has its own start_time + run_hash,
  so SMA writes a SEPARATE report folder per user, and fetches immediately after
  that user finishes (~28 min window — far inside retention, restart-safe).
  Bonus: you get clean PER-USER energy data.

Usage:
  python3 main_pod_service_peruser.py <NUM_USERS>
  e.g. python3 main_pod_service_peruser.py 32
"""

import sys
import subprocess
import threading
import datetime
from logging import getLogger
from dataclasses import dataclass
from sma import SustainabilityMeasurementAgent, Config, SMASession


SINGLE_USER_SCRIPT = "./phase3_pod_service_single.sh"


@dataclass
class UserRun:
    experiment: str
    num_users: int
    user_index: int
    timestamp: str
    type: str = "pod-service-reuse"

    def to_dict(self) -> dict:
        return {
            "experiment":  self.experiment,
            "num_users":   self.num_users,
            "user_index":  self.user_index,
            "timestamp":   self.timestamp,
            "type":        self.type,
        }


class SingleUserTrigger:
    """Runs the pipeline for exactly ONE user. Returned dict becomes user_data
    in that user's SMA report, so each folder is identifiable."""

    def __init__(self, run: UserRun):
        self.run = run

    def trigger(self, cancel: threading.Event = None, **kwargs) -> dict:
        print(f"🚀 [SMA] user {self.run.user_index}/{self.run.num_users}"
              f" (exp={self.run.experiment})")
        subprocess.run(
            [SINGLE_USER_SCRIPT,
             str(self.run.user_index),
             str(self.run.num_users),
             self.run.timestamp],
            check=True,
        )
        print(f"✅ [SMA] user {self.run.user_index} trigger finished")
        return self.run.to_dict()


def main() -> None:
    log = getLogger("experiment.main")

    if len(sys.argv) < 2:
        print("Usage: python3 main_pod_service_peruser.py <NUM_USERS>")
        sys.exit(1)
    num_users = int(sys.argv[1])

    # One shared timestamp groups all users of this experiment together.
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    experiment = f"rnaseq-pod-service-U{num_users}-run1"

    config = Config.from_file("./nextflow-sma-measurments.yaml")

    print("=" * 60)
    print(f"PER-USER MEASUREMENT")
    print(f"Experiment : {experiment}")
    print(f"Users      : {num_users}")
    print(f"Timestamp  : {timestamp}")
    print(f"Each user → its own sma.run() → its own report folder + fetch")
    print("=" * 60)

    # Setup/connect ONCE for the whole experiment.
    sma = SustainabilityMeasurementAgent(config)
    sma.setup(SMASession(name=experiment))
    sma.connect()

    failed = 0
    try:
        for i in range(1, num_users + 1):
            user_run = UserRun(
                experiment=experiment,
                num_users=num_users,
                user_index=i,
                timestamp=timestamp,
            )
            print(f"\n----- USER {i}/{num_users} : measurement window start -----")
            try:
                # One measurement window + fetch for THIS user only.
                sma.run(SingleUserTrigger(user_run))
                print(f"----- USER {i}/{num_users} : measured + fetched -----")
            except subprocess.CalledProcessError as e:
                failed += 1
                print(f"⚠️  USER {i} pipeline returned non-zero (exit {e.returncode}); "
                      f"measurement window still recorded. Continuing.")
            except Exception as e:
                failed += 1
                print(f"⚠️  USER {i} measurement error: {e}. Continuing.")
    finally:
        sma.teardown()

    print("\n" + "=" * 60)
    if failed == 0:
        print(f"🎉 {experiment} complete — all {num_users} users measured per-user")
    else:
        print(f"⚠️  {experiment} done with {failed}/{num_users} user(s) flagged")
    print("=" * 60)
    log.info("Per-user pod-service experiment finished.")


if __name__ == "__main__":
    main()
