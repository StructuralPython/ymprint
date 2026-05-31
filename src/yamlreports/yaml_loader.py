from ruamel.yaml import YAML
import pathlib

yaml = YAML(typ='safe')

def load_yaml(filepath: str | pathlib.Path) -> dict:
    """
    Reads the Yaml document and returns the dict
    """
    with open(filepath) as file:
        data = yaml.load(file)
    return data