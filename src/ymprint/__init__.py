"""Desktop publishing in YAML with Python."""

__version__ = "0.8.1"

from ymprint import config
from ymprint import blocks
from ymprint.app import Ymprint, default_app
from ymprint.blocks.registry import BlockExistsError, BlockRegistry, parse_block_key
from ymprint.render import RenderCallbackError, RenderEvent
from ymprint.data_sources import register_loader
from ymprint.fanout import Instance, RenderRun
from ymprint.exports import register_decoder, register_serializer
