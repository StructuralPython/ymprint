from pathlib import Path
from typing import Optional


def locate_config_dir(cwd: Path) -> Optional[Path]:
    config_dir = None
    for parent in cwd.parents:
        filenames = [path.name for path in parent.glob("*.ymprint.yml")]
        if filenames:
            config_dir = parent
    return config_dir
    

