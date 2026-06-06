from typing import Union, Optional, TypeAlias

YAML_Values: TypeAlias =Union[str, list, dict, float, int]


def check_for_paragraph(value: YAML_Values, context: dict) -> bool:

    """Returns True if the value should be interpreted as a Paragrpah"""
    return isinstance(value, str)


def check_for_subelements(
    value: YAML_Values, context: dict):
    if (
        isinstance(value, list)
        and ( # A combination of str and dicts
            any([isinstance(elem, str) for elem in value])
            and any([isinstance(elem, dict) for elem in value])
        )
        or ( # Not a table because dicts of different lengths
            isinstance(value, list)
            and len(set([len(elem) for elem in value])) == 1
        )
    ):
        return True
    else:
        return False
    

def check_for_tables(
    value: YAML_Values, context: dict
    ):
    if (
        isinstance(value, list)
        and all([isinstance(elem, dict) for elem in value])
        and len(set([len(elem) for elem in value])) == 1
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