"""
Compress baked publication assets without changing global Django settings.
"""

from __future__ import annotations

from typing import Any

from compressor.templatetags.compress import compress as parse_compress
from django import template
from stringprint2.services.render_context import PublicationRenderContext

register = template.Library()


class PublicationCompressionNode(template.Node):
    """
    Force compression only for a static publication's template context.
    """

    def __init__(self, node: Any) -> None:
        self.node = node

    def render(self, context: template.Context) -> str:
        output = str(self.node.render(context, forced=bool(context.get("publication_bake"))))
        render_context = context.get("publication_render")
        if isinstance(render_context, PublicationRenderContext) and render_context.baking:
            render_context.record_assets(output)
        return output


@register.tag("compress")
def compress(
    parser: template.base.Parser, token: template.base.Token
) -> PublicationCompressionNode:
    """
    Preserve the standard compress-tag syntax and honor per-render options.
    """
    return PublicationCompressionNode(parse_compress(parser, token))
