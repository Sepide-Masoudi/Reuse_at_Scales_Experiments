import yaml
import hashlib


class BaseArgoGenerator:
    def __init__(self, config_path: str):
        with open(config_path, "r") as f:
            self.config = yaml.safe_load(f)


    def _hash_stage(self, stage_name: str, parameters: dict) -> str:
        raw = f"{stage_name}:{sorted(parameters.items())}"
        return hashlib.md5(raw.encode()).hexdigest()[:8]

    def _get_stage_params(self, stage_name: str):
        for stage in self.config["stages"]:
            if stage["name"] == stage_name:
                return list(stage["parameters"].keys())
        raise ValueError(f"Stage not found: {stage_name}")


    def _base_workflow(self, name: str) -> dict:
        return {
            "apiVersion": "argoproj.io/v1alpha1",
            "kind": "Workflow",
            "metadata": {
                "generateName": f"{name}-"
            },
            "spec": {
                "entrypoint": "main",
                "templates": []
            }
        }

    def _create_template(self, stage_name: str) -> dict:
        params = self._get_stage_params(stage_name)

        return {
            "name": stage_name,
            "inputs": {
                "parameters": [{"name": p} for p in params]
            },
            "container": {
                "image": f"{stage_name}:latest",
                "command": ["python", "app.py"],
                "args": [
                    f"--{p}={{inputs.parameters.{p}}}" for p in params
                ]
            }
        }
