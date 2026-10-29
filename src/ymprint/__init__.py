"""Desktop publishing in YAML with Python."""

__version__ = "0.7.2"

from ymprint import config
from ymprint import blocks
from ymprint.app import Ymprint, default_app
from ymprint.blocks.registry import BlockExistsError, BlockRegistry, parse_block_key
from ymprint.render import RenderCallbackError, RenderEvent
from ymprint.data_sources import register_loader
