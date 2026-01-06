from base_generator import BaseArgoGenerator


class ReuseAwareArgoGenerator(BaseArgoGenerator):

    def generate_all(self) -> list[dict]:
        workflows = []
        for pipeline in self.config["pipelines"]:
            workflows.append(self._generate_one(pipeline))
        return workflows

    def _generate_one(self, pipeline: dict) -> dict:
        workflow = self._base_workflow(f"{pipeline['name']}-reuse")

        templates = {}
        executed = {}
        steps = []

        for block in pipeline["flow"]:
            if "parallel" in block:
                parallel_steps = []
                for stage in block["stages"]:
                    step = self._reuse_step(stage, templates, executed)
                    parallel_steps.append([step])
                steps.append(parallel_steps)
            else:
                step = self._reuse_step(block, templates, executed)
                steps.append([[step]])

        workflow["spec"]["templates"] = (
            [{"name": "main", "steps": steps}]
            + list(templates.values())
        )

        return workflow

    def _reuse_step(self, block: dict, templates: dict, executed: dict) -> dict:
        stage_name = block["stage"]
        params = block["parameters"]
        stage_hash = self._hash_stage(stage_name, params)

        if stage_hash not in executed:
            executed[stage_hash] = f"{stage_name}-{stage_hash}"
            templates[stage_name] = self._create_template(stage_name)

        return {
            "name": executed[stage_hash],
            "template": stage_name,
            "arguments": {
                "parameters": [
                    {"name": k, "value": v}
                    for k, v in params.items()
                ]
            }
        }
