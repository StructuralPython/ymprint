import re
from typing import Optional

# A block key is `_<code>` or `_<code>_<id>`: the code runs up to the second
# underscore, so `_py_setup` is a `_py` block with id `setup` while `_pyfoo` is a
# `_pyfoo` block. The id only makes keys unique within a mapping.
BLOCK_KEY_PATTERN = re.compile(r"^(?P<code>_[a-zA-Z0-9]+)(?:_(?P<id>.+))?$", re.DOTALL)


def parse_block_key(key) -> Optional[tuple[str, Optional[str]]]:
    """
    Returns (code, id) for a block key, or None if 'key' is not block-shaped.

        '_py_setup' -> ('_py', 'setup')
        '_pyfoo'    -> ('_pyfoo', None)
        'Heading'   -> None
    """
    if not isinstance(key, str):
        return None
    matches = BLOCK_KEY_PATTERN.match(key)
    if matches is None:
        return None
    return matches.group("code"), matches.group("id")
