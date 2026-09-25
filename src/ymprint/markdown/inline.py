from wenmode import Wenmode
from wenmode.nodes import Text, Emphasis, InlineCode, Strong, Link
from wenmode.renderers import BaseRenderer, RenderContext


class RLInlineRenderer(BaseRenderer):
    pass


@RLInlineRenderer.register('emphasis')
def render_emphasis(renderer: RLInlineRenderer, node: Emphasis, context: RenderContext) -> str:
    # Render *all* children (which may themselves be nested inline nodes), not just
    # the first one, so that constructs like `*a **b** c*` survive intact.
    return f"<i>{renderer.render_children(node.children, context)}</i>"


@RLInlineRenderer.register('strong')
def render_strong(renderer: RLInlineRenderer, node: Strong, context: RenderContext) -> str:
    return f"<b>{renderer.render_children(node.children, context)}</b>"


@RLInlineRenderer.register('inlineCode')
def render_inlinecode(renderer: RLInlineRenderer, node: InlineCode, context: RenderContext) -> str:
    # return "<font backcolor={{context.style.yaml.code.background}}>" + f"{node.value}</font>"
    out =  '<font backcolor="#eeeeee" face="DejaVuSansMono">' + f"{node.value}</font>"
    return out


@RLInlineRenderer.register('link')
def render_link(renderer: RLInlineRenderer, node: Link, context: RenderContext) -> str:
    # ReportLab's intra-paragraph <link href="..."> renders a clickable link; the
    # label is the node's rendered children (which previously vanished entirely).
    label = renderer.render_children(node.children, context)
    return f'<link href="{node.url}"><font color="blue">{label}</font></link>'


def convert_inline_markdown(source: str) -> str:
    """
    Converts any inline markdown in 'source' into ReportLab compatible paragraph strings.
    """
    wen = Wenmode(renderer=RLInlineRenderer())
    return wen.render(source)
