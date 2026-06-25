import re

from typing import Callable, Optional, Union, TypeAlias, Any

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

RLFlowables: TypeAlias = Union[Paragraph, Spacer, Table, KeepTogether, Image]

YAML_Values: TypeAlias =Union[str, list, dict, float, int, None]

# TODO: Create a block registration function and a singleton block registry

class BlockExistsError(Exception):
    pass

def create_block_registry() -> tuple[Callable, Callable, Callable]:
    """
    Creates the block registry
    """
    _BLOCK_REGISTRY = {}

    def register_block(block_code: str, block_convert: Callable) -> None:
        """
        Returns None. Adds a new block to the block registry.

        'block_code': a str of the form '_{code}' where 'code' is an alphanumeric code used
            to identify the block.
        'block_convert':a function with the following signature:
            my_func(obj: dict, context: dict) -> list[Flowable] 

            Where:
                obj: a dict which has a key that starts with the block code and a value
                    which is a user-defined data structure that contains the data needed
                    to generate the block as a ReportLab Flowable.
                context: a dict that contains all of the internal state of this program
                    at the time the conversion is executed. This will get passed to your 
                    function automatically and gives your conversion function access to 
                    anything and everything it needs to render your custom block. 
                    Feel free to explore the context dict by using a print(context) call
                    in your function.
                
            Return:
                A list of ReportLab Flowable from the reportlab.platypus module. Your custom
                block may be just one flowable (like a custom-populated table) or it can
                be a list of many flowable. 
        """
        _BLOCK_REGISTRY.update({block_code: block_convert})

    def list_blocks():
        return list(_BLOCK_REGISTRY.keys())
    
    def get_block_callable(block_code: str) -> Optional[Callable]:
        return _BLOCK_REGISTRY.get(block_code)

    return list_blocks, get_block_callable, register_block

list_blocks, get_block_callable, register_block = create_block_registry()

def convert_blocks(block_key: str, block_value: YAML_Values, context: dict) -> list[RLFlowables]:
    block_code_pattern = re.compile(r"(^_[a-zA-Z0-9]+)")
    matches = block_code_pattern.match(block_key)
    if matches is not None:
        block_code = matches.groups()[0]
    else:
        raise ValueError(f"Block code not found within block key: {block_key=}")
    block_converter = get_block_callable(block_code)
    block_value_w_python_objects = retrieve_block_variables(block_value, context)
    flowables = block_converter(block_key, block_value_w_python_objects, context)
    return flowables


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
