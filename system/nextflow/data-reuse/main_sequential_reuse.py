import subprocess
import threading
from logging import getLogger
from sma import SustainabilityMeasurementAgent, Config, SMASession
from dataclasses import dataclass

@dataclass
class Experiment:
    name: str
    num_users: int
    run_id: int
    reuse_pct: int
    baseline_timestamp: str
    type: str = "data-reuse-sequential"

    def to_dict(self) -> dict:
        return {
            "experiment": self.name,
            "num_users":  self.num_users,
            "run_id":     self.run_id,
            "reuse_pct":  self.reuse_pct,
            "type":       self.type,
        }

class ExperimentTrigger:
    def __init__(self, experiment: Experiment):
        self.experiment = experiment

    def trigger(self, cancel: threading.Event = None, **kwargs) -> dict:
        script = "./phase2_seq_measured.sh"
        print(
            f"🚀 Running {self.experiment.num_users} users | "
            f"{self.experiment.reuse_pct}% reuse (sequential)"
        )
        subprocess.run(
            [script,
             str(self.experiment.num_users),
             str(self.experiment.reuse_pct),
             self.experiment.baseline_timestamp],
            check=True
        )
        print("✅ Sequential reuse run completed")
        return self.experiment.to_dict()

def main() -> None:
    log = getLogger("experiment.main")
    config = Config.from_file("./nextflow-sma-measurments.yaml")

    baseline_timestamp = "20260525_171533"

    user_counts = [2, 4, 8]
    reuse_pcts  = [10, 20, 50]
    repetitions = 1

    for num_users in user_counts:
        for reuse_pct in reuse_pcts:
            for run_id in range(1, repetitions + 1):
                exp = Experiment(
                    name=f"rnaseq-seq-reuse-U{num_users}-{reuse_pct}pct-run{run_id}",
                    num_users=num_users,
                    run_id=run_id,
                    reuse_pct=reuse_pct,
                    baseline_timestamp=baseline_timestamp,
                )
                print(f"\n==============================")
                print(f"Starting: {exp.name}")
                print(f"==============================")

                # Seed OUTSIDE SMA (not measured)
                print(f"🔨 Seeding users 2-{num_users} (not measured)...")
                subprocess.run(
                    ["./phase2_seq_seed.sh",
                     str(num_users),
                     str(reuse_pct),
                     baseline_timestamp],
                    check=True
                )
                print(f"✅ Seeding done")

                # Measure only the reuse runs
                sma = SustainabilityMeasurementAgent(config)
                sma.setup(SMASession(name=exp.name))
                sma.connect()
                sma.run(ExperimentTrigger(exp))
                sma.teardown()
                print(f"✅ Experiment finished: {exp.name}")

    log.info("All sequential reuse experiments finished.")

if __name__ == "__main__":
    main()