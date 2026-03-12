import subprocess
from logging import getLogger
from sma import SustainabilityMeasurementAgent, Config, SMASession
from dataclasses import dataclass
from typing import Callable, List
from pathlib import Path


# -----------------------------
# Experiment model
# -----------------------------

@dataclass
class Experiment:
    name: str
    workflow_file: str
    stress_factor: int

    def to_dict(self) -> dict:
        return {
            "experiment": self.name,
            "workflow": self.workflow_file,
            "stress_factor": self.stress_factor
        }


# -----------------------------
# Experiment lifecycle
# -----------------------------

def prepare_experiment(experiment: Experiment) -> None:
    print(f"Preparing experiment: {experiment.name}")


def wait_for_experiment_completion(experiment: Experiment) -> Callable[[], dict]:
    def trigger() -> dict:

        stress_proc = None

        # -------------------------
        # Start stress load first
        # -------------------------
        if experiment.stress_factor > 0:
            print(f"🔥 Starting stress load level {experiment.stress_factor}")
            stress_proc = subprocess.Popen(
                ["python", 
                "./pipeline/output/prime-service-stress.py",
                 str(experiment.stress_factor)]
            )

        # -------------------------
        # Run workflow
        # -------------------------

#        script = "./run_experiment_script.sh"
        script = "./pipeline/output/run_all_data_reuse_workflows.sh"


        print(f"🚀 Running workflow via {script} {experiment.workflow_file}")

        subprocess.run(
            [script, experiment.workflow_file],
            check=True
        )

        # -------------------------
        # Stop stress after workflow
        # -------------------------
        if stress_proc:
            print("🛑 Stopping stress load")
            stress_proc.terminate()
            stress_proc.wait()

        print("✅ Workflow completed successfully")
        return experiment.to_dict()

    return trigger



def cleanup_experiment(experiment: Experiment) -> None:
    print(f"Cleaning up experiment: {experiment.name}")


# -----------------------------
# Discover workflows
# -----------------------------

def discover_workflows(path: str) -> List[Path]:
    p = Path(path)
    return sorted(list(p.glob("*.yaml")) + list(p.glob("*.yml")))


# -----------------------------
# Main
# -----------------------------

def main() -> None:
    log = getLogger("experiment.main")

    config = Config.from_file("./sma-measurments.yaml")

    workflow_dir = "./pipeline/output/one-by-one"
    workflow_files = discover_workflows(workflow_dir)

    if not workflow_files:
        raise RuntimeError(f"No workflow YAML files found in {workflow_dir}")

    print(f"Found {len(workflow_files)} workflows")

    stress_levels = [0] #[0, 5, 50]
    repetitions = 1  # repeat each experiment x times

    for wf in workflow_files:
        for stress in stress_levels:
            for run_id in range(1, repetitions + 1):

                exp = Experiment(
                    name=f"{wf.stem}-stress{stress}-run{run_id}",
                    workflow_file=str(wf),
                    stress_factor=stress
                )

                print("\n==============================")
                print(
                    f"Starting experiment: {exp.name} | "
                    f"stress={stress} | run={run_id}/{repetitions}"
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
