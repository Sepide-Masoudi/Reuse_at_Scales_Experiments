import yaml
from pathlib import Path
import uuid

def load_config(file_path="./test-config-file/config.yaml"):
    with open(file_path, "r") as f:
        return yaml.safe_load(f)


def generate_unique_path(stage_name, pipeline_name, path_type="input"):
    """Generate unique path for input/output directories"""
    uid = str(uuid.uuid4())[:8]
    if path_type == "input":
        return f"/mnt/data/{pipeline_name}_{stage_name}_input_{uid}"
    else:  # output
        return f"/mnt/data/{pipeline_name}_{stage_name}_output_{uid}"


def generate_argo_with_reuse(config):
    namespace = config["Deployment"]["namespace"]
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
                        "persistentVolumeClaim": {"claimName": pvc_name},
                    }
                ],
                "templates": [],
            },
        }

        steps_template = {"name": pipeline_name, "steps": []}

        for step in flow:
            # Handle parallel steps
            if isinstance(step, dict) and "parallel" in step and step["parallel"]:
                parallel_steps = []

                for stage_instance in step["stages"]:
                    stage_name = stage_instance["stage"]
                    stage_def = stages_dict[stage_name]
                    port = stage_def.get("port", 5000)

                    # Use custom template name if specified, otherwise generate from stage name
                    if "template-name" in stage_instance:
                        template_name = f"call-{stage_instance['template-name']}-service"
                        step_name = stage_instance["template-name"]  # Use template-name for step name
                    else:
                        template_name = f"call-{stage_name}-service"
                        step_name = stage_name

                    # Add to parallel steps with unique step name
                    parallel_steps.append({"name": step_name, "template": template_name})

                    # Generate unique paths
                    input_path = generate_unique_path(stage_name, pipeline_name, "input")
                    output_path = generate_unique_path(stage_name, pipeline_name, "output")

                    service_url = (
                        f"http://{stage_name}.{namespace}.svc.cluster.local:{port}/run"
                    )

                    command = ["curl", "-X", "POST", service_url]
                    command += ["-F", f"input_dir={input_path}"]
                    command += ["-F", f"output_dir={output_path}"]

                    # Add parameters
                    for key, value in stage_instance.get("parameters", {}).items():
                        if isinstance(value, list):
                            value = ",".join(map(str, value))
                        command += ["-F", f"{key}={value}"]

                    # Create container with volumeMounts INSIDE the container spec
                    container_spec = {
                        "image": "curlimages/curl:7.85.0",
                        "command": command,
                        "volumeMounts": [
                            {"name": "shared-data", "mountPath": "/mnt/data"}
                        ]
                    }

                    # Add template with container spec
                    workflow["spec"]["templates"].append(
                        {
                            "name": template_name,
                            "container": container_spec
                        }
                    )

                steps_template["steps"].append(parallel_steps)

            # Handle sequential steps
            else:
                if isinstance(step, dict):
                    stage_name = step["stage"]
                    # Use custom template name if specified for sequential steps too
                    if "template-name" in step:
                        template_name = f"call-{step['template-name']}-service"
                        step_name = step["template-name"]  # Use template-name for step name
                    else:
                        template_name = f"call-{stage_name}-service"
                        step_name = stage_name
                else:
                    # Handle case where step might be just a string
                    stage_name = step
                    step = {"stage": stage_name, "parameters": {}}
                    template_name = f"call-{stage_name}-service"
                    step_name = stage_name
                
                stage_def = stages_dict[stage_name]
                port = stage_def.get("port", 5000)

                steps_template["steps"].append(
                    [{"name": step_name, "template": template_name}]
                )

                # Generate unique paths
                input_path = generate_unique_path(stage_name, pipeline_name, "input")
                output_path = generate_unique_path(stage_name, pipeline_name, "output")

                service_url = (
                    f"http://{stage_name}.{namespace}.svc.cluster.local:{port}/run"
                )

                command = ["curl", "-X", "POST", service_url]
                command += ["-F", f"input_dir={input_path}"]
                command += ["-F", f"output_dir={output_path}"]

                # Add parameters
                for key, value in step.get("parameters", {}).items():
                    if isinstance(value, list):
                        value = ",".join(map(str, value))
                    command += ["-F", f"{key}={value}"]

                # Create container with volumeMounts INSIDE the container spec
                container_spec = {
                    "image": "curlimages/curl:7.85.0",
                    "command": command,
                    "volumeMounts": [
                        {"name": "shared-data", "mountPath": "/mnt/data"}
                    ]
                }

                # Add template with container spec
                workflow["spec"]["templates"].append(
                    {
                        "name": template_name,
                        "container": container_spec
                    }
                )

        # Add the steps template as the first template
        workflow["spec"]["templates"].insert(0, steps_template)
        workflows.append(workflow)

    return workflows


def save_workflows(workflows, output_path="output/pipeline_reuse.yaml"):
    Path("output").mkdir(exist_ok=True)
    with open(output_path, "w") as f:
        for i, wf in enumerate(workflows):
            yaml.dump(wf, f, sort_keys=False)
            if i < len(workflows) - 1:  # Add separator between workflows
                f.write("---\n")


if __name__ == "__main__":
    config = load_config()
    workflows = generate_argo_with_reuse(config)
    save_workflows(workflows)
    print("✅ Argo Workflow (with reuse) saved to output/pipeline_reuse.yaml")