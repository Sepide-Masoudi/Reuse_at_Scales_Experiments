import subprocess
import concurrent.futures
from logging import getLogger
from sma import SustainabilityMeasurementAgent, Config, SMASession
from dataclasses import dataclass
from typing import Callable

@dataclass
class Experiment:
    name: str
    num_users: int
    run_id: int
    reuse_mood: str

    def to_dict(self) -> dict:
        return {
            "experiment": self.name,
            "num_users": self.num_users,
            "run_id": self.run_id,
            "reuse_mood" : self.reuse_mood,
        }

def prepare_experiment(experiment: Experiment) -> None:
    print(f"Preparing experiment: {experiment.name}")

def wait_for_experiment_completion(experiment: Experiment) -> Callable[[], dict]:
    def trigger() -> dict:
        script = "./run_nextflow-resume.sh"   ## change the experiment config
        print(f"🚀 Running {experiment.num_users} concurrent users via {script}")
        subprocess.run(
            [script, str(experiment.num_users)],
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

    user_counts = [2]
    repetitions = 1

    for num_users in user_counts:
        for run_id in range(1, repetitions + 1):
            exp = Experiment(
                name=f"rnaseq-users{num_users}-run{run_id}",
                num_users=num_users,
                run_id=run_id,
                reuse_mood="resume"
            )

            print("\n==============================")
            print(f"Starting: {exp.name} | users={num_users} | run={run_id}/{repetitions}")
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