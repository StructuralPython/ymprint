from typing import Union, Optional, TypeAlias

YAML_Values: TypeAlias =Union[str, list, dict, float, int, None]

def check_for_variable(value: YAML_Values, context: dict) -> bool:
    """Returns True if `value` represents a variable to be evaluated from the context vars"""
    return (
        isinstance(value, str)
        and value.startswith("$")
        and value.lstrip("$").isidentifier()
    )


def check_for_paragraph(value: YAML_Values, context: dict) -> bool:

    """Returns True if the value should be interpreted as a Paragrpah"""
    return isinstance(value, str)

def check_for_none(value: YAML_Values, context: dict) -> bool:
    return value is None


def check_for_subelements(
    value: YAML_Values, context: dict):
    if (
        isinstance(value, list)
        and ( # A combination of str and dicts
            any([isinstance(elem, str) for elem in value])
            and any([isinstance(elem, dict) for elem in value])
        )
    ):
        return True
    elif check_for_tables(value, context):
        return False
    elif isinstance(value, dict):
        return True
    else:
        return False
    
def check_for_nested_lists(value: YAML_Values, context: dict):
    """
    Implement recursive check for nested lits
    """
    acc = []
    if value is None or isinstance(value, (float, int)):
        return False
    if not isinstance(value, list):
        return False
    for elem in value:
        if isinstance(elem, list):
            acc.extend([check_for_nested_lists(elem, context)])
        elif isinstance(elem, str):
            acc.extend([True])
        else:
            acc.extend([False])
    return all(acc)  


def check_for_ordered_nested_lists(value: YAML_Values, context: dict):
    """
    Implement recursive check for nested lits
    """
    acc = []
    if value is None or isinstance(value, (float, int)):
        return False
    if not isinstance(value, dict):
        return False
    acc = []
    for k, v in value.items():
        if not isinstance(k, int):
            acc.extend([False])
        if (
            isinstance(k, int)
            and
            isinstance(v, dict)
        ):
            acc.extend([check_for_ordered_nested_lists(v, context)])
        elif isinstance(v, str):
            acc.extend([True])
        else:
            acc.extend([False])
    return all(acc)  


def check_for_tables(
    value: YAML_Values, context: dict
    ):
    if not isinstance(value, list):
        return False
    if not all([isinstance(elem, dict) for elem in value]):
        return False
    table_keys = [tuple([k for k in elem]) for elem in value]
    if (
        isinstance(value, list)
        and all([isinstance(elem, dict) for elem in value])
        and len(set([len(elem) for elem in value])) == 1
        and len(set(table_keys)) == 1
    ):
        return True
    else:
        return False


def check_for_ul(
    value: YAML_Values, context: dict
    ):
    if (
        isinstance(value, list)
        and all([isinstance(elem, str) for elem in value])
    ):
        return True
    else:
        return False
    

def check_for_ol(
    value: YAML_Values, context: dict
    ):
    if (
        isinstance(value, dict)
        and all([isinstance(k, int) for k in value.keys()])
    ):
        return True
    else:
        return False