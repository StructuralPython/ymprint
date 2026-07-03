from wenmode import Wenmode
from wenmode.nodes import Text, Emphasis, InlineCode, Strong, Link
from wenmode.renderers import BaseRenderer, RenderContext


class RLInlineRenderer(BaseRenderer):
    pass


@RLInlineRenderer.register('emphasis')
def render_emphasis(renderer: RLInlineRenderer, node: Emphasis, context: RenderContext) -> str:
    return f"<i>{node.children[0].value}</i>"


@RLInlineRenderer.register('strong')
def render_strong(renderer: RLInlineRenderer, node: Strong, context: RenderContext) -> str:
    return f"<b>{node.children[0].value}</b>"


@RLInlineRenderer.register('inlineCode')
def render_inlinecode(renderer: RLInlineRenderer, node: InlineCode, context: RenderContext) -> str:
    # return "<font backcolor={{context.style.yaml.code.background}}>" + f"{node.value}</font>"
    out =  '<font backcolor="#eeeeee" face="DejaVuSansMono">' + f"{node.value}</font>"
    return out


def convert_inline_markdown(source: str) -> str:
    """
    Converts any inline markdown in 'source' into ReportLab compatible paragraph strings.
    """
    wen = Wenmode(renderer=RLInlineRenderer())
    return wen.render(source)

