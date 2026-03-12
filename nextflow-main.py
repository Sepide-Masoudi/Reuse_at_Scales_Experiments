import subprocess
from logging import getLogger
from sma import SustainabilityMeasurementAgent, Config, SMASession
from dataclasses import dataclass
from typing import Callable
from pathlib import Path


# -----------------------------
# Experiment model
# -----------------------------
@dataclass
class Experiment:
    name: str
    run_id: int

    def to_dict(self) -> dict:
        return {
            "experiment": self.name,
            "run_id": self.run_id,
        }


# -----------------------------
# Experiment lifecycle
# -----------------------------
def prepare_experiment(experiment: Experiment) -> None:
    print(f"Preparing experiment: {experiment.name}")


def wait_for_experiment_completion(experiment: Experiment) -> Callable[[], dict]:
    def trigger() -> dict:
        # -------------------------
        # Run nextflow pipeline
        # -------------------------
        script = "./run_nextflow.sh"
        print(f"🚀 Running pipeline via {script}")
        subprocess.run(
            [script],
            check=True
        )
        print("✅ Pipeline completed successfully")
        return experiment.to_dict()
    return trigger


def cleanup_experiment(experiment: Experiment) -> None:
    print(f"Cleaning up experiment: {experiment.name}")


# -----------------------------
# Main
# -----------------------------
def main() -> None:
    log = getLogger("experiment.main")
    config = Config.from_file("./nextflow-sma-measurments.yaml")

    repetitions = 1  # repeat each experiment x times

    for run_id in range(1, repetitions + 1):
        exp = Experiment(
            name=f"rnaseq-run{run_id}",
            run_id=run_id,
        )

        print("\n==============================")
        print(f"Starting experiment: {exp.name} | run={run_id}/{repetitions}")
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