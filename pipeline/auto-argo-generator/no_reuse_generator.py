from base_generator import BaseArgoGenerator


class NoReuseArgoGenerator(BaseArgoGenerator):

    def generate_all(self) -> list[dict]:
        workflows = []
        for pipeline in self.config["pipelines"]:
            workflows.append(self._generate_one(pipeline))
        return workflows

    def _generate_one(self, pipeline: dict) -> dict:
        workflow = self._base_workflow(pipeline["name"])

        templates = {}
        steps = []

        for block in pipeline["flow"]:
            if "parallel" in block:
                parallel_steps = []
                for stage in block["stages"]:
                    step_name = f"{stage['stage']}-{id(stage)}"
                    parallel_steps.append([
                        self._create_step(step_name, stage)
                    ])
                    templates[stage["stage"]] = self._create_template(stage["stage"])
                steps.append(parallel_steps)
            else:
                step_name = f"{block['stage']}-{id(block)}"
                steps.append([
                    [self._create_step(step_name, block)]
                ])
                templates[block["stage"]] = self._create_template(block["stage"])

        workflow["spec"]["templates"] = (
            [{"name": "main", "steps": steps}]
            + list(templates.values())
        )

        return workflow

    def _create_step(self, name: str, block: dict) -> dict:
        return {
            "name": name,
            "template": block["stage"],
            "arguments": {
                "parameters": [
                    {"name": k, "value": v}
                    for k, v in block["parameters"].items()
                ]
            }
        }
