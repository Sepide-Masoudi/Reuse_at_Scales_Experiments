import subprocess
import threading
import sys
from logging import getLogger
from sma import SustainabilityMeasurementAgent, Config, SMASession
from dataclasses import dataclass

@dataclass
class Experiment:
    name: str
    num_users: int
    run_id: int
    type: str = "pod-service-reuse-concurrent"

    def to_dict(self) -> dict:
        return {
            "experiment": self.name,
            "num_users":  self.num_users,
            "run_id":     self.run_id,
            "type":       self.type,
        }

class ExperimentTrigger:
    def __init__(self, experiment: Experiment):
        self.experiment = experiment

    def trigger(self, cancel: threading.Event = None, **kwargs) -> dict:
        script = "./phase3_pod_service_concurrent.sh"
        print(f"🚀 Running {self.experiment.num_users} users | pod service reuse (concurrent)")
        subprocess.run(
            [script, str(self.experiment.num_users)],
            check=True
        )
        print("✅ Concurrent pod service reuse completed")
        return self.experiment.to_dict()

def main() -> None:
    log = getLogger("experiment.main")
    config = Config.from_file("./nextflow-sma-measurments.yaml")

    # Accept num_users as command line argument, default to [2, 4]
    if len(sys.argv) > 1:
        user_counts = [int(sys.argv[1])]
    else:
        user_counts = [2, 4]

    repetitions = 1

    for num_users in user_counts:
        for run_id in range(1, repetitions + 1):
            exp = Experiment(
                name=f"rnaseq-pod-service-concurrent-U{num_users}-run{run_id}",
                num_users=num_users,
                run_id=run_id,
            )
            print(f"\n==============================")
            print(f"Starting: {exp.name}")
            print(f"==============================")

            sma = SustainabilityMeasurementAgent(config)
            sma.setup(SMASession(name=exp.name))
            sma.connect()
            sma.run(ExperimentTrigger(exp))
            sma.teardown()
            print(f"✅ Experiment finished: {exp.name}")

    log.info("All concurrent pod service experiments finished.")

if __name__ == "__main__":
    main()