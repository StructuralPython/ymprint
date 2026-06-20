from pathlib import Path
from typing import Optional

CONFIG_FILENAMES = ['doctemplate.yml', 'textstyles.yml', 'tablestyles.yml']

def locate_config_dir(cwd: Path) -> Optional[Path]:
    config_dir = None
    for parent in cwd.parents:
        filenames = [path.name for path in parent.glob("*.yml")]
        intersection = set(CONFIG_FILENAMES) & set(filenames)
        if intersection!= set():
            config_dir = parent
    return config_dir
    

