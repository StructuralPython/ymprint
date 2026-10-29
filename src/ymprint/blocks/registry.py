import re
from typing import Any, Callable, Optional

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


# Structural keys handled by the story builder itself, or popped as config before
# the story is built. A block may not take one of these codes.
RESERVED_CODES = frozenset({
    "_ul", "_ol", "_textstyle", "_slide", "_frame",
    "_vars", "_style", "_doc", "_tablestyle", "_data",
})

BLOCK_CODE_PATTERN = re.compile(r"^_[a-zA-Z0-9]+$")

BlockConverter = Callable[[str, Any, dict], list]


class BlockExistsError(Exception):
    pass


class BlockRegistry:
    """
    A mapping of block codes (e.g. '_img') to the converter functions that render
    them. Each Ymprint application owns one, so blocks registered on one app are
    not visible to another.
    """

    def __init__(self, blocks: Optional[dict[str, BlockConverter]] = None):
        self._blocks: dict[str, BlockConverter] = {}
        for code, convert in (blocks or {}).items():
            self.register(code, convert)

    def register(self, code: str, convert: BlockConverter, *, override: bool = False) -> None:
        """
        Returns None. Adds a block to the registry.

        'code': a str of the form '_{code}' where 'code' is alphanumeric. In a
            document, the block is used as `_{code}` or `_{code}_{id}`.
        'convert': a function with the signature

                convert(block_key: str, block_value: Any, context: dict) -> list[Flowable]

            Where:
                block_key: the key as written in the document, e.g. '_img_logo'.
                    Use parse_block_key(block_key) to get the id.
                block_value: the user-defined data under the key, with any
                    "$VAR" values already substituted.
                context: a dict with all of the internal state of the render
                    (styles, frames, vars, paths, the block registry, ...).

            Return:
                A list of ReportLab Flowables from the reportlab.platypus module.
        'override': replace an existing block with the same code instead of
            raising BlockExistsError.
        """
        if not isinstance(code, str) or not BLOCK_CODE_PATTERN.match(code):
            raise ValueError(
                f"Invalid block code {code!r}: a block code is an underscore followed by "
                "letters and digits only, e.g. '_beam'. A second underscore separates "
                "the block id in documents ('_beam_b1') and cannot be part of the code."
            )
        if code in RESERVED_CODES:
            raise ValueError(f"Block code {code!r} is reserved by ymprint.")
        if code in self._blocks and not override:
            raise BlockExistsError(
                f"A block with code {code!r} is already registered. "
                "Pass override=True to replace it."
            )
        self._blocks[code] = convert

    def block(self, code: str, *, override: bool = False) -> Callable[[BlockConverter], BlockConverter]:
        """Decorator form of register()."""
        def decorator(convert: BlockConverter) -> BlockConverter:
            self.register(code, convert, override=override)
            return convert
        return decorator

    def get(self, code: str) -> Optional[BlockConverter]:
        return self._blocks.get(code)

    def codes(self) -> list[str]:
        return list(self._blocks)

    def copy(self) -> "BlockRegistry":
        new = BlockRegistry()
        new._blocks = dict(self._blocks)
        return new

    def __contains__(self, code: object) -> bool:
        return code in self._blocks

    def __len__(self) -> int:
        return len(self._blocks)

    def __repr__(self) -> str:
        return f"BlockRegistry({sorted(self._blocks)})"
