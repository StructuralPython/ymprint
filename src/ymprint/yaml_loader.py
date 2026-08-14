import collections
from ruamel.yaml import YAML
from ruamel.yaml.error import YAMLError
import pathlib

from .errors import YamlSyntaxError

yaml = YAML(typ='safe')

def load_yaml(filepath: str | pathlib.Path) -> dict:
    """
    Reads the Yaml document and returns the dict
    """
    with open(filepath) as file:
        try:
            data = yaml.load(file)
        except YAMLError as e:
            # Re-raise as an authoring error so the CLI can report *which* file
            # and *where* the syntax problem is, instead of crashing.
            raise YamlSyntaxError(filepath, e) from e
    return data
