from collections import ChainMap
from reportlab.lib import pagesizes

def build_context(content: dict, layout: dict, styles: dict, tablestyles: dict) -> ChainMap:
    context = {
        'content': content, 
        'styles': {
            'text': {
                'yaml': styles, 
                'rl': styles.build()
            }, 'tables': {
                'yaml': tablestyles, 
                'rl': tablestyles.build()
            }
        },
        'layout': {
            'yaml': layout,
            'rl': layout.build()
        }
    }
    return ChainMap(context)