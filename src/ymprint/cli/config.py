from pathlib import Path
from typing import Optional


def locate_config_file(cwd: Path) -> Optional[Path]:
    config_file = None
    for parent in cwd.parents:
        filenames = [path.name for path in parent.glob("*.ymprint.yml")]
        if filenames:
            config_file = filenames[0]
    return config_file
    

