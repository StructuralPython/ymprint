"""
The blocks that ship with ymprint. Every Ymprint app starts from a copy of these.

Blocks from optional packages are included when the package is installed:
`_hc` from ym-handcalcs (`pip install ymprint[hc]`).
"""
from importlib.util import find_spec

from .registry import BlockRegistry
from .admonition_block import generate_admonition_block
from .code_block import convert_code_block
from .hrule_block import convert_hrule
from .image_block import convert_image_block
from .json_block import convert_loadjson_block
from .matplotfig_block import convert_matplotfig_block
from .nextpagetemplate_block import convert_next_page_template
from .p_block import convert_p_block
from .page_break_block import convert_page_break
from .python_block import convert_python_block
from .quote_block import convert_quote_block
from .spacer_block import convert_spacer
from .table_block import convert_table_block

BUILTIN_BLOCKS = BlockRegistry({
    "_info": generate_admonition_block("info"),
    "_warning": generate_admonition_block("warning"),
    "_danger": generate_admonition_block("danger"),
    "_tip": generate_admonition_block("tip"),
    "_note": generate_admonition_block("note"),
    "_code": convert_code_block,
    "_hrule": convert_hrule,
    "_img": convert_image_block,
    "_loadjson": convert_loadjson_block,
    "_matplotfig": convert_matplotfig_block,
    "_nextpagetemplate": convert_next_page_template,
    "_p": convert_p_block,
    "_pagebreak": convert_page_break,
    "_py": convert_python_block,
    "_blockquote": convert_quote_block,
    "_spacer": convert_spacer,
    "_table": convert_table_block,
})


def convert_hc_block(block_key, block_value, context):
    # Imported on first use, so documents without _hc don't pay for importing handcalcs.
    from ym_handcalcs import convert_hc_block as convert

    return convert(block_key, block_value, context)


if find_spec("ym_handcalcs") is not None:
    BUILTIN_BLOCKS.register("_hc", convert_hc_block)
