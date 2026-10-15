import subprocess
from logging import getLogger
from sma import SustainabilityMeasurementAgent, Config, SMASession
from dataclasses import dataclass
from typing import Callable


@dataclass
class Experiment:
    name: str
    num_users: int
    run_id: int
    reuse_pct: int        # 10, 20, or 50
    queue_size: int
    cpu: str
    mem: str

    def to_dict(self) -> dict:
        return {
            "experiment":   self.name,
            "num_users":    self.num_users,
            "run_id":       self.run_id,
            "reuse_pct":    self.reuse_pct,
            "queue_size":   self.queue_size,
            "cpu":          self.cpu,
            "mem":          self.mem,
        }


def prepare_experiment(experiment: Experiment) -> None:
    print(f"Preparing experiment: {experiment.name}")


def wait_for_experiment_completion(experiment: Experiment) -> Callable[[], dict]:
    def trigger() -> dict:
        script = "./run_nextflow_partial_resume.sh"
        print(
            f"🚀 Running {experiment.num_users} users | "
            f"{experiment.reuse_pct}% reuse via {script}"
        )
        subprocess.run(
            [script,
             str(experiment.num_users),
             str(experiment.reuse_pct)],
            check=True
        )
        print("✅ All users completed successfully")
        return experiment.to_dict()
    return trigger


def cleanup_experiment(experiment: Experiment) -> None:
    print(f"Cleaning up experiment: {experiment.name}")


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
                    name=f"rnaseq-U{num_users}-reuse{reuse_pct}pct-run{run_id}",
                    num_users=num_users,
                    run_id=run_id,
                    reuse_pct=reuse_pct,
                    queue_size=2,
                    cpu="1",
                    mem="2",
                )

                print("\n==============================")
                print(
                    f"Starting: {exp.name} | "
                    f"users={num_users} | reuse={reuse_pct}% | "
                    f"run={run_id}/{repetitions}"
                )
                print("==============================")

                prepare_experiment(exp)
                sma = SustainabilityMeasurementAgent(config)
                sma.setup(SMASession(name=exp.name))
                sma.connect()
                trigger = wait_for_experiment_completion(exp)
                sma.run(trigger)
                cleanup_experiment(exp)
                sma.teardown()
                print(f"✅ Experiment finished: {exp.name}")

    log.info("All experiments finished.")


if __name__ == "__main__":
    main()