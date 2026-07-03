from ..yaml_loader import load_yaml
import collections
import pathlib
from typing import Optional

class DeepChainMap(collections.ChainMap):
    """
    A ChainMap that recursively retrieves teh 
    """
    def __getitem__(self, key):
        # Gather all existing values for this key across all mapped layers
        values = [mapping[key] for mapping in self.maps if key in mapping]
        
        if not values:
            return self.__missing__(key)
            
        # If the first resolved value is a dictionary, deeply chain all found maps
        if isinstance(values[0], dict):
            sub_maps = [v for v in values if isinstance(v, dict)]
            return self.__class__(*sub_maps)
            
        return values[0]
    

def load_report_config(source_data: Optional[dict] = None, report_config_path: Optional[str | pathlib.Path] = None) -> tuple[dict, dict, dict]:
    """
    Returns a ChainMap of all the config data found in either the source_data or the 'report_config_path',
    which can either be a directory of config files or a specific file that contains all config data.
    """
    if report_config_path is not None:
        report_config_path = pathlib.Path(report_config_path)
    # First load defaults
    default_styles, default_tablestyles, default_doctemplate = load_config_directory(
        pathlib.Path(__file__).parent / 'defaults'
    )
    # Next load supplied config
    if report_config_path is not None and not report_config_path.exists():
        raise FileNotFoundError(f"The supplied path for the report_config_path does not exist. Here is what you passed:\n\n{str(report_config_path.resolve())}")
    
    if report_config_path is not None and report_config_path.is_file():
        config_data = load_yaml(report_config_path)
        config_styles = config_data.get("_style", {})
        config_tablestyles = config_data.get("_tablestyle", {})
        config_doctemplate = config_data.get("_doc", {})
    elif report_config_path is not None and report_config_path.is_dir():
        config_styles, config_tablestyles, config_doctemplate = load_config_directory(report_config_path)
    else:
        config_styles = {}
        config_tablestyles = {}
        config_doctemplate = {}

    # Third, load content-level config
    if source_data is None:
        source_data = {}
    content_styles = {"_style": source_data.pop("_style", {})}
    content_tablestyles = {"_tablestyle": source_data.pop("_tablestyle", {})}
    content_doctemplate = {"_doc": source_data.pop("_doc", {})}
    print(f"{content_styles=}")
    print(f"{config_styles=}")
    print(f"{default_styles=}")
    # Use chainmaps and recursively iterate over all keys within the config tree
    # (using the default trees as the source of all current keys) to build a dict
    # of only the governing keys from all sources.
    style_config = build_current_config(
        default_styles,
        DeepChainMap(
            content_styles,
            config_styles,
            default_styles,
        )
    )

    tablestyle_config = build_current_config(
        default_tablestyles,
        DeepChainMap(   
            content_tablestyles,
            config_tablestyles,
            default_tablestyles
        )
    )

    doctemplate_config = build_current_config(
        default_doctemplate,    
        DeepChainMap(
            content_doctemplate,
            config_doctemplate,
            default_doctemplate
        )
    )

    return style_config, tablestyle_config, doctemplate_config


def build_current_config(default_config: dict, config_data: DeepChainMap):
    """
    Returns a recursive mapping of the most current config in 'config_data' by referencing
    the keys in the 'default_config' which is assumed to have the complete set of
    all the most current keys.
    """
    style_map = {}
    for key in default_config:
        value = config_data[key]
        if isinstance(value, DeepChainMap):
            value = build_current_config(default_config[key], value)
        style_map.update({key: value})
    return style_map


def load_config_directory(config_dir: str | pathlib.Path | None) -> tuple[dict, dict, dict]:
    """
    Returns the config data for the configuration files contained within 'config_dir'.

    'config_dir': a directory containing a *.ymprint.yml file.
    """
    if config_dir is None:
        return {}, {}, {}
    config_dir = pathlib.Path(config_dir)
    dir_contents = list(config_dir.glob('*.ymprint.yml'))
    print(f"{dir_contents=}")
    if len(dir_contents) == 1:
        config_data = load_yaml(dir_contents[0])
    if config_data is None: # Occurs when the file exists but is empty
        return {}, {}, {}
    style = {"_style": config_data.get("_style", {})}
    tablestyle = {"_tablestyle": config_data.get("_tablestyle", {})}
    doctemplate = {"_doc": config_data.get("_doc", {})}
    return (
        style, tablestyle, doctemplate
    )