import yaml
from pathlib import Path
import uuid

def load_config(file_path="./test-config-file/config.yaml"):
    with open(file_path, "r") as f:
        return yaml.safe_load(f)


def generate_argo_with_parallel(config):
    namespace = "no-reuse-pipeline" 
    pvc_name = config["Deployment"].get("pvcName", "argo-shard-pvc")
    stages_dict = {s["name"]: s for s in config["stages"]}

    workflows = []

    for pipeline in config["pipelines"]:
        pipeline_name = pipeline["name"]
        flow = pipeline["flow"]

        workflow = {
            "apiVersion": "argoproj.io/v1alpha1",
            "kind": "Workflow",
            "metadata": {
                "generateName": f"{pipeline_name}-",
                "namespace": namespace
            },
            "spec": {
                "entrypoint": pipeline_name,
                "serviceAccountName": "argo-workflow-sa",
                "volumes": [
                    {
                        "name": "shared-data",
                        "persistentVolumeClaim": {"claimName": pvc_name}
                    }
                ],
                "templates": []
            }
        }

        # main steps template
        steps_template = {"name": pipeline_name, "steps": []}
        step_counter = {}  # To track duplicate stage names in a pipeline

        for step in flow:
            # -------------------------
            # PARALLEL STAGES
            # -------------------------
            if isinstance(step, dict) and step.get("parallel", False):
                parallel_steps = []

                for stage_instance in step["stages"]:
                    stage_name = stage_instance["stage"]
                    stage_def = stages_dict[stage_name]
                    
                    # Handle duplicate stage names with counter
                    if stage_name not in step_counter:
                        step_counter[stage_name] = 1
                    else:
                        step_counter[stage_name] += 1
                    
                    # Create unique template name
                    if step_counter[stage_name] > 1:
                        template_name = f"{stage_name}-{step_counter[stage_name]}-{pipeline_name}"
                        step_display_name = f"{stage_name}-{step_counter[stage_name]}"
                    else:
                        template_name = f"{stage_name}-{pipeline_name}"
                        step_display_name = stage_name

                    # Register parallel leaf
                    parallel_steps.append({"name": step_display_name, "template": template_name})

                    # Build args - fix format to be separate args
                    args = []
                    for k, v in stage_instance.get("parameters", {}).items():
                        if isinstance(v, list):
                            v = ",".join(map(str, v))
                        args.append(f"--{k}")
                        if "=" not in str(v):  # Only add value if not already in key
                            args.append(str(v))

                    # Create container spec
                    container_spec = {
                        "image": f"no{stage_def['image']}",
                        "command": ["python", "main.py"],
                        "args": args,
                        "volumeMounts": [
                            {"name": "shared-data", "mountPath": stage_def["data-path"]}
                        ]
                    }

                    # Create template
                    stage_template = {
                        "name": template_name,
                        "container": container_spec
                    }

                    workflow["spec"]["templates"].append(stage_template)

                steps_template["steps"].append(parallel_steps)

            else:
                # -------------------------
                # SEQUENTIAL STAGE
                # -------------------------
                if isinstance(step, dict):
                    stage_name = step["stage"]
                else:
                    # Handle case where step might be just a string
                    stage_name = step
                    step = {"stage": stage_name, "parameters": {}}
                
                stage_def = stages_dict[stage_name]
                
                # Handle duplicate stage names with counter
                if stage_name not in step_counter:
                    step_counter[stage_name] = 1
                else:
                    step_counter[stage_name] += 1
                
                # Create unique template name
                if step_counter[stage_name] > 1:
                    template_name = f"{stage_name}-{step_counter[stage_name]}-{pipeline_name}"
                    step_display_name = f"{stage_name}-{step_counter[stage_name]}"
                else:
                    template_name = f"{stage_name}-{pipeline_name}"
                    step_display_name = stage_name

                steps_template["steps"].append(
                    [{"name": step_display_name, "template": template_name}]
                )

                # Build args - fix format to be separate args
                args = []
                for k, v in step.get("parameters", {}).items():
                    if isinstance(v, list):
                        v = ",".join(map(str, v))
                    args.append(f"--{k}")
                    if "=" not in str(v):  # Only add value if not already in key
                        args.append(str(v))

                # Create container spec
                container_spec = {
                    "image": f"no{stage_def['image']}",
                    "command": ["python", "main.py"],
                    "args": args,
                    "volumeMounts": [
                        {"name": "shared-data", "mountPath": stage_def["data-path"]}
                    ]
                }

                # Create template
                stage_template = {
                    "name": template_name,
                    "container": container_spec
                }

                workflow["spec"]["templates"].append(stage_template)

        # Add the steps template as the first template
        workflow["spec"]["templates"].insert(0, steps_template)
        workflows.append(workflow)

    return workflows


def save_workflows(workflows, output_path="output/pipeline_noreuse.yaml"):
    Path("output").mkdir(exist_ok=True)
    with open(output_path, "w") as f:
        for i, wf in enumerate(workflows):
            yaml.dump(wf, f, sort_keys=False, default_flow_style=False)
            if i < len(workflows) - 1:  # Add separator between workflows
                f.write("---\n")


if __name__ == "__main__":
    config = load_config()
    workflows = generate_argo_with_parallel(config)
    
    # Debug: print number of workflows
    print(f"Generated {len(workflows)} workflows")
    
    save_workflows(workflows)
    print("✅ Argo Workflow (parallel-capable, no reuse) saved to output/pipeline_noreuse.yaml")