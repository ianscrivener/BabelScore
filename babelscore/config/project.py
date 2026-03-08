from pathlib import Path
import yaml

BABELSCORE_DIR = Path.home() / ".babelscore"
PROJECTS_DIR = BABELSCORE_DIR / "projects"


def project_exists(name: str) -> bool:
    return (PROJECTS_DIR / name).exists()


def create_project(config: dict) -> Path:
    """Write config.yaml and create data/ results/ dirs. Returns project path."""
    name = config["project"]
    proj_dir = PROJECTS_DIR / name
    (proj_dir / "data").mkdir(parents=True, exist_ok=True)
    (proj_dir / "results").mkdir(parents=True, exist_ok=True)

    config_path = proj_dir / "config.yaml"
    config_path.write_text(yaml.dump(config, default_flow_style=False, allow_unicode=True))

    return proj_dir
