
from typing import Union, TypeAlias

from reportlab.platypus import (
    Paragraph,
    Spacer,
    Table,
    Image,
    HRFlowable,
    KeepTogether,
)
from reportlab.lib.units import mm
from ymprint.config.docstyles import ReportStyles
from ..content_checks import check_for_variable
from ..errors import BlockError, YmprintAuthoringError
from .registry import BlockExistsError, BlockRegistry, parse_block_key

RLFlowables: TypeAlias = Union[Paragraph, Spacer, Table, KeepTogether, Image]

YAML_Values: TypeAlias =Union[str, list, dict, float, int, None]


def content_box(context: dict) -> dict:
    """
    Returns the content box ({'anchor', 'width', 'height'}) that a block should size
    itself against: the slide frame it is being rendered into, if any, otherwise
    the conservative box shared by all page templates.
    """
    return context['frames'].get('current') or context['frames']['all_pages']


def convert_blocks(block_key: str, block_value: YAML_Values, context: dict) -> list[RLFlowables]:
    parsed = parse_block_key(block_key)
    if parsed is None:
        raise ValueError(f"Block code not found within block key: {block_key=}")
    block_code, _block_id = parsed
    blocks: BlockRegistry = context["blocks"]
    block_converter = blocks.get(block_code)
    if block_converter is None:
        raise BlockError(
            block_key,
            f"Unknown block {block_code!r} (from key {block_key!r}). "
            f"Available blocks: {sorted(blocks.codes())}",
        )
    block_value_w_python_objects = retrieve_block_variables(block_value, context)
    try:
        flowables = block_converter(block_key, block_value_w_python_objects, context)
    except YmprintAuthoringError:
        # Already a friendly, author-facing error (e.g. PythonBlockError) — let it
        # propagate so the CLI can render it as-is.
        raise
    except Exception as exc:
        # An author mistake (missing key, empty/None value, wrong shape) surfaced as
        # a raw KeyError/TypeError/AttributeError. Wrap it so live mode reports it
        # instead of crashing.
        raise BlockError(block_key, _explain_block_error(block_key, exc)) from exc
    return flowables


def _explain_block_error(block_key: str, exc: Exception) -> str:
    """Turn a raw exception from a block converter into an author-facing message."""
    if isinstance(exc, KeyError):
        missing = exc.args[0] if exc.args else exc
        return (
            f"Block {block_key!r} is missing a required field: {missing!r}."
        )
    if isinstance(exc, TypeError) and "NoneType" in str(exc):
        return (
            f"Block {block_key!r} was left empty (or has no value). "
            f"Provide the fields this block needs."
        )
    if isinstance(exc, AttributeError) and "'NoneType'" in str(exc):
        return (
            f"Block {block_key!r} was left empty (or has no value). "
            f"Provide the fields this block needs."
        )
    return f"Block {block_key!r} could not be rendered: {type(exc).__name__}: {exc}"


def retrieve_block_variables(block_value: YAML_Values, context: dict) -> YAML_Values:
    """
    Returns 'block_value' but with list values or dictionary values that have
    the "$VAR" syntax substituted with the object values
    """
    if isinstance(block_value, str) and check_for_variable(block_value, context):
        var_name = get_variable_name(block_value)
        return context['vars'].get(var_name, block_value)
    elif isinstance(block_value, list):
        acc = []
        for elem in block_value:
            new_elem = retrieve_block_variables(elem, context)
            acc.append(new_elem)
        return acc
    elif isinstance(block_value, dict):
        acc = {}
        for k, v in block_value.items():
            new_v = retrieve_block_variables(v, context)
            acc.update({k: new_v})
        return acc
    else:
        return block_value


def get_variable_name(var_string: str) -> str:
    return var_string.lstrip('$')
