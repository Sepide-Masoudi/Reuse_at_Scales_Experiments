#pip install pyyaml
import yaml
from no_reuse_generator import NoReuseArgoGenerator
from reuse_generator import ReuseAwareArgoGenerator

CONFIG_PATH = "config.yaml"


def write_yaml(filename: str, workflows: list[dict]):
    with open(filename, "w") as f:
        yaml.dump_all(
            workflows,
            f,
            explicit_start=True, 
            sort_keys=False
        )


if __name__ == "__main__":
    no_reuse_gen = NoReuseArgoGenerator(CONFIG_PATH)
    reuse_gen = ReuseAwareArgoGenerator(CONFIG_PATH)

    no_reuse_workflows = no_reuse_gen.generate_all()
    reuse_workflows = reuse_gen.generate_all()

    write_yaml("argo-no-reuse.yaml", no_reuse_workflows)
    write_yaml("argo-reuse.yaml", reuse_workflows)
