import subprocess
from logging import getLogger
import sys
from sma import SustainabilityMeasurementAgent, Config, SMAObserver, SMASession
from dataclasses import dataclass
from typing import Callable


#TODO: add thing to handle the experimentes, e.g., multiple runs, which varaibles we are doing etc

@dataclass
class Experiment:
    name: str
    run: int
    
    users: int
    reuse_users:int
    
    def to_dict(self) -> dict:
        return {
            "experiment": self.name,
            "run": self.run,
            "users": self.users,
            "reuse_users": self.reuse_users
        }
    
    
def prepare_experiment(experiment: Experiment) -> None:
    #TODO: deploy things we need for reuse
    pass


def wait_for_experiment_completion(experiment) -> Callable[[], dict]:
    def trigger() -> dict:
        wrapper_script = "./run_all_experiments.sh"  
        print(f"Starting experiment batch via {wrapper_script}...")
        result = subprocess.run(wrapper_script, shell=True, check=True)
        print("Wrapper script finished ✅")

        return experiment.to_dict()

    return trigger
    

def cleanup_experiment(experiment: Experiment) -> None:
    pass


def main() -> None:
    config = Config.from_file("./sma-measurments.yaml")
    log = getLogger("experiment.main")

    sma = SustainabilityMeasurementAgent(config)
    sma.setup(SMASession(
       name="PipelineReuse"
    ))
    sma.connect()
    
    #TODO: generate Experiments form
    
    exp = Experiment(
        name="no-reuse-baremetal-pipeline-experiment",
        run=1,
        users=100,
        reuse_users=50
    ) 
    
    prepare_experiment(exp)
    
    wait_for_exp = wait_for_experiment_completion(exp)
    
    #TODO: if you need to start trigger something before wating, now's the time, possibly in parallel...
    
    sma.run(wait_for_exp)
    
    cleanup_experiment(exp)
    sma.teardown()

    log.info("Sustainability Measurement Agent finished.")


if __name__ == "__main__":
    main()
