from .admonition_block import check_admoninition_block, convert_admonition_block
from .image_block import check_image_block, convert_image_block
from .quote_block import check_quote_block, convert_quote_block
from typing import Callable, Optional

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
        if block_code in _BLOCK_REGISTRY:
            raise BlockExistsError(f"The block with code name {block_code} is already in the registry")
        _BLOCK_REGISTRY.update({block_code: block_convert})

    def list_blocks():
        return list(_BLOCK_REGISTRY.keys())
    
    def get_block_callable(block_code: str) -> Optional[Callable]:
        return _BLOCK_REGISTRY.get(block_code)

    return list_blocks, get_block_callable, register_block

list_blocks, get_block_callable, register_block = create_block_registry()
