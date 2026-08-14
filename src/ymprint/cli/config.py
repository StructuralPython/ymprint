from pathlib import Path
from typing import Optional


def locate_config_file(cwd: Path) -> Optional[Path]:
    """Return the nearest ``*.ymprint.yml`` at or above ``cwd`` as a full path."""
    for parent in [cwd, *cwd.parents]:
        matches = sorted(parent.glob("*.ymprint.yml"))
        if matches:
            return matches[0]
    return None
    

