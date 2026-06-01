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
    type: str = "data-reuse"

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
        script = "./phase2_reuse.sh"
        print(
            f"🚀 Running {self.experiment.num_users} users | "
            f"{self.experiment.reuse_pct}% reuse via {script}"
        )
        subprocess.run(
            [script,
             str(self.experiment.num_users),
             str(self.experiment.reuse_pct)],
            check=True
        )
        print("✅ Reuse run completed successfully")
        return self.experiment.to_dict()


def main() -> None:
    log = getLogger("experiment.main")
    config = Config.from_file("./nextflow-sma-measurments.yaml")

    user_counts = [2, 4, 8]
    reuse_pcts  = [10, 20, 50]
    repetitions = 1

    for num_users in user_counts:
        for reuse_pct in reuse_pcts:
            for run_id in range(1, repetitions + 1):
                exp = Experiment(
                    name=f"rnaseq-reuse-U{num_users}-{reuse_pct}pct-run{run_id}",
                    num_users=num_users,
                    run_id=run_id,
                    reuse_pct=reuse_pct,
                )
                print(f"\n==============================")
                print(
                    f"Starting: {exp.name} | "
                    f"users={num_users} | reuse={reuse_pct}%"
                )
                print(f"==============================")

                sma = SustainabilityMeasurementAgent(config)
                sma.setup(SMASession(name=exp.name))
                sma.connect()
                sma.run(ExperimentTrigger(exp))
                sma.teardown()
                print(f"✅ Experiment finished: {exp.name}")

    log.info("All reuse experiments finished.")


if __name__ == "__main__":
    main()
