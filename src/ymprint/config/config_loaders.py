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
    print(f"{report_config_path=}")
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
        config_doctemplate = config_data.get("_doctemplate", {})
    elif report_config_path is not None and report_config_path.is_dir():
        config_styles, config_tablestyles, config_doctemplate = load_config_directory(report_config_path)
    else:
        config_styles = {}
        config_tablestyles = {}
        config_doctemplate = {}

    # Third, load content-level config
    if source_data is None:
        source_data = {}
    content_styles = {"_style": source_data.get("_style", {})}
    content_tablestyles = {"_tablestyle": source_data.get("_tablestyle", {})}
    content_doctemplate = {"_doc": source_data.get("_doc", {})}

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

    'config_dir': a directory containing a textstyles.yml, tablestyles.yml, doctemplate.yml
    file.
    """
    if config_dir is None:
        return {}, {}, {}
    config_dir = pathlib.Path(config_dir)
    dir_contents = list(config_dir.glob('*'))
    file_list =[file.name for file in dir_contents if file.is_file]
    file_name_count = collections.Counter(file_list)
    styles, tablestyles, doctemplate = {}, {}, {}
    if file_name_count.get('textstyles.yml', 0) == 1:
        styles = load_yaml(config_dir / 'textstyles.yml')
    if file_name_count.get('tablestyles.yml', 0) == 1:
        tablestyles = load_yaml(config_dir / 'tablestyles.yml')
    if file_name_count.get('doctemplate.yml', 0) == 1:
        doctemplate = load_yaml(config_dir / 'doctemplate.yml')
    if (
        file_name_count.get('textstyles.yml', 0) > 1
        or file_name_count.get('tablestyles.yml', 0) > 1
        or file_name_count.get('doctemplate.yml', 0) > 1
    ):
        raise ValueError(
            "Expected to find one or none of each file: textstyles.yml, tablestyles.yml, doctemplate.yml' within "
            f"{str(config_dir.resolve())}. A duplicate filename was found (which causes ambiguity). Review file counts for this directory and correct:\n\n"
            f"{file_name_count}"
        )
    return styles, tablestyles, doctemplate